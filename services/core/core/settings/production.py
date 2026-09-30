# ruff: noqa: F401, F403, F405
from .base import *

DEBUG = False

# =============================================================================
# PRODUCTION SECRET VALIDATION
# =============================================================================
# Fail fast at boot rather than shipping a service that silently trusts
# caller-supplied headers, or worse, one where a blank secret makes the
# gateway auth path unreachable and every request 401s.
# =============================================================================

_PRODUCTION_REQUIRED = (
    "SECRET_KEY",
    "INTERNAL_REQUEST_SECRET",
    "JWT_PUBLIC_KEY_PATH",
    "DATABASE_URL",
)

_missing = [name for name in _PRODUCTION_REQUIRED if not globals().get(name)]

if _missing:
    raise RuntimeError(
        "Refusing to start in production with unset required settings: "
        + ", ".join(_missing)
        + ". Set these in the environment (see .env.example) before deploying."
    )
