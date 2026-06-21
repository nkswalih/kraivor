"""
ASGI application for the Core Service.

Routes HTTP requests to Django and WebSocket connections to Channels consumers.
Used by uvicorn in development and production.

    uvicorn core.asgi:application --host 0.0.0.0 --port 8002 --reload
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")

django_asgi = get_asgi_application()

from apps.chat import routing as chat_routing  # noqa: E402
from core.middleware.websocket_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": JWTAuthMiddleware(URLRouter(chat_routing.websocket_urlpatterns)),
    }
)
