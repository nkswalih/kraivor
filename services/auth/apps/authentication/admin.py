"""
Admin configuration for the Authentication app.

Provides admin interfaces for:
- RefreshToken: Session management, device tracking, revocation
- OAuthIdentity: OAuth provider linkage management
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now

from .models import OAuthIdentity, RefreshToken

# ---------------------------------------------------------------------------
# RefreshToken Admin
# ---------------------------------------------------------------------------


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    """
    Session management admin with:
    - Device and IP tracking
    - Active/expired/revoked filtering
    - Bulk revocation actions
    - Read-only token hash (security)
    """

    list_display = (
        "id_short",
        "user_email",
        "device_info",
        "ip_address",
        "status_badge",
        "created_at",
        "last_used_at",
        "expires_at",
    )

    list_filter = (
        "revoked",
        "device_type",
        ("created_at", admin.DateFieldListFilter),
        ("expires_at", admin.DateFieldListFilter),
    )

    search_fields = (
        "user__email",
        "user__name",
        "device_id",
        "ip_address",
        "device_name",
    )

    readonly_fields = ("id", "token_hash", "user", "created_at", "last_used_at")

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Token", {"fields": ("id", "token_hash")}),
        ("User", {"fields": ("user",)}),
        (
            "Device",
            {
                "fields": (
                    "device_id",
                    "device_name",
                    "device_type",
                    "ip_address",
                    "user_agent",
                )
            },
        ),
        ("Status", {"fields": ("revoked", "expires_at", "last_used_at", "created_at")}),
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

    def device_info(self, obj):
        parts = []
        if obj.device_name:
            parts.append(obj.device_name)
        if obj.device_type:
            parts.append(f"({obj.device_type})")
        return " ".join(parts) or "—"

    device_info.short_description = "Device"

    def status_badge(self, obj):
        if obj.revoked:
            return format_html(
                '<span style="color: #ef4444; font-weight: bold;">Revoked</span>'
            )
        if obj.expires_at < now():
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

    actions = ["revoke_selected", "revoke_expired", "revoke_all_for_user"]

    def revoke_selected(self, request, queryset):
        count = queryset.filter(revoked=False).update(revoked=True)
        self.message_user(request, f"{count} session(s) revoked.", messages.SUCCESS)

    revoke_selected.short_description = "Revoke selected sessions"

    def revoke_expired(self, request, queryset):
        count = queryset.filter(revoked=False, expires_at__lt=now()).update(
            revoked=True
        )
        self.message_user(
            request, f"{count} expired session(s) revoked.", messages.SUCCESS
        )

    revoke_expired.short_description = "Revoke all expired sessions"

    def revoke_all_for_user(self, request, queryset):
        user_ids = queryset.values_list("user_id", flat=True).distinct()
        count = RefreshToken.objects.filter(user_id__in=user_ids, revoked=False).update(
            revoked=True
        )
        self.message_user(
            request,
            f"{count} session(s) revoked for {user_ids.count()} user(s).",
            messages.SUCCESS,
        )

    revoke_all_for_user.short_description = "Revoke all sessions for these users"


# ---------------------------------------------------------------------------
# OAuthIdentity Admin
# ---------------------------------------------------------------------------


@admin.register(OAuthIdentity)
class OAuthIdentityAdmin(admin.ModelAdmin):
    """
    OAuth identity management with:
    - Provider filtering
    - User linkage
    - Token expiration tracking
    - Soft-delete visibility
    """

    list_display = (
        "id_short",
        "user_email",
        "provider_badge",
        "provider_user_id",
        "provider_email",
        "token_status",
        "created_at",
    )

    list_filter = ("provider", ("created_at", admin.DateFieldListFilter))

    search_fields = ("user__email", "user__name", "provider_user_id", "provider_email")

    readonly_fields = ("id", "user", "raw_data", "created_at", "updated_at")

    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Identity",
            {"fields": ("id", "provider", "provider_user_id", "provider_email")},
        ),
        ("User", {"fields": ("user",)}),
        (
            "Tokens",
            {
                "fields": (
                    "access_token_encrypted",
                    "refresh_token_encrypted",
                    "expires_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("raw_data", "deleted_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
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

    def provider_badge(self, obj):
        colors = {"github": "#6e40c9", "google": "#4285f4", "apple": "#000000"}
        color = colors.get(obj.provider, "#666")
        return format_html(
            '<span style="color: {}; font-weight: bold; text-transform: uppercase;">{}</span>',
            color,
            obj.provider,
        )

    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = "provider"

    def token_status(self, obj):
        if not obj.expires_at:
            return "—"
        if obj.expires_at < now():
            return format_html('<span style="color: #ef4444;">Expired</span>')
        return format_html('<span style="color: #22c55e;">Valid</span>')

    token_status.short_description = "Token Status"

    # -----------------------------------------------------------------------
    # Queryset optimization
    # -----------------------------------------------------------------------

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    # -----------------------------------------------------------------------
    # Bulk actions
    # -----------------------------------------------------------------------

    actions = ["soft_delete_selected", "restore_selected"]

    def soft_delete_selected(self, request, queryset):
        count = queryset.filter(deleted_at__isnull=True).update(deleted_at=now())
        self.message_user(
            request, f"{count} OAuth identity(ies) soft-deleted.", messages.WARNING
        )

    soft_delete_selected.short_description = "Soft-delete selected identities"

    def restore_selected(self, request, queryset):
        count = queryset.filter(deleted_at__isnull=False).update(deleted_at=None)
        self.message_user(
            request, f"{count} OAuth identity(ies) restored.", messages.SUCCESS
        )

    restore_selected.short_description = "Restore selected identities"
