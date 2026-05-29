"""Unit tests for SHA-256 hasher and constant-time compare."""

from api_keys.services.generator import generate_api_key
from api_keys.services.hasher import hash_api_key, verify_api_key


class TestHashAPIKey:
    def test_returns_64_char_hex(self):
        result = hash_api_key("krv_live_" + "a" * 64)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self):
        key = generate_api_key()
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_keys_different_hashes(self):
        k1, k2 = generate_api_key(), generate_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)


class TestVerifyAPIKey:
    def test_correct_key_passes(self):
        raw = generate_api_key()
        stored = hash_api_key(raw)
        assert verify_api_key(raw, stored) is True

    def test_wrong_key_fails(self):
        raw = generate_api_key()
        stored = hash_api_key(generate_api_key())  # different key's hash
        assert verify_api_key(raw, stored) is False

    def test_tampered_key_fails(self):
        raw = generate_api_key()
        stored = hash_api_key(raw)
        tampered = raw[:-1] + ("b" if raw[-1] != "b" else "c")
        assert verify_api_key(tampered, stored) is False