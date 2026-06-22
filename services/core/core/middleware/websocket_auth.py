"""
WebSocket JWT authentication middleware for Django Channels.

Extracts JWT from the WebSocket query string (?token=...), verifies it
against the Identity Service JWKS endpoint, and attaches user info to
the scope.

Usage:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from core.middleware.websocket_auth import JWTAuthMiddleware

    application = ProtocolTypeRouter({
        "websocket": JWTAuthMiddleware(URLRouter(...)),
    })
"""

import jwt
import logging
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from urllib.parse import parse_qs

from core.middleware.jwt_auth import _get_jwks_client

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            logger.warning("websocket.auth.no_token")
            await send({"type": "websocket.close", "code": 4001})
            return

        try:
            payload = await database_sync_to_async(self._verify_token)(token)
            scope["user_id"] = payload.get("sub") or payload.get("user_id")
            scope["user_name"] = payload.get("name") or payload.get("email", "")
            scope["email"] = payload.get("email")
            scope["workspace_ids"] = payload.get("workspace_ids", [])
            scope["roles"] = payload.get("roles", {})
            scope["jwt_payload"] = payload
        except jwt.ExpiredSignatureError:
            logger.warning("websocket.auth.token_expired")
            await send({"type": "websocket.close", "code": 4002})
            return
        except jwt.InvalidTokenError as exc:
            logger.warning("websocket.auth.invalid_token: %s", exc)
            await send({"type": "websocket.close", "code": 4003})
            return
        except Exception as exc:
            logger.error("websocket.auth.error: %s", exc, exc_info=True)
            await send({"type": "websocket.close", "code": 4001})
            return

        return await super().__call__(scope, receive, send)

    @staticmethod
    def _verify_token(token: str) -> dict:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        decode_options = {
            "verify_exp": getattr(settings, "JWT_VERIFY_EXPIRATION", True)
        }
        audience = getattr(settings, "JWT_AUDIENCE", None)
        issuer = getattr(settings, "JWT_ISSUER", None)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=audience,
            issuer=issuer,
            options=decode_options,
        )
        return payload
