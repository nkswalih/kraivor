from django.contrib import admin

from .models import Profile, UserFollow


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["username", "display_name", "reputation_score", "followers_count", "is_public", "created_at"]
    list_filter = ["is_public", "created_at"]
    search_fields = ["username", "display_name", "bio"]
    readonly_fields = ["id", "user_id", "reputation_score", "followers_count", "following_count", "discussion_count", "comment_count", "created_at", "updated_at"]


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "following", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["follower__email", "following__email"]
