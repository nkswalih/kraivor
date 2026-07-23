"""
apps/api_keys/services/hasher.py

SHA-256 hashing and constant-time comparison for API keys.

WHY SHA-256 and not Argon2/bcrypt?
───────────────────────────────────
API keys are 32 bytes (256 bits) of cryptographically-secure random data.
Unlike passwords they already have maximum entropy, so slow-hashing adds
latency (200–500 ms per request) for no security gain.  SHA-256 is the
right tool here — it is the same approach used by GitHub, Stripe, and OpenAI.

Use Argon2 only for low-entropy inputs (passwords, PINs).

TIMING ATTACK PREVENTION
─────────────────────────
hmac.compare_digest performs a constant-time byte comparison that does not
short-circuit on the first differing byte.  This prevents an attacker from
learning valid key prefixes through response-time differences.
"""

from __future__ import annotations

import hashlib
import hmac


def hash_api_key(raw_key: str) -> str:
    """
    SHA-256 hash a raw API key for database storage.

    Args:
        raw_key: Full key string (e.g. 'krv_live_abc123…').

    Returns:
        64-character lowercase hex digest.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of a supplied raw key against its stored hash.

    Hashes raw_key with SHA-256 then compares the result to stored_hash
    using hmac.compare_digest to prevent timing side-channels.

    Args:
        raw_key:     The raw key from the Authorization header.
        stored_hash: The SHA-256 hex digest stored in the database.

    Returns:
        True if the key matches, False otherwise.
    """
    computed = hash_api_key(raw_key)
    return hmac.compare_digest(computed, stored_hash)
