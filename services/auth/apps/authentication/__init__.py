from authentication.otp import get_otp_sender, get_otp_service
from authentication.security import get_lockout_manager

__all__ = [
    "SignInIdentifyView",
    "SignInPasswordView",
    "OTPSendView",
    "OTPVerifyView",
    "RefreshTokenView",
    "get_lockout_manager",
    "get_otp_service",
    "get_otp_sender",
]

# The five view names were listed in __all__ but never imported, so the
# package advertised an API it did not have:
#   >>> from authentication import RefreshTokenView
#   ImportError: cannot import name 'RefreshTokenView' from 'authentication'
# Nothing inside the repo hit it because urls.py imports from .views
# directly, but any external caller following __all__ would have.
#
# They cannot simply be imported at module scope: Django imports this app's
# __init__ while populating the app registry, and views.py reaches Django
# models, so an eager import raises AppRegistryNotReady during setup.
#
# PEP 562 lazy export resolves it. Access is resolved on first attribute
# lookup, by which point the registry is populated.
_VIEW_EXPORTS = frozenset(
    {
        "SignInIdentifyView",
        "SignInPasswordView",
        "OTPSendView",
        "OTPVerifyView",
        "RefreshTokenView",
    }
)


def __getattr__(name: str):
    if name in _VIEW_EXPORTS:
        from authentication import views

        return getattr(views, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
