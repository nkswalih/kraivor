from django.contrib import admin

from .models import Comment, Discussion, Tag, Vote


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ["title", "author_username", "upvote_count", "comment_count", "is_pinned", "created_at"]
    list_filter = ["is_pinned", "is_locked", "is_resolved", "created_at"]
    search_fields = ["title", "body", "author_username"]
    readonly_fields = ["id", "author_id", "upvote_count", "downvote_count", "comment_count", "created_at", "updated_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "discussion", "author_username", "upvote_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["body", "author_username"]
    readonly_fields = ["id", "author_id", "upvote_count", "downvote_count", "created_at", "updated_at"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "usage_count", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ["user_id", "discussion", "comment", "value", "created_at"]
    list_filter = ["value", "created_at"]
