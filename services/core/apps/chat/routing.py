"""
WebSocket URL routing for the Chat app.

Maps URL patterns to Channels consumers.
"""

from django.urls import re_path

from apps.chat.consumers import ChatConsumer, NotificationConsumer, PresenceConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>[^/]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),
    re_path(r"ws/presence/$", PresenceConsumer.as_asgi()),
]
