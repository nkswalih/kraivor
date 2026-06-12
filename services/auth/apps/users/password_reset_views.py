"""
Password reset views.

Endpoints
─────────
POST /api/auth/forgot-password/  — Send password reset email
POST /api/auth/reset-password/   — Reset password with token
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from users.email_service import email_service
from users.models import User
from users.rate_limiter import RateLimitExceededError, rate_limiter
from users.verification import decode_verification_token, generate_verification_token

logger = logging.getLogger(__name__)

_RESEND_LIMIT = 3
_RESEND_WINDOW = 3600


class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/

    Sends a password reset email with a signed JWT token.
    Rate limited to prevent abuse.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": "Email is required.", "error_code": "missing_email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rate_key = f"forgot_password:{email}"
        try:
            rate_limiter.is_allowed(rate_key, limit=_RESEND_LIMIT, window_seconds=_RESEND_WINDOW)
        except RateLimitExceededError as exc:
            response = Response(
                {
                    "error": "Too many requests. Please wait before trying again.",
                    "error_code": "rate_limit_exceeded",
                    "retry_after": exc.retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response["Retry-After"] = str(exc.retry_after)
            return response

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {
                    "message": "If that email exists, a password reset link has been sent.",
                },
                status=status.HTTP_200_OK,
            )

        token = generate_verification_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Reset your Kraivor password</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f0f13; color: #e2e8f0; margin: 0; padding: 0; }}
    .container {{ max-width: 520px; margin: 40px auto; background: #1a1a2e;
                 border-radius: 12px; overflow: hidden;
                 border: 1px solid rgba(255,255,255,0.08); }}
    .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6);
               padding: 32px 40px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; color: #fff; font-weight: 700; }}
    .body {{ padding: 40px; }}
    .body p {{ margin: 0 0 16px; line-height: 1.6; color: #cbd5e1; }}
    .btn {{ display: inline-block; padding: 14px 32px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: #fff; text-decoration: none; border-radius: 8px;
            font-weight: 600; font-size: 15px; margin: 8px 0 24px; }}
    .footer {{ padding: 20px 40px; border-top: 1px solid rgba(255,255,255,0.06);
               color: #64748b; font-size: 12px; }}
    .url {{ word-break: break-all; color: #818cf8; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>✦ Kraivor</h1>
    </div>
    <div class="body">
      <p>Hi {user.name or user.email},</p>
      <p>We received a request to reset your password. Click the button below to set a new password.</p>
      <p style="text-align:center;">
        <a href="{reset_url}" class="btn">Reset Password</a>
      </p>
      <p>This link expires in <strong>1 hour</strong>. If you didn't request this, you can safely ignore this email.</p>
      <p style="font-size:12px;color:#64748b;">
        Or copy this URL into your browser:<br>
        <span class="url">{reset_url}</span>
      </p>
    </div>
    <div class="footer">
      &copy; 2026 Kraivor &middot; You received this because you requested a password reset.
    </div>
  </div>
</body>
</html>"""

        text = (
            f"Hi {user.name or user.email},\n\n"
            "We received a request to reset your password.\n\n"
            f"Reset here: {reset_url}\n\n"
            "This link expires in 1 hour.\n\n"
            "If you didn't request this, you can safely ignore this email.\n\n"
            "— The Kraivor Team"
        )

        try:
            email_service._backend.send(
                to_email=user.email,
                subject="Reset your Kraivor password",
                html=html,
                text=text,
            )
            logger.info("Password reset email sent to %s", user.email)
        except Exception:
            logger.exception("Failed to send password reset email to %s", user.email)

        return Response(
            {"message": "If that email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/

    Accepts a signed JWT token and a new password.
    Validates the token and updates the user's password.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token", "").strip()
        new_password = request.data.get("password", "").strip()

        if not token:
            return Response(
                {"error": "Reset token is required.", "error_code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password or len(new_password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters.", "error_code": "weak_password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload, error_code = decode_verification_token(token)

        if error_code == "token_expired":
            return Response(
                {
                    "error": "Your reset link has expired.",
                    "error_code": "token_expired",
                    "hint": "Request a new reset link via /api/auth/forgot-password/",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if error_code:
            return Response(
                {"error": "Invalid reset token.", "error_code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = payload.get("sub")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found.", "error_code": "user_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.email != payload.get("email"):
            return Response(
                {"error": "Invalid reset token.", "error_code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        logger.info("Password reset for user %s", user.email)

        return Response(
            {"message": "Password reset successfully. You can now sign in."},
            status=status.HTTP_200_OK,
        )
