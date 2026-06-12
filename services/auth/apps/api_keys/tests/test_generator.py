"""Unit tests for API key generator."""

from api_keys.services.generator import (
    API_KEY_PREFIX,
    generate_api_key,
    is_api_key_format,
)


class TestGenerateAPIKey:
    def test_returns_string(self):
        key = generate_api_key()[0]
        assert isinstance(key, str)

    def test_has_correct_prefix(self):
        key = generate_api_key()[0]
        assert key.startswith(API_KEY_PREFIX)

    def test_random_part_is_64_hex_chars(self):
        key = generate_api_key()[0]
        random_part = key[len(API_KEY_PREFIX):]
        assert len(random_part) == 64
        assert all(c in "0123456789abcdef" for c in random_part)

    def test_keys_are_unique(self):
        keys = {generate_api_key()[0] for _ in range(100)}
        assert len(keys) == 100  # no collisions


class TestIsAPIKeyFormat:
    def test_valid_key_passes(self):
        key = generate_api_key()[0]
        assert is_api_key_format(key) is True

    def test_jwt_token_fails(self):
        jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        assert is_api_key_format(jwt) is False

    def test_wrong_prefix_fails(self):
        assert is_api_key_format("sk_live_" + "a" * 64) is False

    def test_too_short_fails(self):
        assert is_api_key_format(f"{API_KEY_PREFIX}{'a' * 32}") is False

    def test_too_long_fails(self):
        assert is_api_key_format(f"{API_KEY_PREFIX}{'a' * 65}") is False

    def test_uppercase_hex_fails(self):
        # keys are lowercase only
        assert is_api_key_format(f"{API_KEY_PREFIX}{'A' * 64}") is False

    def test_empty_string_fails(self):
        assert is_api_key_format("") is False

    def test_none_fails(self):
        assert is_api_key_format(None) is False  # type: ignore