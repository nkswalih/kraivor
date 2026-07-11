"""
WebSocket URL routing for the Chat app.

Maps URL patterns to Channels consumers.
"""

from django.urls import re_path

from apps.chat.consumers import ChatConsumer, NotificationConsumer, PresenceConsumer
from apps.chat.consumers_v2 import ChatV2Consumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>[^/]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/chat/v2/$", ChatV2Consumer.as_asgi()),
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
    re_path(r"ws/presence/$", PresenceConsumer.as_asgi()),
]
