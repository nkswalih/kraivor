from django.urls import path

from apps.chat.views import (
    DMCreateView,
    MessageDetailView,
    MessageListSendView,
    MessageSearchView,
    RoomDetailView,
    RoomListCreateView,
)

urlpatterns = [
    path(
        "workspaces/<str:workspace_pk>/chat/dm/",
        DMCreateView.as_view(),
        name="chat-room-dm",
    ),
    path(
        "workspaces/<str:workspace_pk>/chat/rooms/",
        RoomListCreateView.as_view(),
        name="chat-room-list",
    ),
    path(
        "workspaces/<str:workspace_pk>/chat/rooms/<uuid:pk>/",
        RoomDetailView.as_view(),
        name="chat-room-detail",
    ),
    path(
        "workspaces/<str:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/",
        MessageListSendView.as_view(),
        name="chat-message-list",
    ),
    path(
        "workspaces/<str:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/search/",
        MessageSearchView.as_view(),
        name="chat-message-search",
    ),
    path(
        "workspaces/<str:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/<uuid:pk>/",
        MessageDetailView.as_view(),
        name="chat-message-detail",
    ),
]
