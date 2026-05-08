"""
OTP Service for sign-in verification - KRV-011.

Handles:
- OTP generation (6-digit codes)
- OTP storage in Redis with expiry
- OTP sending via email
- Rate limiting for OTP resend
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class OTPError(Exception):
    """Base exception for OTP operations."""
    pass


class OTPExpiredError(OTPError):
    """Raised when OTP has expired."""
    pass


class OTPInvalidError(OTPError):
    """Raised when OTP is invalid."""
    pass


class OTPRateLimitError(OTPError):
    """Raised when too many OTP requests."""
    
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Too many requests. Try again in {retry_after} seconds.")


class OTPService:
    """
    Redis-backed OTP service for sign-in verification.
    
    Generates 6-digit OTPs, stores in Redis with 5-minute expiry,
    and handles rate limiting for resend requests.
    """

    OTP_PREFIX = "otp_code"
    OTP_ATTEMPTS_PREFIX = "otp_attempts"
    OTP_RESEND_PREFIX = "otp_resend"

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.REDIS_URL
        self.client: redis.Redis = redis.from_url(url, decode_responses=True)

    def _get_otp_key(self, email: str) -> str:
        return f"{self.OTP_PREFIX}:{email.lower()}"

    def _get_attempts_key(self, email: str) -> str:
        return f"{self.OTP_ATTEMPTS_PREFIX}:{email.lower()}"

    def _get_resend_key(self, email: str) -> str:
        return f"{self.OTP_RESEND_PREFIX}:{email.lower()}"

    def generate_otp(self, email: str) -> str:
        """Generate a 6-digit OTP."""
        # Generate cryptographically secure random number
        otp = ''.join(secrets.choice('0123456789') for _ in range(settings.OTP_CODE_LENGTH))
        return otp

    def store_otp(self, email: str, otp: str) -> None:
        """Store OTP in Redis with expiry."""
        otp_key = self._get_otp_key(email)
        expiry_seconds = settings.OTP_EXPIRE_MINUTES * 60
        
        pipe = self.client.pipeline()
        pipe.setex(otp_key, expiry_seconds, otp)
        pipe.execute()

    def send_otp(self, email: str, otp: str) -> bool:
        """
        Send OTP to user email.
        
        This is a placeholder - actual email sending is handled
        by the email_service in the views layer.
        
        Returns True if sending was initiated.
        """
        # OTP will be sent via email service in the view
        # This method just marks that OTP was generated
        logger.info(f"OTP generated for {email} (to be sent via email)")
        return True

    def create_and_send(self, email: str) -> tuple[str, bool]:
        """
        Generate OTP, store it, and prepare for sending.
        
        Returns:
            (otp_code, sending_initiated)
        """
        # Check rate limit first
        self.check_resend_rate_limit(email)
        
        otp = self.generate_otp(email)
        self.store_otp(email, otp)
        
        return otp, True

    def verify_otp(self, email: str, otp_code: str) -> bool:
        """
        Verify OTP code.
        
        Returns True if valid, raises appropriate error otherwise.
        """
        otp_key = self._get_otp_key(email)
        attempts_key = self._get_attempts_key(email)
        
        stored_otp = self.client.get(otp_key)
        
        if stored_otp is None:
            raise OTPExpiredError("OTP has expired. Please request a new one.")
        
        # Constant-time comparison using hmac
        import hmac
        if not hmac.compare_digest(stored_otp, otp_code):
            # Record failed attempt
            pipe = self.client.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(attempts_key, settings.OTP_EXPIRE_MINUTES * 60)
            pipe.execute()
            
            # Check if max attempts exceeded
            attempts = int(self.client.get(attempts_key) or 0)
            if attempts >= settings.OTP_MAX_ATTEMPTS:
                self.client.delete(otp_key)
                self.client.delete(attempts_key)
                raise OTPInvalidError("Too many failed attempts. Please request a new OTP.")
            
            raise OTPInvalidError("Invalid OTP code.")
        
        # Success - delete OTP and attempts
        pipe = self.client.pipeline()
        pipe.delete(otp_key)
        pipe.delete(attempts_key)
        pipe.execute()
        
        return True

    def check_resend_rate_limit(self, email: str) -> None:
        """Check if user can request OTP resend."""
        resend_key = self._get_resend_key(email)
        ttl = self.client.ttl(resend_key)
        
        if ttl > 0:
            raise OTPRateLimitError(retry_after=ttl)

    def record_resend(self, email: str) -> None:
        """Record that OTP was requested for resend rate limiting."""
        resend_key = self._get_resend_key(email)
        wait_seconds = settings.OTP_RESEND_WAIT_SECONDS
        
        pipe = self.client.pipeline()
        pipe.setex(resend_key, wait_seconds, 1)
        pipe.execute()


class OTPSender:
    """
    Email sender for OTP codes.
    
    This is a simple wrapper that defers to the email service.
    In a real implementation, this would format and send the email.
    """
    
    def send(self, email: str, otp: str) -> None:
        """
        Send OTP code to user email.
        
        Uses the existing email_service infrastructure.
        """
        from apps.users.email_service import email_service
        
        subject = "Your Kraivor Sign-In Code"
        message = f"""
Your sign-in verification code is: {otp}

This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request this code, please ignore this email.
"""
        try:
            email_service.send_email(
                to_email=email,
                subject=subject,
                message=message,
            )
        except Exception:
            logger.exception(f"Failed to send OTP email to {email}")


_otp_service: Optional[OTPService] = None
_otp_sender: Optional[OTPSender] = None


def get_otp_service() -> OTPService:
    """Get or create the OTP service singleton."""
    global _otp_service
    if _otp_service is None:
        _otp_service = OTPService()
    return _otp_service


def get_otp_sender() -> OTPSender:
    """Get or create the OTP sender singleton."""
    global _otp_sender
    if _otp_sender is None:
        _otp_sender = OTPSender()
    return _otp_sender