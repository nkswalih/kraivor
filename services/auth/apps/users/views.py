import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .email_service import email_service
from .models import User
from .rate_limiter import RateLimitExceeded, rate_limiter
from .serializers import SignUpSerializer, UserSerializer
from .verification import decode_verification_token, generate_verification_token

logger = logging.getLogger(__name__)

# Rate limit: 3 resend requests per hour per email (KRV-010)
_RESEND_LIMIT = 3
_RESEND_WINDOW = 3600  # seconds (1 hour)


class SignUpView(APIView):
    """
    POST /api/auth/signup/

    Registers a new user and sends a verification email.
    The account is created immediately but gated — analysis and AI features
    require email_verified=True.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Generate JWT verification token and send email
        token = generate_verification_token(user)
        try:
            email_service.send_verification_email(user, token)
            email_sent = True
        except Exception:
            logger.exception("Failed to send verification email to %s after signup", user.email)
            email_sent = False

        return Response(
            {
                "message": "Registration successful. Please check your email to verify your account.",
                "user_id": str(user.id),
                "email": user.email,
                "name": user.name,
                "email_verified": user.email_verified,
                "email_sent": email_sent,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """
    POST /api/auth/verify-email/

    Accepts a signed JWT, validates it, and marks the user's email as verified.

    Frontend states supported:
        verification_success  — 200, email_verified: true
        token_expired         — 400, error_code: "token_expired"
        invalid_token         — 400, error_code: "invalid_token"
        already_verified      — 200, email_verified: true (idempotent)
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "").strip()
        if not token:
            return Response(
                {"error": "Verification token is required.", "error_code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload, error_code = decode_verification_token(token)

        if error_code == "token_expired":
            return Response(
                {
                    "error": "Your verification link has expired.",
                    "error_code": "token_expired",
                    "hint": "Request a new verification email via /api/auth/resend-verification/",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if error_code:
            return Response(
                {"error": "Invalid verification token.", "error_code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch user from JWT sub claim
        user_id = payload.get("sub")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found.", "error_code": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Guard: email must match what was signed into the token
        if user.email != payload.get("email"):
            return Response(
                {"error": "Invalid verification token.", "error_code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Idempotent — already verified is fine
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified", "updated_at"])
            logger.info("Email verified for user %s", user.email)

        return Response(
            {
                "message": "Email verified successfully. Welcome to Kraivor!",
                "email_verified": True,
                "user_id": str(user.id),
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """
    POST /api/auth/resend-verification/

    Rate limited: maximum 3 requests per hour per email (Redis-backed).

    Frontend states supported:
        resend_success        — 200
        rate_limit_exceeded   — 429, retry_after header
        already_verified      — 400, error_code: "already_verified"
        user_not_found        — 404  (intentionally vague to prevent enumeration)
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": "Email is required.", "error_code": "missing_email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Redis rate limit check BEFORE DB lookup (fail fast, prevent enumeration)
        rate_key = f"resend_verification:{email}"
        try:
            rate_limiter.is_allowed(rate_key, limit=_RESEND_LIMIT, window_seconds=_RESEND_WINDOW)
        except RateLimitExceeded as exc:
            response = Response(
                {
                    "error": "Too many resend requests. Please wait before trying again.",
                    "error_code": "rate_limit_exceeded",
                    "retry_after": exc.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(exc.retry_after)
            return response

        # Intentionally return 200 even if user not found (prevents email enumeration)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {
                    "message": "If that email exists and is unverified, a new link has been sent.",
                },
                status=status.HTTP_200_OK,
            )

        if user.email_verified:
            return Response(
                {
                    "error": "This email address is already verified.",
                    "error_code": "already_verified",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = generate_verification_token(user)
        try:
            email_service.send_verification_email(user, token)
        except Exception:
            logger.exception("Failed to resend verification email to %s", user.email)
            return Response(
                {"error": "Failed to send email. Please try again later.", "error_code": "email_send_failed"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "message": "Verification email resent. Please check your inbox.",
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(APIView):
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)