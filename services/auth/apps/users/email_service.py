"""
Email service layer for the Auth/Identity service.

Architecture:
    Phase 1 (current): Direct SMTP from Auth Service.
        - Development  → MailHog (captures all email, no real delivery)
        - Staging      → AWS SES SMTP sandbox
        - Production   → AWS SES SMTP

    Phase 2 (future): Auth Service publishes a Kafka event
        (e.g. "user.email_verification_requested") and the Notification Service
        consumes it and handles delivery.  The interface here is designed so
        that swapping the backend only requires changing this module.

The public API is intentionally simple:
    email_service.send_verification_email(user, token)
    email_service.send_welcome_email(user)          # future
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.users.models import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------


def _build_verification_html(verify_url: str, user_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Verify your Kraivor account</title>
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
      <p>Hi {user_name},</p>
      <p>Welcome to Kraivor! Please verify your email address to unlock analysis
         and AI features.</p>
      <p style="text-align:center;">
        <a href="{verify_url}" class="btn">Verify Email Address</a>
      </p>
      <p>This link expires in <strong>24 hours</strong>. If you didn't create an
         account you can safely ignore this email.</p>
      <p style="font-size:12px;color:#64748b;">
        Or copy this URL into your browser:<br>
        <span class="url">{verify_url}</span>
      </p>
    </div>
    <div class="footer">
      &copy; 2026 Kraivor &middot; You received this because you signed up.
    </div>
  </div>
</body>
</html>"""


def _build_verification_text(verify_url: str, user_name: str) -> str:
    return (
        f"Hi {user_name},\n\n"
        "Welcome to Kraivor! Please verify your email address to unlock "
        "analysis and AI features.\n\n"
        f"Verify here: {verify_url}\n\n"
        "This link expires in 24 hours.\n\n"
        "If you didn't create an account you can safely ignore this email.\n\n"
        "— The Kraivor Team"
    )


# ---------------------------------------------------------------------------
# SMTP backend
# ---------------------------------------------------------------------------


class SMTPEmailBackend:
    """
    Thin SMTP wrapper.  Works with MailHog (no auth) and SES (with auth).
    Settings consumed:
        EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
        EMAIL_USE_TLS, EMAIL_FROM
    """

    def send(self, to_email: str, subject: str, html: str, text: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        host = settings.EMAIL_HOST
        port = int(settings.EMAIL_PORT)
        use_tls = getattr(settings, "EMAIL_USE_TLS", False)
        user = getattr(settings, "EMAIL_HOST_USER", "")
        password = getattr(settings, "EMAIL_HOST_PASSWORD", "")

        try:
            if use_tls:
                smtp = smtplib.SMTP_SSL(host, port)
            else:
                smtp = smtplib.SMTP(host, port)
                smtp.ehlo()
                if getattr(settings, "EMAIL_USE_STARTTLS", False):
                    smtp.starttls()

            if user and password:
                smtp.login(user, password)

            smtp.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
            smtp.quit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to send email to %s: %s", to_email, exc)
            raise


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------


class EmailService:
    """High-level email operations for the Identity service."""

    def __init__(self) -> None:
        self._backend = SMTPEmailBackend()

    def send_verification_email(self, user: User, token: str) -> None:
        """
        Send a verification email to *user* containing the JWT *token*.

        In development this is captured by MailHog (localhost:8025).
        """
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={token}"

        html = _build_verification_html(verify_url, user.name or user.email)
        text = _build_verification_text(verify_url, user.name or user.email)

        logger.info("Sending verification email to %s", user.email)
        self._backend.send(
            to_email=user.email,
            subject="Verify your Kraivor account",
            html=html,
            text=text,
        )
        logger.info("Verification email sent to %s", user.email)

    def send_email(self, to_email: str, subject: str, message: str) -> None:
        """
        Send a plain text email.
        
        Used for OTP codes, password reset, etc.
        """
        text = f"{message}\n\n— The Kraivor Team"
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, sans-serif; background: #0f0f13; color: #e2e8f0; padding: 40px;">
  <div style="max-width: 520px; margin: 0 auto; background: #1a1a2e; border-radius: 12px; padding: 40px;">
    <h2 style="margin: 0 0 16px;">✦ Kraivor</h2>
    <p style="line-height: 1.6;">{message}</p>
  </div>
</body>
</html>"""
        
        logger.info("Sending email to %s", to_email)
        self._backend.send(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
        )


# Module-level singleton
email_service = EmailService()
