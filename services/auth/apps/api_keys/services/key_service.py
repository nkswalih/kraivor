"""
apps/api_keys/services/key_service.py
 
Business logic for the API key lifecycle.
 
Responsibilities:
  ─ Validate requested scopes
  ─ Generate raw key + prefix, hash the raw key
  ─ Persist the APIKey record (hash + prefix, never raw key)
  ─ Soft-revoke keys (sets revoked=True)
  ─ Authenticate incoming requests (used by the DRF backend)
 
This service NEVER returns a raw key from list/get operations.
The raw key surfaces only from create_api_key(), exactly once.
"""
 
from __future__ import annotations

import logging
from dataclasses import dataclass

from api_keys.models import VALID_SCOPES, APIKey
from api_keys.selectors.api_key import get_active_key_by_hash, get_user_key_by_id
from api_keys.services.generator import generate_api_key
from api_keys.services.hasher import hash_api_key
from django.utils import timezone
from users.models import User

logger = logging.getLogger(__name__)
 
 
# ── Exceptions ────────────────────────────────────────────────────────────────
 
class APIKeyError(Exception):
    """Base exception for all API key service errors."""
 
 
class APIKeyNotFoundError(APIKeyError):
    """Key does not exist, is revoked, or belongs to a different user."""
 
 
class APIKeyExpiredError(APIKeyError):
    """Key exists but has passed its expires_at timestamp."""
 
 
class InvalidScopeError(APIKeyError):
    """One or more requested scopes are not in VALID_SCOPES."""
 
 
# ── Result object ─────────────────────────────────────────────────────────────
 
@dataclass(frozen=True)
class CreatedAPIKey:
    """
    Returned once from create_api_key().
 
    raw_key is shown to the user exactly once in the HTTP response body.
    It is not persisted anywhere after that response is sent.
    """
    api_key: APIKey   # the DB record — contains hash and prefix, not raw key
    raw_key: str      # full key for the user to copy — show once, then gone
 
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def _validate_scopes(scopes: list[str]) -> None:
    invalid = set(scopes) - VALID_SCOPES
    if invalid:
        raise InvalidScopeError(
            f"Invalid scopes: {sorted(invalid)}. "
            f"Valid scopes are: {sorted(VALID_SCOPES)}"
        )
 
 
# ── Public service functions ──────────────────────────────────────────────────
 
def create_api_key(
    user: User,
    name: str,
    scopes: list[str],
    expires_at=None,
) -> CreatedAPIKey:
    """
    Create a new API key for a user.
 
    The raw key is returned in CreatedAPIKey.raw_key — this is the ONLY
    moment it is accessible.  It is never written to the database.
 
    Args:
        user:       Owner of the key.
        name:       Human-readable label (e.g. "GitHub Actions CI").
        scopes:     Permission scopes the key should carry.
        expires_at: Optional datetime.  None means the key never expires.
 
    Returns:
        CreatedAPIKey containing the saved APIKey record and the raw key.
 
    Raises:
        InvalidScopeError: If any scope string is not in VALID_SCOPES.
    """
    _validate_scopes(scopes)
 
    raw_key, prefix = generate_api_key()
    key_hash = hash_api_key(raw_key)
 
    api_key = APIKey.objects.create(
        user=user,
        name=name.strip(),
        key_hash=key_hash,
        prefix=prefix,
        scopes=scopes,
        expires_at=expires_at,
    )
 
    logger.info(
        "api_key_created: user_id=%s key_id=%s name=%r scopes=%s",
        user.id,
        api_key.id,
        name,
        scopes,
        # raw_key and key_hash are intentionally NOT logged
    )
 
    return CreatedAPIKey(api_key=api_key, raw_key=raw_key)
 
 
def revoke_api_key(user: User, key_id: str) -> APIKey:
    """
    Revoke an API key (sets revoked=True).
 
    Only the key's owner can revoke it.  The row is kept for audit purposes.
 
    Args:
        user:    Must be the key's owner.
        key_id:  UUID string of the key to revoke.
 
    Returns:
        The updated APIKey instance.
 
    Raises:
        APIKeyNotFoundError: Key doesn't exist or belongs to another user.
    """
    key = get_user_key_by_id(user_id=str(user.id), key_id=key_id)
    if key is None:
        raise APIKeyNotFoundError(f"API key {key_id} not found")
 
    key.revoked = True
    key.save(update_fields=["revoked"])
 
    logger.info(
        "api_key_revoked: user_id=%s key_id=%s name=%r",
        user.id,
        key.id,
        key.name,
    )
 
    return key
 
 
def authenticate_api_key(raw_key: str) -> APIKey:
    """
    Authenticate an incoming API key from an Authorization header.
 
    Called by APIKeyAuthentication backend on every request that carries
    a 'Bearer krv_live_…' token.
 
    Flow:
      1. SHA-256 hash the raw key
      2. Index lookup by hash (O(1))
      3. Verify not revoked   (handled by selector — revoked=False filter)
      4. Verify not expired   (checked here with a Python comparison)
      5. Update last_used_at  (targeted UPDATE — no full model save)
 
    Args:
        raw_key: Full raw key string from the Authorization header.
 
    Returns:
        Active APIKey with user pre-fetched.
 
    Raises:
        APIKeyNotFoundError: Hash not in DB or key is revoked.
        APIKeyExpiredError:  Key has passed its expires_at.
    """
    key_hash = hash_api_key(raw_key)
    api_key = get_active_key_by_hash(key_hash)
 
    if api_key is None:
        logger.info("api_key_auth_failed: key not found or revoked")
        raise APIKeyNotFoundError("API key not found or revoked")
 
    if api_key.expires_at and api_key.expires_at < timezone.now():
        logger.info("api_key_auth_failed: expired key_id=%s", api_key.id)
        raise APIKeyExpiredError("API key has expired")
 
    # Targeted UPDATE avoids a full model save and a read-modify-write race
    APIKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
    api_key.last_used_at = timezone.now()
 
    logger.info(
        "api_key_auth_success: key_id=%s user_id=%s",
        api_key.id,
        api_key.user_id,
    )
 
    return api_key