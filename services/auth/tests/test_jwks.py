"""
Tests for KRV-012 — JWKS Endpoint

Covers:
  - GET /.well-known/jwks.json returns public key in JWK format
  - Cache-Control header set to 1 hour
  - JWK format validation
"""

from datetime import UTC
from pathlib import Path

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.authentication.jwks import JWKSView


def generate_test_rsa_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


class TestJWKSView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.private_pem, self.public_pem = generate_test_rsa_keypair()

    @override_settings(JWT_PUBLIC_KEY_PATH="/nonexistent/key.pem")
    def test_returns_500_when_key_not_found(self):
        JWKSView.invalidate_cache()
        response = self.client.get("/.well-known/jwks.json")
        self.assertIn(response.status_code, [500, 503])

    def test_returns_valid_jwks_response(self):
        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        key_path = temp_dir / "jwt-public.pem"

        try:
            with open(key_path, "wb") as f:
                f.write(self.public_pem)

            with override_settings(JWT_PUBLIC_KEY_PATH=str(key_path)):
                JWKSView.invalidate_cache()
                response = self.client.get("/.well-known/jwks.json")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("keys", data)
            self.assertEqual(len(data["keys"]), 1)

            jwk = data["keys"][0]
            self.assertEqual(jwk["kty"], "RSA")
            self.assertEqual(jwk["use"], "sig")
            self.assertEqual(jwk["alg"], "RS256")
            self.assertIn("n", jwk)
            self.assertIn("e", jwk)
            self.assertIn("kid", jwk)
        finally:
            if key_path.exists():
                key_path.unlink()

    def test_cache_control_header_set(self):
        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        key_path = temp_dir / "jwt-public.pem"

        try:
            with open(key_path, "wb") as f:
                f.write(self.public_pem)

            with override_settings(JWT_PUBLIC_KEY_PATH=str(key_path)):
                JWKSView.invalidate_cache()
                response = self.client.get("/.well-known/jwks.json")

            cache_header = response["Cache-Control"]
            self.assertIn("max-age=3600", cache_header)
            self.assertIn("public", cache_header)
        finally:
            if key_path.exists():
                key_path.unlink()

    def test_caching_works(self):
        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        key_path = temp_dir / "jwt-public.pem"

        try:
            with open(key_path, "wb") as f:
                f.write(self.public_pem)

            with override_settings(JWT_PUBLIC_KEY_PATH=str(key_path)):
                JWKSView.invalidate_cache()
                response1 = self.client.get("/.well-known/jwks.json")
                response2 = self.client.get("/.well-known/jwks.json")

            self.assertEqual(response1.status_code, 200)
            self.assertEqual(response2.status_code, 200)
            self.assertEqual(response1.json(), response2.json())
        finally:
            if key_path.exists():
                key_path.unlink()

    def test_jwk_format_has_correct_structure(self):
        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        key_path = temp_dir / "jwt-public.pem"

        try:
            with open(key_path, "wb") as f:
                f.write(self.public_pem)

            with override_settings(JWT_PUBLIC_KEY_PATH=str(key_path)):
                JWKSView.invalidate_cache()
                response = self.client.get("/.well-known/jwks.json")

            jwk = response.json()["keys"][0]
            self.assertEqual(jwk["kty"], "RSA")
            self.assertIn("n", jwk)
            self.assertIn("e", jwk)
            self.assertGreater(len(jwk["n"]), 300)
            self.assertLess(len(jwk["e"]), 10)
        finally:
            if key_path.exists():
                key_path.unlink()


class TestJWKSViewUnit(TestCase):
    def setUp(self):
        self.private_pem, self.public_pem = generate_test_rsa_keypair()

    def test_public_key_to_jwk_conversion(self):
        from cryptography.hazmat.primitives import serialization

        public_key = serialization.load_pem_public_key(self.public_pem)
        jwk = JWKSView._public_key_to_jwk(public_key)

        self.assertEqual(jwk["kty"], "RSA")
        self.assertEqual(jwk["use"], "sig")
        self.assertEqual(jwk["alg"], "RS256")
        self.assertIn("n", jwk)
        self.assertIn("e", jwk)
        self.assertIn("kid", jwk)

    def test_base64url_encoding(self):
        test_data = b"test data with special chars!@#$%"
        encoded = JWKSView._base64url_encode(test_data)
        self.assertIsInstance(encoded, str)
        self.assertFalse(encoded.endswith("="))

    def test_cache_invalidation(self):
        JWKSView._cached_jwks = {"test": "data"}
        JWKSView.invalidate_cache()
        self.assertIsNone(JWKSView._cached_jwks)


class TestIntegrationEndToEndJWT(TestCase):
    """
    Integration test: Identity issues token, Core/Analysis/AI services verify it.

    This test simulates the full flow:
    1. Identity Service generates JWT using private key
    2. JWKS endpoint exposes public key in JWK format
    3. Other services fetch JWKS and verify the JWT
    """

    def setUp(self):
        self.private_pem, self.public_pem = generate_test_rsa_keypair()

    def test_identity_issues_token_core_verifies(self):
        from datetime import datetime, timedelta

        import jwt

        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        public_key_path = temp_dir / "jwt-public.pem"
        private_key_path = temp_dir / "jwt-private.pem"

        try:
            # Save keys for JWKS endpoint
            with open(public_key_path, "wb") as f:
                f.write(self.public_pem)
            with open(private_key_path, "wb") as f:
                f.write(self.private_pem)

            # Step 1: Identity Service issues a JWT
            payload = {
                "sub": "user-integration-123",
                "email": "integration@kraivor.test",
                "workspace_ids": ["ws-integration-1", "ws-integration-2"],
                "roles": {"ws-integration-1": "owner", "ws-integration-2": "member"},
                "token_type": "access",
                "iat": datetime.now(UTC),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "aud": "kraivor",
                "iss": "kraivor-identity",
            }

            with override_settings(JWT_PUBLIC_KEY_PATH=str(public_key_path)):
                JWKSView.invalidate_cache()
                token = jwt.encode(payload, self.private_pem, algorithm="RS256")

            # Step 2: JWKS endpoint returns public key
            with override_settings(JWT_PUBLIC_KEY_PATH=str(public_key_path)):
                JWKSView.invalidate_cache()
                jwks = JWKSView._get_jwks()
                jwk = jwks["keys"][0]

            # Step 3: Core/Analysis/AI services verify the token using JWKS
            import base64

            from cryptography.hazmat.primitives.asymmetric import rsa

            # Convert JWK back to public key for verification
            def b64url_decode(data: str) -> bytes:
                return base64.urlsafe_b64decode(data + "=" * (4 - len(data) % 4))

            n = int.from_bytes(b64url_decode(jwk["n"]), "big")
            e = int.from_bytes(b64url_decode(jwk["e"]), "big")
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key()

            # Verify the token
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="kraivor",
                issuer="kraivor-identity",
            )

            # Verify claims
            self.assertEqual(decoded["sub"], "user-integration-123")
            self.assertEqual(decoded["email"], "integration@kraivor.test")
            self.assertEqual(decoded["workspace_ids"], ["ws-integration-1", "ws-integration-2"])
            self.assertEqual(decoded["roles"]["ws-integration-1"], "owner")

        finally:
            if public_key_path.exists():
                public_key_path.unlink()
            if private_key_path.exists():
                private_key_path.unlink()

    def test_expired_token_is_rejected(self):
        from datetime import datetime, timedelta

        import jwt

        temp_dir = Path(__file__).parent.parent / ".keys"
        temp_dir.mkdir(exist_ok=True)
        public_key_path = temp_dir / "jwt-public.pem"
        private_key_path = temp_dir / "jwt-private.pem"

        try:
            with open(public_key_path, "wb") as f:
                f.write(self.public_pem)
            with open(private_key_path, "wb") as f:
                f.write(self.private_pem)

            # Create expired token
            payload = {
                "sub": "user-expired",
                "email": "expired@kraivor.test",
                "token_type": "access",
                "iat": datetime.now(UTC) - timedelta(hours=2),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "aud": "kraivor",
                "iss": "kraivor-identity",
            }

            with override_settings(JWT_PUBLIC_KEY_PATH=str(public_key_path)):
                JWKSView.invalidate_cache()
                token = jwt.encode(payload, self.private_pem, algorithm="RS256")
                jwks = JWKSView._get_jwks()

            # Try to decode - should fail with ExpiredSignatureError
            import base64

            from cryptography.hazmat.primitives.asymmetric import rsa

            jwk = jwks["keys"][0]

            def b64url_decode(data: str) -> bytes:
                return base64.urlsafe_b64decode(data + "=" * (4 - len(data) % 4))

            n = int.from_bytes(b64url_decode(jwk["n"]), "big")
            e = int.from_bytes(b64url_decode(jwk["e"]), "big")
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key()

            with self.assertRaises(jwt.ExpiredSignatureError):
                jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience="kraivor",
                    issuer="kraivor-identity",
                )

        finally:
            if public_key_path.exists():
                public_key_path.unlink()
            if private_key_path.exists():
                private_key_path.unlink()
