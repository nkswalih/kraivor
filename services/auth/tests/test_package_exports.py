"""The package __all__ must be importable.

`authentication/__init__.py` listed five view classes in `__all__` without
importing them, so the package advertised an API it did not have:

    >>> from authentication import RefreshTokenView
    ImportError: cannot import name 'RefreshTokenView' from 'authentication'

Nothing in the repo hit this because `urls.py` imports from `.views`
directly. The views are exported lazily (PEP 562) rather than at module
scope, because Django imports this app's `__init__` while populating the
app registry and an eager import of `views.py` raises AppRegistryNotReady
during `django.setup()`.
"""

import importlib

import pytest

import authentication

pytestmark = pytest.mark.unit

VIEW_EXPORTS = [
    "SignInIdentifyView",
    "SignInPasswordView",
    "OTPSendView",
    "OTPVerifyView",
    "RefreshTokenView",
]

HELPER_EXPORTS = ["get_lockout_manager", "get_otp_service", "get_otp_sender"]


class TestPackageExports:
    @pytest.mark.parametrize("name", VIEW_EXPORTS + HELPER_EXPORTS)
    def test_every_name_in_all_is_importable(self, name: str) -> None:
        assert getattr(authentication, name) is not None, (
            f"{name} is in authentication.__all__ but not importable from the package"
        )

    @pytest.mark.parametrize("name", VIEW_EXPORTS)
    def test_from_import_works(self, name: str) -> None:
        """The exact form an external caller would write."""
        ns: dict = {}
        exec(f"from authentication import {name}", ns)  # noqa: S102
        assert ns[name].__name__ == name

    @pytest.mark.parametrize("name", VIEW_EXPORTS)
    def test_lazy_export_is_the_same_object_as_views_module(self, name: str) -> None:
        views = importlib.import_module("authentication.views")
        assert getattr(authentication, name) is getattr(views, name)

    def test_unknown_attribute_still_raises_attribute_error(self) -> None:
        with pytest.raises(AttributeError, match="no attribute 'NotAThing'"):
            authentication.NotAThing  # noqa: B018

    def test_dir_advertises_all(self) -> None:
        assert set(authentication.__all__) <= set(dir(authentication))

    def test_django_setup_completed(self) -> None:
        """Guards the AppRegistryNotReady regression.

        If the views were ever moved back to an eager module-level import,
        this module would fail to import at all — which pytest would report
        as a collection error rather than a clean failure.
        """
        from django.apps import apps

        assert apps.ready
        assert apps.get_app_config("authentication") is not None
