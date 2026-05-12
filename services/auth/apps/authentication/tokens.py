"""
Token Service - Production-Grade Token Management
==================================================

This service handles all JWT token operations with security best practices:
- Token generation with rotation
- Token storage with SHA-256 hashing
- Replay attack detection
- Session management
- Token revocation

This implements KRV-013: Refresh Token Rotation
"""

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class TokenError(Exception):
    """Base exception for token operations."""
    pass


class TokenExpiredError(TokenError):
    """Raised when token has expired."""
    pass


class TokenInvalidError(TokenError):
    """Raised when token is invalid."""
    pass


class TokenRevokedError(TokenError):
    """Raised when token has been revoked."""
    pass


class TokenReusedError(TokenError):
    """Raised when a reused token is detected (replay attack)."""
    pass


@dataclass
class TokenPair:
    """Container for generated token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 0


@dataclass
class TokenPayload:
    """Decoded token payload information."""
    user_id: str
    email: str
    name: str
    device_id: str
    token_id: Optional[str] = None


def _hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.
    
    Why hash? Even though JWTs are signed, storing the full token
    in the database creates a larger attack surface. Hashing provides
    an additional layer of protection.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_token_id() -> str:
    """Generate a unique ID for each token for tracking."""
    return secrets.token_urlsafe(16)


class TokenService:
    """
    Production-grade token service with rotation and security.
    
    Features:
    - Token rotation on every refresh
    - Token hashing for storage
    - Replay attack detection
    - Session management
    """

    def __init__(self):
        from authentication.models import RefreshToken
        self.RefreshToken = RefreshToken

    def generate_tokens(
        self,
        user,
        device_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ) -> TokenPair:
        """
        Generate access and refresh token pair with token tracking.
        
        Each refresh token gets a unique ID that's stored alongside
        the token hash in the database for rotation tracking.
        """
        token_id = _generate_token_id()
        
        refresh = CustomRefreshToken.for_user(user, device_id)
        refresh['token_id'] = token_id
        
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        self._store_refresh_token(
            user=user,
            token_id=token_id,
            token_hash=_hash_token(refresh_token),
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
        )

    def _store_refresh_token(
        self,
        user,
        token_id: str,
        token_hash: str,
        device_id: str,
        ip_address: str,
        user_agent: str,
    ) -> None:
        """Store refresh token in database with hash."""
        try:
            expiry_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
            expires_at = timezone.now() + timedelta(days=expiry_days)
            
            self.RefreshToken.objects.create(
                user=user,
                token_hash=token_hash,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else "",
                expires_at=expires_at,
            )
            
            logger.info(
                "token_created",
                extra={
                    "user_id": str(user.id),
                    "token_id": token_id,
                    "device_id": device_id[:32] if device_id else "",
                }
            )
        except Exception as e:
            logger.error(
                "token_store_failed",
                extra={"user_id": str(user.id), "error": str(e)}
            )

    def validate_and_rotate(
        self,
        refresh_token: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> tuple:
        """
        Validate refresh token and rotate (invalidate old, issue new).
        
        This implements the critical KRV-013 requirements:
        1. Validate token signature
        2. Check token not revoked/expired
        3. Verify token exists in database
        4. Rotate: revoke old, issue new
        5. Detect replay attacks
        
        Returns:
            (user, new_token_pair)
            
        Raises:
            TokenExpiredError: Token has expired
            TokenInvalidError: Token is invalid
            TokenRevokedError: Token has been revoked
            TokenReusedError: Replay attack detected
        """
        token_id = None
        device_id = ""
        
        try:
            token = RefreshToken(refresh_token)
            token_id = token.get('token_id')
            user_id = token.get('user_id')
            device_id = token.get('device_id', '')
            
            if not user_id:
                raise TokenInvalidError("Invalid token: missing user_id")
                
        except Exception as e:
            logger.warning("token_parse_failed", extra={"error": str(e)})
            raise TokenInvalidError("Invalid or malformed token")

        try:
            from users.models import User
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise TokenInvalidError("User not found or inactive")

        token_hash = _hash_token(refresh_token)
        
        try:
            stored_token = self.RefreshToken.objects.select_related('user').get(
                token_hash=token_hash,
                user=user,
                revoked=False,
            )
        except self.RefreshToken.DoesNotExist:
            token_exists = self.RefreshToken.objects.filter(
                user=user,
                token_hash=token_hash,
            ).exists()
            
            if token_exists:
                logger.error(
                    "token_replay_detected",
                    extra={
                        "user_id": str(user.id),
                        "token_id": token_id,
                        "ip": ip_address,
                    }
                )
                self._revoke_all_user_tokens(user)
                raise TokenReusedError("Replay attack detected - all sessions invalidated")
            
            raise TokenInvalidError("Token not found or already used")

        if stored_token.expires_at <= timezone.now():
            raise TokenExpiredError("Refresh token has expired")

        new_tokens = self.generate_tokens(
            user=user,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        stored_token.revoked = True
        stored_token.last_used_at = timezone.now()
        stored_token.save()
        
        logger.info(
            "token_rotated",
            extra={
                "user_id": str(user.id),
                "old_token_id": token_id,
                "new_token_id": getattr(new_tokens, 'token_id', 'N/A'),
            }
        )
        
        return user, new_tokens

    def validate_only(self, refresh_token: str) -> TokenPayload:
        """
        Validate refresh token WITHOUT rotation.
        
        Used for token introspection or validation without
        consuming the token.
        """
        try:
            token = RefreshToken(refresh_token)
            token_id = token.get('token_id')
            user_id = token.get('user_id')
            
            if not user_id:
                raise TokenInvalidError("Invalid token: missing user_id")
                
            from users.models import User
            user = User.objects.get(id=user_id, is_active=True)
            
            token_hash = _hash_token(refresh_token)
            
            stored_token = self.RefreshToken.objects.get(
                token_hash=token_hash,
                user=user,
                revoked=False,
            )
            
            if stored_token.expires_at <= timezone.now():
                raise TokenExpiredError("Token has expired")
            
            return TokenPayload(
                user_id=str(user.id),
                email=user.email,
                name=user.name,
                device_id=token.get('device_id', ''),
                token_id=token_id,
            )
            
        except self.RefreshToken.DoesNotExist:
            raise TokenInvalidError("Token not found or revoked")
        except TokenExpiredError:
            raise
        except Exception as e:
            logger.warning("token_validation_failed", extra={"error": str(e)})
            raise TokenInvalidError("Invalid token")

    def revoke_token(self, refresh_token: str) -> bool:
        """Revoke a specific refresh token."""
        try:
            token_hash = _hash_token(refresh_token)
            token = self.RefreshToken.objects.get(token_hash=token_hash)
            token.revoked = True
            token.save()
            logger.info("token_revoked", extra={"token_id": str(token.id)})
            return True
        except self.RefreshToken.DoesNotExist:
            return False

    def revoke_all_user_tokens(self, user) -> int:
        """Revoke ALL refresh tokens for a user (logout from all devices)."""
        count = self.RefreshToken.objects.filter(user=user, revoked=False).update(
            revoked=True
        )
        logger.info(
            "all_tokens_revoked",
            extra={"user_id": str(user.id), "count": count}
        )
        return count

    def _revoke_all_user_tokens(self, user) -> None:
        """Internal method for replay attack response."""
        self.revoke_all_user_tokens(user)

    def get_active_sessions(self, user) -> list:
        """Get list of active sessions for a user."""
        tokens = self.RefreshToken.objects.filter(
            user=user,
            revoked=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at')
        
        return [
            {
                "id": str(t.id),
                "device_id": t.device_id,
                "ip_address": t.ip_address,
                "user_agent": t.user_agent[:100],
                "created_at": t.created_at.isoformat(),
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
            }
            for t in tokens
        ]


class CustomRefreshToken(RefreshToken):
    """Custom refresh token with device_id and token_id."""

    @classmethod
    def for_user(cls, user, device_id: str = ""):
        token = super().for_user(user)
        token['name'] = user.name
        if device_id:
            token['device_id'] = device_id
        token['token_id'] = _generate_token_id()
        return token


_token_service: Optional[TokenService] = None


def get_token_service() -> TokenService:
    """Get or create the token service singleton."""
    global _token_service
    if _token_service is None:
        _token_service = TokenService()
    return _token_service