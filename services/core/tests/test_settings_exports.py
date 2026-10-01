"""Tests for the settings package's export surface.

`development.py`, `production.py`, `test.py` and `test_postgres.py` all do
`from .base import *`. Before base.py declared `__all__`, that star-import
also dragged base's own imports (`environ`, `env`, `Path`, `mimetypes`) into
every derived settings module — CodeQL's py/polluting-import.

Two things must hold:

1. Every Django setting a derived module needs is still exported.
2. base's implementation details are NOT exported.
"""

import ast
import importlib
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DERIVED = [
    "core.settings.development",
    "core.settings.production",
    "core.settings.test",
    "core.settings.test_postgres",
]

PRODUCTION_SOURCE = Path(__file__).resolve().parents[1] / "core" / "settings" / "production.py"


def _guarded_names() -> list[str]:
    """The names production.py's startup guard requires.

    Parsed rather than imported: importing production raises when its secrets
    are unset, which is the very behaviour under test.
    """
    tree = ast.parse(PRODUCTION_SOURCE.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_PRODUCTION_REQUIRED"
            for t in node.targets
        ):
            assert isinstance(node.value, ast.Tuple), "_PRODUCTION_REQUIRED is not a tuple"
            names = [
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            assert len(names) == len(node.value.elts), "non-literal entry in the guard list"
            return names

    raise AssertionError("_PRODUCTION_REQUIRED not found in production.py")


# Settings that the derived modules either override or read back, so losing
# any of them from base's export surface would break a real boot.
MUST_BE_EXPORTED = [
    "SECRET_KEY",
    "DEBUG",
    "ALLOWED_HOSTS",
    "INSTALLED_APPS",
    "MIDDLEWARE",
    "ROOT_URLCONF",
    "ASGI_APPLICATION",
    "TEMPLATES",
    "STATIC_URL",
    "MEDIA_URL",
    "DATABASES",
    "REST_FRAMEWORK",
    "CACHES",
    "LOGGING",
    "CELERY_BROKER_URL",
    "CELERY_TASK_ROUTES",
    "CELERY_BEAT_SCHEDULE",
    "CHANNEL_LAYERS",
    "KAFKA_BOOTSTRAP_SERVERS",
    "REDIS_URL",
    "IDENTITY_SERVICE_URL",
    "JWT_ALGORITHM",
    "JWT_AUDIENCE",
    "JWT_ISSUER",
    "INTERNAL_REQUEST_HEADER",
    "INTERNAL_REQUEST_SECRET",
    "INTERNAL_REQUEST_TOKEN",
]


class TestBaseExportsSettings:
    @pytest.mark.parametrize("name", MUST_BE_EXPORTED)
    def test_setting_is_in_all(self, name):
        from core.settings import base

        assert name in base.__all__, f"{name} missing from base.__all__"

    def test_all_only_contains_uppercase_names(self):
        from core.settings import base

        offenders = [n for n in base.__all__ if not n.isupper()]
        assert offenders == []

    def test_all_is_sorted_and_unique(self):
        """Sorted so diffs stay readable when a setting is added."""
        from core.settings import base

        assert base.__all__ == sorted(base.__all__)
        assert len(base.__all__) == len(set(base.__all__))

    def test_every_exported_name_actually_exists(self):
        from core.settings import base

        missing = [n for n in base.__all__ if not hasattr(base, n)]
        assert missing == []


class TestBaseDoesNotLeakImports:
    @pytest.mark.parametrize("name", ["env", "environ", "Path", "mimetypes"])
    def test_import_is_not_exported(self, name):
        """These are base's implementation details, not settings.

        If one leaked into a derived module, a bare `env(...)` or `Path(...)`
        there would resolve against base's binding instead of raising
        NameError, which is exactly the confusion this export list prevents.
        """
        from core.settings import base

        assert name not in base.__all__

    @pytest.mark.parametrize("name", ["env", "environ", "Path", "mimetypes"])
    def test_star_import_does_not_bind_it(self, name):
        """The actual property: what `from .base import *` binds.

        Executed rather than inferred, so the assertion covers Python's own
        star-import semantics instead of a reimplementation of them. A derived
        settings module that later writes `env(...)` or `Path(...)` must get a
        NameError, not base's binding.
        """
        namespace: dict = {"__builtins__": __builtins__}
        exec("from core.settings.base import *", namespace)  # noqa: S102

        assert name not in namespace

    def test_star_import_does_bind_the_settings(self):
        """The other half: restricting __all__ must not cost us any setting."""
        from core.settings import base

        namespace: dict = {"__builtins__": __builtins__}
        exec("from core.settings.base import *", namespace)  # noqa: S102

        for name in ("SECRET_KEY", "INSTALLED_APPS", "MIDDLEWARE", "DATABASES"):
            assert name in namespace, f"{name} no longer reaches derived settings"

        # And the bound set is exactly __all__ — no more, no less.
        bound = {k for k in namespace if not k.startswith("__")}
        assert bound == set(base.__all__)


class TestDerivedModulesLoad:
    @pytest.mark.parametrize(
        "module_name", ["core.settings.development", "core.settings.test", "core.settings.test_postgres"]
    )
    def test_module_imports_and_has_settings(self, module_name):
        """Every derived settings module must still boot after __all__."""
        mod = importlib.import_module(module_name)
        assert mod.SECRET_KEY
        assert "MIDDLEWARE" in dir(mod)
        assert "REST_FRAMEWORK" in dir(mod)

    @pytest.mark.parametrize(
        "module_name",
        ["core.settings.development", "core.settings.test", "core.settings.test_postgres"],
    )
    def test_settings_are_strings_or_containers(self, module_name):
        """Django only accepts these types; a leaked object would not.

        TEMPLATES is a list of dicts by design, so it is checked separately
        from the dotted-path lists.
        """
        mod = importlib.import_module(module_name)
        for name in ("INSTALLED_APPS", "MIDDLEWARE"):
            value = getattr(mod, name)
            assert isinstance(value, (list, tuple)), f"{module_name}.{name}"
            assert all(isinstance(v, str) for v in value), f"{module_name}.{name}"

        templates = mod.TEMPLATES
        assert isinstance(templates, (list, tuple))
        assert templates and all(isinstance(t, dict) for t in templates)
        assert all("BACKEND" in t for t in templates)

    def test_production_imports_when_required_secrets_are_present(self, monkeypatch):
        """production.py refuses to import without its required secrets.

        base.py resolves env(...) at import time, so patching os.environ
        after base is loaded has no effect — production reads the values
        base already computed. Patch base's namespace, which is what the
        star import copies.
        """
        from core.settings import base

        monkeypatch.setattr(base, "IDENTITY_JWKS_URL", "https://id/.well-known/jwks.json", raising=False)
        monkeypatch.setattr(base, "DATABASES", {"default": {"NAME": "kraivor"}}, raising=False)
        monkeypatch.setattr(base, "INTERNAL_REQUEST_SECRET", "s" * 32, raising=False)
        monkeypatch.setattr(base, "SECRET_KEY", "k" * 50, raising=False)

        sys.modules.pop("core.settings.production", None)
        try:
            mod = importlib.import_module("core.settings.production")

            assert mod.DEBUG is False
            assert mod.INTERNAL_REQUEST_SECRET == "s" * 32
            assert "MIDDLEWARE" in dir(mod)
        finally:
            sys.modules.pop("core.settings.production", None)

    def test_production_still_refuses_missing_secrets(self, monkeypatch):
        """The production guard must survive the __all__ change.

        The guard reads globals() of production's own module, which is
        populated by the star import. If __all__ had stopped exporting
        SECRET_KEY into that namespace the guard would silently stop seeing
        it and production would boot unprotected — so assert it still trips.
        """
        from core.settings import base

        monkeypatch.setattr(base, "IDENTITY_JWKS_URL", "", raising=False)
        monkeypatch.setattr(base, "DATABASES", {"default": {"NAME": "kraivor"}}, raising=False)
        monkeypatch.setattr(base, "INTERNAL_REQUEST_SECRET", "", raising=False)
        monkeypatch.setattr(base, "SECRET_KEY", "", raising=False)

        sys.modules.pop("core.settings.production", None)
        try:
            with pytest.raises(RuntimeError, match="Refusing to start in production"):
                importlib.import_module("core.settings.production")
        finally:
            sys.modules.pop("core.settings.production", None)

    def test_guard_names_the_settings_that_are_missing(self, monkeypatch):
        """A guard that fires without saying what is missing sends the
        operator to grep. Assert the message is actionable."""
        from core.settings import base

        monkeypatch.setattr(base, "IDENTITY_JWKS_URL", "", raising=False)
        monkeypatch.setattr(base, "DATABASES", {"default": {"NAME": "kraivor"}}, raising=False)
        monkeypatch.setattr(base, "INTERNAL_REQUEST_SECRET", "s" * 32, raising=False)
        monkeypatch.setattr(base, "SECRET_KEY", "k" * 50, raising=False)

        sys.modules.pop("core.settings.production", None)
        try:
            with pytest.raises(RuntimeError) as exc:
                importlib.import_module("core.settings.production")
        finally:
            sys.modules.pop("core.settings.production", None)

        message = str(exc.value)
        assert "IDENTITY_JWKS_URL" in message
        # SECRET_KEY was set, so it must NOT be reported missing.
        assert "unset required settings: SECRET_KEY" not in message
        assert "INTERNAL_REQUEST_SECRET" not in message

    def test_guard_reports_a_missing_database(self, monkeypatch):
        """A blank database name must be reported as DATABASE_URL, which is
        the name the operator sets — not as some inner dict key."""
        from core.settings import base

        monkeypatch.setattr(base, "IDENTITY_JWKS_URL", "https://id/jwks", raising=False)
        monkeypatch.setattr(base, "DATABASES", {"default": {"NAME": ""}}, raising=False)
        monkeypatch.setattr(base, "INTERNAL_REQUEST_SECRET", "s" * 32, raising=False)
        monkeypatch.setattr(base, "SECRET_KEY", "k" * 50, raising=False)

        sys.modules.pop("core.settings.production", None)
        try:
            with pytest.raises(RuntimeError) as exc:
                importlib.import_module("core.settings.production")
        finally:
            sys.modules.pop("core.settings.production", None)

        assert "DATABASE_URL" in str(exc.value)

    def test_every_guarded_name_exists_in_base(self):
        """The invariant that let the broken guard ship.

        `globals().get(name)` returns None both when a secret is unset and
        when the name was never defined — the guard cannot tell those apart.
        It listed two names base.py does not define, so it raised on every
        import and DJANGO_SETTINGS_MODULE=core.settings.production, which
        docker-compose.yml sets for four services, could never start.

        Any name added to _PRODUCTION_REQUIRED must therefore be a real
        module-level setting in base.py, or the guard is unsatisfiable.
        """
        from core.settings import base

        guarded = _guarded_names()
        assert guarded, "_PRODUCTION_REQUIRED must not be empty"

        undefined = [name for name in guarded if not hasattr(base, name)]
        assert undefined == [], (
            f"production.py guards names base.py never defines, so the guard "
            f"can never pass: {undefined}"
        )

    def test_every_guarded_name_is_exported_by_base(self):
        """A guarded name must also survive the star import into production."""
        from core.settings import base

        not_exported = [name for name in _guarded_names() if name not in base.__all__]
        assert not_exported == [], (
            f"guarded names missing from base.__all__, so production would "
            f"see them as unset: {not_exported}"
        )

    def test_test_postgres_differs_from_test_only_where_intended(self):
        """test_postgres overrides the database; it must not lose the rest."""
        from core.settings import test as test_settings
        from core.settings import test_postgres

        assert test_postgres.MIDDLEWARE == test_settings.MIDDLEWARE
        assert test_postgres.REST_FRAMEWORK == test_settings.REST_FRAMEWORK
