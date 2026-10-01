"""Tests for the BYOK encryption-key handling.

The failure these guard against is silent and expensive: a key that is
present but malformed used to be replaced with a freshly generated one, so
every process start produced a different encrypter and previously stored
provider sub-keys became permanently unreadable with no error anywhere.
"""

import pytest
from cryptography.fernet import Fernet

from app.core import encryption


@pytest.fixture
def valid_key():
    return Fernet.generate_key().decode()


class TestGetEncrypter:
    def test_accepts_generated_key(self, valid_key, monkeypatch):
        monkeypatch.setattr(
            encryption.settings, "key_encryption_key", valid_key, raising=False
        )
        encrypter = encryption.get_encrypter()
        assert encrypter.decrypt(encrypter.encrypt(b"sk-secret")) == b"sk-secret"

    def test_missing_key_raises_with_generation_hint(self, monkeypatch):
        monkeypatch.setattr(
            encryption.settings, "key_encryption_key", "", raising=False
        )
        with pytest.raises(ValueError, match="Fernet.generate_key"):
            encryption.get_encrypter()

    @pytest.mark.parametrize(
        "bad_key",
        [
            # What the old .env.example told operators to generate.
            "a" * 64,
            # 32 raw bytes: the old length check accepted this, then Fernet
            # raised an opaque error.
            "b" * 32,
            # Truncated base64.
            "c" * 43,
            # Too short.
            "d" * 16,
        ],
    )
    def test_malformed_key_raises_instead_of_regenerating(self, bad_key, monkeypatch):
        """A bad key must fail loudly, never be silently replaced.

        Regenerating produced a different encrypter per process, so every
        stored provider sub-key became unreadable with no error raised.
        """
        monkeypatch.setattr(
            encryption.settings, "key_encryption_key", bad_key, raising=False
        )
        with pytest.raises(ValueError, match="malformed"):
            encryption.get_encrypter()

    def test_error_names_the_wrong_generation_command(self, monkeypatch):
        """The old hint (secrets.token_hex) produces a key Fernet rejects."""
        monkeypatch.setattr(
            encryption.settings, "key_encryption_key", "e" * 64, raising=False
        )
        with pytest.raises(ValueError) as exc:
            encryption.get_encrypter()
        assert "token_hex" in str(exc.value)

    def test_same_key_gives_stable_ciphertext_across_calls(self, valid_key, monkeypatch):
        """Deterministic across instances: the same key must round-trip."""
        monkeypatch.setattr(
            encryption.settings, "key_encryption_key", valid_key, raising=False
        )
        first = encryption.get_encrypter().encrypt(b"sk-secret")
        second = encryption.get_encrypter()
        assert second.decrypt(first) == b"sk-secret"
