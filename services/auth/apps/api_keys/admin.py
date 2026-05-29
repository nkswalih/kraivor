"""
Admin configuration for the API Keys app.

Provides admin interfaces for:
- APIKey: Key lifecycle management, scope assignment, revocation
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now

from .models import APIKey

# ---------------------------------------------------------------------------
# APIKey Admin
# ---------------------------------------------------------------------------

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """
    API key management admin with:
    - Key status tracking (active/expired/revoked)
    - Scope visualization
    - Usage tracking (last_used_at)
    - Bulk revocation actions
    - Read-only key hash (security)
    """

    list_display = (
        "id_short",
        "name",
        "user_email",
        "prefix",
        "scopes_display",
        "status_badge",
        "last_used_at",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "revoked",
        "scopes",
        ("created_at", admin.DateFieldListFilter),
        ("expires_at", admin.DateFieldListFilter),
    )

    search_fields = (
        "name",
        "user__email",
        "user__name",
        "prefix",
    )

    readonly_fields = (
        "id",
        "key_hash",
        "prefix",
        "user",
        "created_at",
        "updated_at",
        "last_used_at",
    )

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Key", {
            "fields": ("id", "name", "prefix", "key_hash")
        }),
        ("Owner", {
            "fields": ("user",)
        }),
        ("Permissions", {
            "fields": ("scopes",)
        }),
        ("Lifecycle", {
            "fields": ("revoked", "expires_at", "last_used_at", "created_at", "updated_at")
        }),
    )

    # -----------------------------------------------------------------------
    # Custom display methods
    # -----------------------------------------------------------------------

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = "ID"

    def user_email(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/users/user/{obj.user_id}/change/",
            obj.user.email,
        )
    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"

    def scopes_display(self, obj):
        if not obj.scopes:
            return format_html('<span style="color: #999;">No scopes</span>')
        badges = []
        for scope in obj.scopes:
            badges.append(
                format_html(
                    '<span style="background: #e0e7ff; color: #3730a3; '
                    'padding: 2px 6px; border-radius: 4px; font-size: 11px; '
                    'margin-right: 4px;">{}</span>',
                    scope,
                )
            )
        return format_html("".join(badges))
    scopes_display.short_description = "Scopes"
    scopes_display.allow_tags = True

    def status_badge(self, obj):
        if obj.revoked:
            return format_html(
                '<span style="color: #ef4444; font-weight: bold;">Revoked</span>'
            )
        if obj.expires_at and obj.expires_at < now():
            return format_html(
                '<span style="color: #f59e0b; font-weight: bold;">Expired</span>'
            )
        return format_html(
            '<span style="color: #22c55e; font-weight: bold;">Active</span>'
        )
    status_badge.short_description = "Status"

    # -----------------------------------------------------------------------
    # Queryset optimization
    # -----------------------------------------------------------------------

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    # -----------------------------------------------------------------------
    # Bulk actions
    # -----------------------------------------------------------------------

    actions = [
        "revoke_selected",
        "revoke_expired",
        "revoke_all_for_user",
    ]

    def revoke_selected(self, request, queryset):
        count = queryset.filter(revoked=False).update(revoked=True)
        self.message_user(request, f"{count} API key(s) revoked.", messages.SUCCESS)
    revoke_selected.short_description = "Revoke selected API keys"

    def revoke_expired(self, request, queryset):
        count = queryset.filter(
            revoked=False,
            expires_at__lt=now(),
        ).update(revoked=True)
        self.message_user(request, f"{count} expired API key(s) revoked.", messages.SUCCESS)
    revoke_expired.short_description = "Revoke all expired API keys"

    def revoke_all_for_user(self, request, queryset):
        user_ids = queryset.values_list("user_id", flat=True).distinct()
        count = APIKey.objects.filter(
            user_id__in=user_ids,
            revoked=False,
        ).update(revoked=True)
        self.message_user(
            request,
            f"{count} API key(s) revoked for {user_ids.count()} user(s).",
            messages.SUCCESS,
        )
    revoke_all_for_user.short_description = "Revoke all API keys for these users"
