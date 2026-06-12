from django.urls import path

from apps.chat.views import ChatRoomViewSet, MessageViewSet

chat_rooms_list = ChatRoomViewSet.as_view({"get": "list", "post": "create"})

chat_rooms_detail = ChatRoomViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

messages_list = MessageViewSet.as_view({"get": "list", "post": "send"})

messages_detail = MessageViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

messages_search = MessageViewSet.as_view({"get": "search"})

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_pk>/chat/rooms/",
        chat_rooms_list,
        name="chat-room-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/chat/rooms/<uuid:pk>/",
        chat_rooms_detail,
        name="chat-room-detail",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/",
        messages_list,
        name="chat-message-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/search/",
        messages_search,
        name="chat-message-search",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/chat/rooms/<uuid:room_pk>/messages/<uuid:pk>/",
        messages_detail,
        name="chat-message-detail",
    ),
]
