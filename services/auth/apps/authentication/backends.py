import logging

import jwt
from django.conf import settings
from rest_framework_simplejwt.backends import TokenBackend as BaseTokenBackend

logger = logging.getLogger(__name__)


class JWKSTokenBackend(BaseTokenBackend):
    """
    TokenBackend that injects 'kid' into every JWT header.

    PyJWKClient on downstream services (Core, Analysis, AI)
    reads the 'kid' from the JWT header to match against the
    JWKS endpoint. Without this, kid = None -> PyJWKClientError.

    The kid value must match the 'kid' in the JWKS response
    served by JWKSView at /.well-known/jwks.json.
    """

    def encode(self, payload: dict) -> str:
        jwt_payload = payload.copy()
        if self.audience is not None:
            jwt_payload["aud"] = self.audience
        if self.issuer is not None:
            jwt_payload["iss"] = self.issuer

        kid_value = getattr(settings, "JWT_KEY_ID", None)
        if kid_value is None:
            logger.warning("JWT_KEY_ID is not set — token will have no kid")

        headers = {"kid": kid_value} if kid_value else None

        token = jwt.encode(
            jwt_payload,
            self.prepared_signing_key,
            algorithm=self.algorithm,
            headers=headers,
            json_encoder=self.json_encoder,
        )
        if isinstance(token, bytes):
            return token.decode("utf-8")
        return token
