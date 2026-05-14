"""
Sign-in views for KRV-011/KRV-013.

Multi-step authentication flow with secure token handling:
1. POST /signin/identify - Email only, returns next step
2. POST /signin/password - Password verification
3. POST /signin/otp/send - Send OTP to email
4. POST /signin/otp/verify - Verify OTP and return tokens
5. POST /refresh - Refresh tokens with rotation (KRV-013)

Returns:
- access_token: In JSON response (store in memory)
- refresh_token: HttpOnly cookie (30-day persist, rotated on use)

Security features:
- Token rotation on every refresh
- Replay attack detection (KRV-013)
- Token hashing in database
- Session management
"""

import logging
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User

from .cookie_utils import create_refresh_cookie
from .otp import (
    OTPExpiredError,
    OTPInvalidError,
    OTPRateLimitError,
    get_otp_sender,
    get_otp_service,
)
from .security import (
    check_password as verify_password,
)
from .security import (
    generate_device_id,
    get_client_ip,
    get_lockout_manager,
)
from .serializers import (
    OTPSendSerializer,
    OTPVerifySerializer,
    SignInIdentifySerializer,
    SignInPasswordSerializer,
)
from .tokens import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenReusedError,
    TokenRevokedError,
    get_token_service,
)

logger = logging.getLogger(__name__)


@dataclass
class ErrorResponse:
    """Structured error response for consistent API responses."""

    error: str
    error_code: str
    status_code: int = 400
    extra: dict = None

    def to_response(self) -> Response:
        data = {"error": self.error, "error_code": self.error_code}
        if self.extra:
            data.update(self.extra)
        return Response(data, status=self.status_code)


def log_auth_event(
    event_type: str,
    user_id: str = None,
    email: str = None,
    ip: str = None,
    device_id: str = None,
    success: bool = True,
    method: str = None,
    extra: dict = None,
):
    """Structured logging for authentication events."""
    log_data = {
        "event": event_type,
        "user_id": user_id,
        "email": email,
        "ip": ip,
        "device_id": device_id[:32] if device_id else None,
        "success": success,
        "method": method,
        "timestamp": timezone.now().isoformat(),
    }
    if extra:
        log_data.update(extra)

    if success:
        logger.info("auth_event", extra=log_data)
    else:
        logger.warning("auth_event_failed", extra=log_data)


class SignInIdentifyView(APIView):
    """
    POST /api/auth/signin/identify

    Step 1: Email only - determines next authentication method.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignInIdentifySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                error="Invalid email format",
                error_code="invalid_email",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).to_response()

        email = serializer.validated_data["email"].lower()
        ip = get_client_ip(request)

        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)

        if is_locked:
            return ErrorResponse(
                error="Too many failed attempts. Account temporarily locked.",
                error_code="account_locked",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after": retry_after},
            ).to_response()

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
            user_exists = True
            email_verified = user.email_verified
        except User.DoesNotExist:
            user_exists = False
            email_verified = False

        if not user_exists:
            return Response({"next_step": "signup", "user_exists": False, "email_verified": False})

        if not email_verified:
            return Response(
                {
                    "next_step": "verify_email",
                    "user_exists": True,
                    "email_verified": False,
                    "message": "Please verify your email first",
                }
            )

        return Response(
            {
                "next_step": "choose_method",
                "user_exists": True,
                "email_verified": True,
                "methods": ["password", "otp"],
            }
        )


class SignInPasswordView(APIView):
    """
    POST /api/auth/signin/password

    Step 2: Password verification.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignInPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                error="Invalid request data",
                error_code="invalid_request",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).to_response()

        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        device_id = serializer.validated_data.get("device_id") or generate_device_id(request)

        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)

        if is_locked:
            return ErrorResponse(
                error="Too many failed attempts. Account temporarily locked.",
                error_code="account_locked",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after": retry_after},
            ).to_response()

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return ErrorResponse(
                error="Invalid credentials",
                error_code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        if not verify_password(password, user.password):
            lockout_mgr.record_failure(email, ip)
            log_auth_event(
                event_type="login_failed",
                user_id=str(user.id),
                email=email,
                ip=ip,
                device_id=device_id,
                success=False,
                method="password",
            )
            return ErrorResponse(
                error="Invalid credentials",
                error_code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        lockout_mgr.clear_attempts(email, ip)

        token_service = get_token_service()
        tokens = token_service.generate_tokens(user, device_id, ip, user_agent)
        cookie = create_refresh_cookie(tokens.refresh_token)

        log_auth_event(
            event_type="login_success",
            user_id=str(user.id),
            email=email,
            ip=ip,
            device_id=device_id,
            success=True,
            method="password",
        )

        response = Response(
            {
                "access_token": tokens.access_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
                "user": {"id": str(user.id), "email": user.email, "name": user.name},
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            "refresh_token",
            cookie["value"],
            httponly=cookie["httponly"],
            secure=cookie["secure"],
            samesite=cookie["samesite"],
            path=cookie["path"],
            max_age=cookie["max_age"],
            domain=cookie.get("domain"),
        )

        return response


class OTPSendView(APIView):
    """POST /api/auth/signin/otp/send - Send OTP to user's email."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                error="Invalid request data",
                error_code="invalid_request",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).to_response()

        email = serializer.validated_data["email"].lower()
        ip = get_client_ip(request)

        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)

        if is_locked:
            return ErrorResponse(
                error="Too many failed attempts. Account temporarily locked.",
                error_code="account_locked",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after": retry_after},
            ).to_response()

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return ErrorResponse(
                error="Invalid credentials",
                error_code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        if not user.email_verified:
            return ErrorResponse(
                error="Please verify your email first",
                error_code="email_not_verified",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).to_response()

        otp_service = get_otp_service()

        try:
            otp, _ = otp_service.create_and_send(email)
        except OTPRateLimitError as e:
            return ErrorResponse(
                error="Too many OTP requests. Please wait before trying again.",
                error_code="rate_limit_exceeded",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after": e.retry_after},
            ).to_response()

        otp_sender = get_otp_sender()
        try:
            otp_sender.send(email, otp)
        except Exception:
            logger.exception(f"Failed to send OTP to {email}")

        log_auth_event(
            event_type="otp_sent",
            user_id=str(user.id),
            email=email,
            ip=ip,
            method="otp",
        )

        return Response({"message": "OTP sent to your email"}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    """POST /api/auth/signin/otp/verify - Verify OTP and return tokens."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return ErrorResponse(
                error="Invalid request data",
                error_code="invalid_request",
                status_code=status.HTTP_400_BAD_REQUEST,
            ).to_response()

        email = serializer.validated_data["email"].lower()
        otp_code = serializer.validated_data["otp_code"]
        device_id = serializer.validated_data.get("device_id") or generate_device_id(request)

        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        lockout_mgr = get_lockout_manager()
        is_locked, retry_after = lockout_mgr.check_lockout(email, ip)

        if is_locked:
            return ErrorResponse(
                error="Too many failed attempts. Account temporarily locked.",
                error_code="account_locked",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                extra={"retry_after": retry_after},
            ).to_response()

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return ErrorResponse(
                error="Invalid credentials",
                error_code="invalid_credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        otp_service = get_otp_service()

        try:
            otp_service.verify_otp(email, otp_code)
        except OTPExpiredError:
            lockout_mgr.record_failure(email, ip)
            return ErrorResponse(
                error="OTP has expired. Please request a new one.",
                error_code="otp_expired",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()
        except OTPInvalidError as e:
            lockout_mgr.record_failure(email, ip)
            return ErrorResponse(
                error=str(e),
                error_code="invalid_otp",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        lockout_mgr.clear_attempts(email, ip)

        token_service = get_token_service()
        tokens = token_service.generate_tokens(user, device_id, ip, user_agent)
        cookie = create_refresh_cookie(tokens.refresh_token)

        log_auth_event(
            event_type="login_success",
            user_id=str(user.id),
            email=email,
            ip=ip,
            device_id=device_id,
            success=True,
            method="otp",
        )

        response = Response(
            {
                "access_token": tokens.access_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
                "user": {"id": str(user.id), "email": user.email, "name": user.name},
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            "refresh_token",
            cookie["value"],
            httponly=cookie["httponly"],
            secure=cookie["secure"],
            samesite=cookie["samesite"],
            path=cookie["path"],
            max_age=cookie["max_age"],
            domain=cookie.get("domain"),
        )

        return response


class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh

    Refresh access token using HttpOnly cookie.

    KRV-013: Implements secure refresh token rotation:
    1. Reads refresh token from HttpOnly cookie
    2. Validates token against database (not just JWT signature)
    3. Issues new access token AND new refresh token
    4. Immediately invalidates old refresh token (rotation)
    5. Detects replay attacks: if reused token is presented,
       ALL active sessions for that user are invalidated

    Returns:
    - access_token: In JSON response body
    - refresh_token: New token in HttpOnly cookie
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return ErrorResponse(
                error="Refresh token not found. Please sign in again.",
                error_code="missing_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        token_service = get_token_service()

        try:
            user, tokens = token_service.validate_and_rotate(
                refresh_token=refresh_token,
                ip_address=ip,
                user_agent=user_agent,
            )
        except TokenExpiredError:
            return ErrorResponse(
                error="Refresh token has expired. Please sign in again.",
                error_code="token_expired",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()
        except TokenInvalidError as e:
            logger.warning("refresh_token_invalid", extra={"error": str(e), "ip": ip})
            return ErrorResponse(
                error="Invalid refresh token. Please sign in again.",
                error_code="invalid_token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()
        except TokenRevokedError:
            return ErrorResponse(
                error="Token has been revoked. Please sign in again.",
                error_code="token_revoked",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()
        except TokenReusedError as e:
            logger.error(
                "replay_attack_detected",
                extra={
                    "user_id": str(user.id) if "user" in locals() else "unknown",
                    "ip": ip,
                    "error": str(e),
                },
            )
            return ErrorResponse(
                error="Security alert: suspicious activity detected. Please sign in again.",
                error_code="security_alert",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()
        except TokenError as e:
            logger.error("token_error", extra={"error": str(e), "ip": ip})
            return ErrorResponse(
                error="An error occurred. Please try again.",
                error_code="internal_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ).to_response()

        cookie = create_refresh_cookie(tokens.refresh_token)

        log_auth_event(
            event_type="token_refreshed",
            user_id=str(user.id),
            email=user.email,
            ip=ip,
            method="refresh",
        )

        response = Response(
            {
                "access_token": tokens.access_token,
                "token_type": tokens.token_type,
                "expires_in": tokens.expires_in,
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            "refresh_token",
            cookie["value"],
            httponly=cookie["httponly"],
            secure=cookie["secure"],
            samesite=cookie["samesite"],
            path=cookie["path"],
            max_age=cookie["max_age"],
            domain=cookie.get("domain"),
        )

        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout

    Invalidate current refresh token (single device logout).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        ip = get_client_ip(request)

        if refresh_token:
            token_service = get_token_service()
            token_service.revoke_token(refresh_token)

            log_auth_event(
                event_type="logout",
                ip=ip,
                method="single",
            )

        response = Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK,
        )

        cookie = create_refresh_cookie("")
        cookie["max_age"] = 0

        response.set_cookie(
            "refresh_token",
            value="",
            httponly=cookie["httponly"],
            secure=cookie["secure"],
            samesite=cookie["samesite"],
            path=cookie["path"],
            max_age=0,
            domain=cookie.get("domain"),
        )

        return response


class LogoutAllView(APIView):
    """
    POST /api/auth/logout/all

    Invalidate ALL refresh tokens for the user (all devices).
    Requires authentication.
    """

    def post(self, request):
        if not request.user.is_authenticated:
            return ErrorResponse(
                error="Authentication required",
                error_code="unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ).to_response()

        token_service = get_token_service()
        count = token_service.revoke_all_user_tokens(request.user)

        log_auth_event(
            event_type="logout_all",
            user_id=str(request.user.id),
            method="all_devices",
            extra={"sessions_revoked": count},
        )

        response = Response(
            {
                "message": "Logged out from all devices",
                "sessions_revoked": count,
            },
            status=status.HTTP_200_OK,
        )

        response.set_cookie(
            "refresh_token",
            value="",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path=settings.COOKIE_PATH,
            max_age=0,
            domain=settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
        )

        return response
