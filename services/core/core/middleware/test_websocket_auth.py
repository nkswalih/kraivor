"""Tests for the WebSocket JWT authentication middleware.

This middleware had no tests. It gates every chat WebSocket connection, so
its close codes and its accept/reject decision are the security boundary.

Two defects are pinned here:

1. A signature-valid token carrying no subject claim (`sub` and `user_id`
   both absent) produced `scope["user_id"] = None` and the handshake was
   allowed through. Consumers each re-checked `if not self.user_id` and
   closed 4001 themselves, which meant the authorization decision lived in
   four consumers rather than one place.

2. The success path returned `await super().__call__(...)` while every
   rejection path used a bare `return`, so the function mixed implicit and
   explicit returns (CodeQL py/mixed-returns).

The core service has no pytest-asyncio plugin, so each test is synchronous
and drives the coroutine with asyncio.run.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from django.conf import settings

from core.middleware.websocket_auth import JWTAuthMiddleware

pytestmark = pytest.mark.security

CLOSE_NO_TOKEN = 4001
CLOSE_EXPIRED = 4002
CLOSE_INVALID = 4003
CLOSE_GENERIC = 4001
CLOSE_NO_SUBJECT = 4001


def _scope(subprotocols=None, query_string=b""):
    scope = {"type": "websocket", "subprotocols": subprotocols or []}
    if query_string:
        scope["query_string"] = query_string
    return scope


def _run(monkeypatch, verify, scope):
    """Drive one handshake with _verify_token stubbed.

    The base middleware __call__ is stubbed too, so these tests assert on the
    auth decision rather than on Channels internals. Its return value,
    "downstream-called", marks the accepted path.
    """
    mw = JWTAuthMiddleware(lambda s, r, se: None)
    monkeypatch.setattr(JWTAuthMiddleware, "_verify_token", staticmethod(verify))
    monkeypatch.setattr(
        "channels.middleware.BaseMiddleware.__call__",
        AsyncMock(return_value="downstream-called"),
    )
    send = AsyncMock()

    async def go():
        return await mw(scope, AsyncMock(), send)

    result = asyncio.run(go())
    return result, send


class TestTokenExtraction:
    def test_reads_token_from_subprotocol(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "the-jwt"])
        seen = {}

        def verify(token):
            seen["token"] = token
            return {"sub": "u1"}

        result, send = _run(monkeypatch, verify, scope)

        assert seen["token"] == "the-jwt"
        assert result == "downstream-called"
        send.assert_not_called()

    def test_falls_back_to_query_string(self, monkeypatch):
        scope = _scope(query_string=b"token=from-query")
        seen = {}

        def verify(token):
            seen["token"] = token
            return {"sub": "u1"}

        _run(monkeypatch, verify, scope)

        assert seen["token"] == "from-query"

    def test_subprotocol_wins_over_query_string(self, monkeypatch):
        """The subprotocol method exists to avoid URL exposure, so it must
        take precedence when both are present."""
        scope = _scope(
            subprotocols=["auth", "from-sub"], query_string=b"token=from-query"
        )
        seen = {}

        def verify(token):
            seen["token"] = token
            return {"sub": "u1"}

        _run(monkeypatch, verify, scope)

        assert seen["token"] == "from-sub"


class TestRejectionPaths:
    def test_missing_token_closes_without_calling_verify(self, monkeypatch):
        called = []

        def verify(token):
            called.append(token)
            return {"sub": "u1"}

        result, send = _run(monkeypatch, verify, _scope())

        assert result is None
        assert called == []
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_NO_TOKEN}
        )

    def test_single_subprotocol_is_not_enough(self, monkeypatch):
        """['auth'] alone carries no token — must not be treated as one."""
        result, send = _run(
            monkeypatch, lambda t: {"sub": "u1"}, _scope(subprotocols=["auth"])
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_NO_TOKEN}
        )

    def test_wrong_leading_subprotocol_falls_through_to_query(self, monkeypatch):
        scope = _scope(
            subprotocols=["nope", "tok"], query_string=b"token=real"
        )
        seen = {}

        def verify(token):
            seen["token"] = token
            return {"sub": "u1"}

        _run(monkeypatch, verify, scope)

        assert seen["token"] == "real"

    def test_expired_token_closes_4002(self, monkeypatch):
        def verify(token):
            raise jwt.ExpiredSignatureError("expired")

        result, send = _run(
            monkeypatch, verify, _scope(subprotocols=["auth", "t"])
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_EXPIRED}
        )

    def test_invalid_token_closes_4003(self, monkeypatch):
        def verify(token):
            raise jwt.InvalidTokenError("bad sig")

        result, send = _run(
            monkeypatch, verify, _scope(subprotocols=["auth", "t"])
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_INVALID}
        )

    def test_unexpected_error_closes_4001(self, monkeypatch):
        """A JWKS fetch failure must close, not fall through to the consumer."""

        def verify(token):
            raise RuntimeError("jwks unreachable")

        result, send = _run(
            monkeypatch, verify, _scope(subprotocols=["auth", "t"])
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_GENERIC}
        )

    def test_each_rejection_path_uses_its_own_close_code(self, monkeypatch):
        """The three JWT error classes must not collapse into one code.

        A client that cannot distinguish expired (retry after refresh) from
        invalid (re-authenticate) from server error (retry) cannot behave
        correctly, so the mapping is pinned.
        """
        codes = set()
        for exc, expected in (
            (jwt.ExpiredSignatureError("e"), CLOSE_EXPIRED),
            (jwt.InvalidTokenError("i"), CLOSE_INVALID),
            (RuntimeError("boom"), CLOSE_GENERIC),
        ):
            def verify(token, exc=exc):
                raise exc

            _, send = _run(monkeypatch, verify, _scope(subprotocols=["auth", "t"]))
            codes.add(send.await_args[0][0]["code"])
            assert send.await_args[0][0]["code"] == expected

        # 4001 and 4003 are distinct; only the generic bucket shares with
        # no-subject and no-token.
        assert codes == {CLOSE_EXPIRED, CLOSE_INVALID, CLOSE_GENERIC}


class TestSubjectClaimIsRequired:
    """A signature-valid token with no subject identifies nobody."""

    def test_token_without_sub_is_rejected(self, monkeypatch):
        """The defect: this used to reach the downstream consumer with
        scope['user_id'] = None."""
        result, send = _run(
            monkeypatch,
            lambda t: {"email": "a@b.c"},
            _scope(subprotocols=["auth", "t"]),
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_NO_SUBJECT}
        )

    def test_empty_sub_is_rejected(self, monkeypatch):
        result, send = _run(
            monkeypatch,
            lambda t: {"sub": "", "user_id": ""},
            _scope(subprotocols=["auth", "t"]),
        )

        assert result is None
        send.assert_awaited_once_with(
            {"type": "websocket.close", "code": CLOSE_NO_SUBJECT}
        )

    def test_sub_is_used_when_present(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "t"])
        _run(monkeypatch, lambda t: {"sub": "from-sub"}, scope)
        assert scope["user_id"] == "from-sub"

    def test_user_id_is_the_fallback_claim(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "t"])
        _run(monkeypatch, lambda t: {"user_id": "from-user-id"}, scope)
        assert scope["user_id"] == "from-user-id"

    def test_sub_takes_precedence_over_user_id(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "t"])
        _run(
            monkeypatch,
            lambda t: {"sub": "primary", "user_id": "secondary"},
            scope,
        )
        assert scope["user_id"] == "primary"


class TestScopePopulation:
    def test_populates_all_scope_keys_on_success(self, monkeypatch):
        payload = {
            "sub": "u1",
            "name": "Ada",
            "email": "ada@example.com",
            "workspace_ids": ["w1", "w2"],
            "roles": {"admin": True},
        }
        scope = _scope(subprotocols=["auth", "t"])

        _run(monkeypatch, lambda t: payload, scope)

        assert scope["user_id"] == "u1"
        assert scope["user_name"] == "Ada"
        assert scope["email"] == "ada@example.com"
        assert scope["workspace_ids"] == ["w1", "w2"]
        assert scope["roles"] == {"admin": True}
        assert scope["jwt_payload"] == payload

    def test_user_name_falls_back_to_email(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "t"])
        _run(monkeypatch, lambda t: {"sub": "u1", "email": "x@y.z"}, scope)
        assert scope["user_name"] == "x@y.z"

    def test_missing_optional_claims_get_defaults(self, monkeypatch):
        scope = _scope(subprotocols=["auth", "t"])
        _run(monkeypatch, lambda t: {"sub": "u1"}, scope)

        assert scope["user_name"] == ""
        assert scope["email"] is None
        assert scope["workspace_ids"] == []
        assert scope["roles"] == {}

    def test_no_scope_keys_written_on_rejection(self, monkeypatch):
        """A rejected handshake must not leave partial identity data behind."""
        scope = _scope(subprotocols=["auth", "t"])
        _run(
            monkeypatch,
            lambda t: (_ for _ in ()).throw(jwt.InvalidTokenError("x")),
            scope,
        )

        for key in (
            "user_id",
            "user_name",
            "email",
            "workspace_ids",
            "roles",
            "jwt_payload",
        ):
            assert key not in scope

    def test_no_scope_keys_written_when_subject_missing(self, monkeypatch):
        """The no-subject path must not write identity keys either."""
        scope = _scope(subprotocols=["auth", "t"])
        _run(monkeypatch, lambda t: {"email": "a@b.c"}, scope)

        for key in ("user_id", "user_name", "jwt_payload"):
            assert key not in scope


class TestTokenVerification:
    """_verify_token decodes against the JWKS signing key."""

    def test_token_signed_by_a_different_key_is_invalid(self):
        """A wrong-signature token must surface as InvalidTokenError so the
        middleware picks close code 4003, not the generic 4001."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        token = jwt.encode(
            {
                "sub": "u1",
                "aud": settings.JWT_AUDIENCE,
                "iss": settings.JWT_ISSUER,
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "some-other-key"},
        )

        # The JWKS client hands back a *different* key.
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = other.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        jwks_client = type(
            "FakeJWKS",
            (),
            {
                "get_signing_key_from_jwt": staticmethod(
                    lambda t: type("K", (), {"key": public_pem})()
                )
            },
        )()

        with patch(
            "core.middleware.websocket_auth._get_jwks_client",
            return_value=jwks_client,
        ), pytest.raises(jwt.InvalidTokenError):
            JWTAuthMiddleware._verify_token(token)

    def test_valid_token_returns_payload(self):
        """Round trip: sign with a key, verify against the matching JWKS."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        token = jwt.encode(
            {
                "sub": "u1",
                "email": "u1@example.com",
                "aud": settings.JWT_AUDIENCE,
                "iss": settings.JWT_ISSUER,
                "exp": 9999999999,
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "k1"},
        )

        jwks_client = type(
            "FakeJWKS",
            (),
            {
                "get_signing_key_from_jwt": staticmethod(
                    lambda t: type("K", (), {"key": public_pem})()
                )
            },
        )()

        with patch(
            "core.middleware.websocket_auth._get_jwks_client",
            return_value=jwks_client,
        ):
            payload = JWTAuthMiddleware._verify_token(token)

        assert payload["sub"] == "u1"
        assert payload["email"] == "u1@example.com"

    def test_expired_token_raises_expired_signature_error(self):
        """The 4002 path depends on jwt.ExpiredSignatureError being raised
        specifically, not a subclass of InvalidTokenError handled first."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        token = jwt.encode(
            {
                "sub": "u1",
                "aud": settings.JWT_AUDIENCE,
                "iss": settings.JWT_ISSUER,
                "exp": 1000000000,  # 2001
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "k1"},
        )

        jwks_client = type(
            "FakeJWKS",
            (),
            {
                "get_signing_key_from_jwt": staticmethod(
                    lambda t: type("K", (), {"key": public_pem})()
                )
            },
        )()

        with patch(
            "core.middleware.websocket_auth._get_jwks_client",
            return_value=jwks_client,
        ), pytest.raises(jwt.ExpiredSignatureError):
            JWTAuthMiddleware._verify_token(token)
