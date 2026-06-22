"""
apps/api_keys/services/generator.py
 
Cryptographically secure API key generation.
 
Key format:  krv_live_<64 hex characters>
             ─────────────────────────────
prefix part  krv_live_       (stored in APIKey.prefix)
random part  64 hex chars    (32 random bytes via secrets.token_hex)
 
The prefix makes keys identifiable in logs, code review, and secret-
scanning tools (GitHub Advanced Security, GitLeaks, truffleHog can all
be configured to flag the 'krv_live_' pattern automatically).
 
Example:
    krv_live_3f8b2a9c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a
"""
 
from __future__ import annotations

import secrets

API_KEY_PREFIX = "krv_live_"
API_KEY_RANDOM_BYTES = 32  # 32 bytes → 64 hex characters
 
 
def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
 
    Returns:
        (raw_key, prefix) tuple where:
          raw_key  — the full key string to show the user ONCE, then discard
          prefix   — the short prefix stored in APIKey.prefix for display
 
    The raw key must never be stored.  Store only its SHA-256 hash.
    """
    random_part = secrets.token_hex(API_KEY_RANDOM_BYTES)
    raw_key = f"{API_KEY_PREFIX}{random_part}"
    prefix = f"{API_KEY_PREFIX}{random_part[:8]}"   # e.g. krv_live_3f8b2a9c
    return raw_key, prefix
 
 
def is_api_key_format(value: str) -> bool:
    """
    Fast format check — does this Bearer token look like a Kraivor API key?
 
    Used by the DRF authentication backend to decide in O(1) whether to
    attempt API key auth vs. falling through to JWT auth.  No DB involved.
 
    Args:
        value: The raw bearer token string from the Authorization header.
 
    Returns:
        True only when value starts with 'krv_live_' and the remaining
        64 characters are all lowercase hex digits.
    """
    if not isinstance(value, str):
        return False
    if not value.startswith(API_KEY_PREFIX):
        return False
    rest = value[len(API_KEY_PREFIX):]
    return len(rest) == 64 and all(c in "0123456789abcdef" for c in rest)