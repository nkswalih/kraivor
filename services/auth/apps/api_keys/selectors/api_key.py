"""
apps/api_keys/selectors/api_key.py
 
Read-only database helpers for API keys.
No business logic — selectors only fetch rows.
 
Follows the selector / service split used throughout the project
(same pattern as authentication/ and oauth/).
"""
 
from __future__ import annotations

from api_keys.models import APIKey


def get_active_key_by_hash(key_hash: str) -> APIKey | None:
    """
    Look up a non-revoked API key by its SHA-256 hash.
 
    Called on every authenticated request — must be fast.
    The key_hash column is indexed so this is an O(1) index seek.
 
    NOTE: expiry is NOT checked here — that is the service layer's job so
    that we can return a distinct error (expired vs. invalid/revoked).
 
    Args:
        key_hash: 64-char SHA-256 hex digest.
 
    Returns:
        APIKey with user pre-fetched via select_related, or None.
    """
    try:
        return APIKey.objects.select_related("user").get(
            key_hash=key_hash,
            revoked=False,
        )
    except APIKey.DoesNotExist:
        return None
 
 
def get_user_api_keys(user_id: str):
    """
    List all non-revoked API keys for a user, newest first.
 
    Expired keys are intentionally included — users should be able to
    see and clean up expired keys themselves.
 
    Args:
        user_id: UUID string of the authenticated user.
 
    Returns:
        QuerySet of APIKey objects (lazy — not yet evaluated).
    """
    return APIKey.objects.filter(
        user_id=user_id,
        revoked=False,
    ).order_by("-created_at")
 
 
def get_user_key_by_id(user_id: str, key_id: str) -> APIKey | None:
    """
    Look up a specific non-revoked API key that belongs to a user.
 
    Returns None — not raises — when the key does not exist or belongs
    to a different user.  The view converts None → 404, which avoids
    confirming the existence of other users' keys (IDOR protection).
 
    Args:
        user_id: UUID string of the requesting user.
        key_id:  UUID string of the API key.
 
    Returns:
        APIKey instance or None.
    """
    try:
        return APIKey.objects.get(
            id=key_id,
            user_id=user_id,
            revoked=False,
        )
    except APIKey.DoesNotExist:
        return None
