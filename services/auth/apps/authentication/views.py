"""
Authentication views — KRV-011 / KRV-013 / KRV-014

Multi-step sign-in, token refresh, sign-out, and session management.

Endpoints
─────────
KRV-011  POST /signin/identify/         Email lookup → next step
KRV-011  POST /signin/password/         Password verification + token issuance
KRV-011  POST /signin/otp/send/         Send OTP email
KRV-011  POST /signin/otp/verify/       Verify OTP + token issuance
KRV-013  POST /refresh/                 Rotate refresh token
KRV-014  POST /signout/                 Revoke current session (cookie-based, no JWT needed)
KRV-014  GET  /sessions/                List active sessions
KRV-014  DELETE /sessions/<id>/         Revoke one session
KRV-014  DELETE /sessions/all/          Revoke all sessions

Token strategy
──────────────
- access_token   → JSON body (store in memory, 15-min lifetime)
- refresh_token  → HttpOnly cookie (30-day lifetime, rotated on every use)
"""

import hashlib
import logging
from dataclasses import dataclass

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User

from .cookie_utils import create_refresh_cookie
from .models import RefreshToken
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
    SessionSerializer,
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


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

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


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash a raw refresh token. Consistent with token_service storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _clear_refresh_cookie(response: Response) -> None:
    """Expire the refresh_token cookie on a response object in-place."""
    cookie = create_refresh_cookie("")
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


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Write a new refresh_token cookie onto a response object in-place."""
    cookie = create_refresh_cookie(raw_token)
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


def _active_sessions_qs(user_id):
    """Base queryset: non-revoked, non-expired sessions for a user."""
    return RefreshToken.objects.filter(
        user_id=user_id,
        revoked=False,
        expires_at__gt=timezone.now(),
    )


def _current_device_id(request) -> str | None:
    """
    Extract device_id from the JWT payload sitting on request.auth.
    DRF places the decoded payload dict on request.auth when using
    a JWT authentication backend that returns the raw payload.
    """
    if isinstance(request.auth, dict):
        return request.auth.get("device_id")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# KRV-011 — Multi-step Sign In
# ─────────────────────────────────────────────────────────────────────────────

class SignInIdentifyView(APIView):
    """
    POST /api/auth/signin/identify/

    Step 1: Email only — determines next authentication method.
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
            return Response(
                {"next_step": "signup", "user_exists": False, "email_verified": False}
            )

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
    POST /api/auth/signin/password/

    Step 2a: Password verification → issues token pair.
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
        _set_refresh_cookie(response, tokens.refresh_token)
        return response


class OTPSendView(APIView):
    """POST /api/auth/signin/otp/send/ — Send OTP to user's email."""

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
    """POST /api/auth/signin/otp/verify/ — Verify OTP and issue token pair."""

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
        _set_refresh_cookie(response, tokens.refresh_token)
        return response


# ─────────────────────────────────────────────────────────────────────────────
# KRV-013 — Token Refresh
# ─────────────────────────────────────────────────────────────────────────────

class RefreshTokenView(APIView):
    """
    POST /api/auth/refresh/

    Rotate refresh token:
    1. Read refresh token from HttpOnly cookie
    2. Validate against database
    3. Issue new access_token + new refresh_token
    4. Immediately revoke old refresh token
    5. Replay attack: reused token → revoke ALL user sessions
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
        _set_refresh_cookie(response, tokens.refresh_token)
        return response


# ─────────────────────────────────────────────────────────────────────────────
# KRV-013 legacy — kept for backwards compat with existing url patterns
# ─────────────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/auth/logout/

    Legacy single-device logout via token_service.revoke_token().
    Kept so existing url pattern and any clients using /logout/ still work.
    New clients should use POST /signout/ (KRV-014).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        ip = get_client_ip(request)

        if refresh_token:
            token_service = get_token_service()
            token_service.revoke_token(refresh_token)
            log_auth_event(event_type="logout", ip=ip, method="single")

        response = Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(response)
        return response


class LogoutAllView(APIView):
    """
    POST /api/auth/logout/all/

    Legacy all-devices logout via token_service.revoke_all_user_tokens().
    Kept for backwards compat. New clients should use DELETE /sessions/all/ (KRV-014).
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
            {"message": "Logged out from all devices", "sessions_revoked": count},
            status=status.HTTP_200_OK,
        )
        _clear_refresh_cookie(response)
        return response


# ─────────────────────────────────────────────────────────────────────────────
# KRV-014 — Sign Out & Session Management
# ─────────────────────────────────────────────────────────────────────────────

class SignOutView(APIView):
    """
    POST /api/auth/signout/

    Revoke the refresh token from the HttpOnly cookie and clear the cookie.

    Does NOT require a valid JWT — covers the common case where the
    access token has already expired and the user just wants to sign out.

    Always returns 200 (idempotent — already-revoked or missing tokens are fine).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get("refresh_token")
        ip = get_client_ip(request)

        if raw_token:
            token_hash = _hash_token(raw_token)
            revoked = RefreshToken.objects.filter(
                token_hash=token_hash,
                revoked=False,
            ).update(revoked=True)

            if revoked:
                log_auth_event(event_type="signout", ip=ip, method="single")

        response = Response({"message": "Signed out successfully."}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(response)
        return response


class SessionListView(APIView):
    """
    GET /api/auth/sessions/

    Returns all active (non-revoked, non-expired) sessions for the
    authenticated user, ordered by most-recently-used first.

    is_current=True on the session whose device_id matches the
    device_id claim in the caller's JWT payload.

    Response shape:
    {
        "sessions": [
            {
                "session_id": "uuid",
                "device_name": "Chrome on macOS",
                "device_type": "desktop",
                "ip_address": "203.0.113.1",
                "last_used_at": "2025-05-14T10:00:00Z",
                "created_at":   "2025-05-10T08:00:00Z",
                "is_current":   true
            },
            ...
        ]
    }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = _active_sessions_qs(request.user.id).order_by("-last_used_at")

        serializer = SessionSerializer(
            sessions,
            many=True,
            context={"current_device_id": _current_device_id(request)},
        )
        return Response({"sessions": serializer.data}, status=status.HTTP_200_OK)


class SessionRevokeView(APIView):
    """
    DELETE /api/auth/sessions/<session_id>/

    Revoke a single session by UUID.

    Security rules:
    - Users can only revoke their own sessions.
    - Returns 404 (not 403) for sessions belonging to other users —
      avoids confirming the session exists.
    - Returns 404 for sessions that are already revoked or expired.
    - If the revoked session is the current device, the cookie is also cleared.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        try:
            session = RefreshToken.objects.get(
                id=session_id,
                user=request.user,
                revoked=False,
                expires_at__gt=timezone.now(),
            )
        except RefreshToken.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        session.revoked = True
        session.save(update_fields=["revoked"])

        log_auth_event(
            event_type="session_revoked",
            user_id=str(request.user.id),
            ip=get_client_ip(request),
            extra={"session_id": str(session_id)},
        )

        response = Response({"message": "Session revoked."}, status=status.HTTP_200_OK)

        # Clear cookie only if the caller just revoked their own current device
        current = _current_device_id(request)
        if current and str(session.device_id) == str(current):
            _clear_refresh_cookie(response)

        return response


class SessionRevokeAllView(APIView):
    """
    DELETE /api/auth/sessions/all/

    Revoke every active session for the current user (sign out everywhere).
    Requires a valid JWT.
    Also clears the refresh cookie on the current device.

    Response:
    {
        "message": "All sessions revoked.",
        "revoked_count": 3
    }
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        revoked_count = _active_sessions_qs(request.user.id).update(revoked=True)

        log_auth_event(
            event_type="logout_all",
            user_id=str(request.user.id),
            ip=get_client_ip(request),
            method="all_devices",
            extra={"sessions_revoked": revoked_count},
        )

        response = Response(
            {"message": "All sessions revoked.", "revoked_count": revoked_count},
            status=status.HTTP_200_OK,
        )
        _clear_refresh_cookie(response)
        return response