from django.contrib import admin

from apps.chat.models import ChatRoom


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["name", "room_type", "workspace", "is_active", "created_at", "updated_at"]
    list_filter = ["room_type", "is_active", "workspace"]
    search_fields = ["name", "topic"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
