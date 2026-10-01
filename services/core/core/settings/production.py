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
#
# Every name below must be defined by base.py. Two names this guard used to
# require — JWT_PUBLIC_KEY_PATH and DATABASE_URL — are not: core verifies
# tokens against the identity service's remote JWKS (IDENTITY_JWKS_URL) and
# builds DATABASES via env.db_url("DATABASE_URL"). So globals().get() returned
# None for both on every import, the guard always raised, and
# DJANGO_SETTINGS_MODULE=core.settings.production (four services in
# docker-compose.yml) could not start at all. The guard was doing its job on a
# list that could never be satisfied.
#
# When adding a name here, assert it exists in base.__all__ first — a name
# base does not define fails identically to an unset secret, which is the
# failure this list exists to detect.

_PRODUCTION_REQUIRED = (
    "SECRET_KEY",              # Django signs sessions and CSRF with it
    "INTERNAL_REQUEST_SECRET",  # gateway/sibling auth bypass; blank = every request 401s
    "IDENTITY_JWKS_URL",       # blank = no token can ever be verified
)

_missing = [name for name in _PRODUCTION_REQUIRED if not globals().get(name)]

# DATABASE_URL has no default in base.py, so an unset value already raises
# there. Check the parsed name as well so the failure names the setting the
# operator has to set instead of surfacing as a missing key inside DATABASES.
if not (globals().get("DATABASES") or {}).get("default", {}).get("NAME"):
    _missing.append("DATABASE_URL")

if _missing:
    raise RuntimeError(
        "Refusing to start in production with unset required settings: "
        + ", ".join(_missing)
        + ". Set these in the environment (see .env.example) before deploying."
    )
