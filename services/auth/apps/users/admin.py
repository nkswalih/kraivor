"""
Admin configuration for the Users app.

Provides a production-grade Django admin interface for user management
with custom forms, filters, actions, and inline relationships.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.html import format_html

from .models import User

# ---------------------------------------------------------------------------
# User Admin
# ---------------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Production-grade User admin with:
    - Custom list display with status indicators
    - Advanced filtering (verified, active, deleted, staff)
    - Bulk actions (verify, activate, soft-delete, revoke sessions)
    - Inline relationships (OAuth, tokens, API keys)
    - Read-only audit fields
    """

    # Fieldsets — organized by logical group
    fieldsets = (
        (None, {
            "fields": ("email", "password")
        }),
        ("Personal Info", {
            "fields": ("name", "avatar_url")
        }),
        ("Status", {
            "fields": ("email_verified", "is_active", "is_staff", "is_superuser", "deleted_at"),
            "classes": ("collapse",),
        }),
        ("Permissions", {
            "fields": ("groups", "user_permissions"),
            "classes": ("collapse",),
        }),
        ("Audit", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # Add form fieldsets
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2"),
        }),
    )

    # List display
    list_display = (
        "email",
        "name",
        "email_verified_badge",
        "is_active_badge",
        "is_staff_badge",
        "session_count",
        "api_key_count",
        "created_at",
    )

    # List filters
    list_filter = (
        "email_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        ("created_at", admin.DateFieldListFilter),
    )

    # Search
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    date_hierarchy = "created_at"

    # Inlines — set models dynamically to avoid import cycles
    def get_inlines(self, request, obj=None):
        inlines = []

        if obj:
            # Add OAuth identity inline
            from authentication.models import OAuthIdentity

            class OAuthInline(admin.TabularInline):
                model = OAuthIdentity
                extra = 0
                can_delete = True
                readonly_fields = ("provider_user_id", "provider_email", "created_at", "updated_at")
                fields = ("provider", "provider_user_id", "provider_email", "expires_at", "deleted_at", "created_at")

            inlines.append(OAuthInline)

            # Add refresh token inline (active only)
            from authentication.models import RefreshToken

            class RTInline(admin.TabularInline):
                model = RefreshToken
                extra = 0
                can_delete = True
                readonly_fields = ("device_id", "ip_address", "user_agent_short", "created_at", "last_used_at", "expires_at")
                fields = ("device_id", "ip_address", "user_agent_short", "created_at", "last_used_at", "expires_at", "revoked")

                def user_agent_short(self, obj):
                    return (obj.user_agent or "")[:60]
                user_agent_short.short_description = "User Agent"

            inlines.append(RTInline)

            # Add API key inline
            from api_keys.models import APIKey

            class AKInline(admin.TabularInline):
                model = APIKey
                extra = 0
                can_delete = True
                readonly_fields = ("prefix", "scopes_display", "created_at", "last_used_at", "expires_at")
                fields = ("name", "prefix", "scopes_display", "created_at", "last_used_at", "expires_at", "revoked")

                def scopes_display(self, obj):
                    return ", ".join(obj.scopes) if obj.scopes else "—"
                scopes_display.short_description = "Scopes"

            inlines.append(AKInline)

        return inlines

    # -----------------------------------------------------------------------
    # Custom display methods
    # -----------------------------------------------------------------------

    def email_verified_badge(self, obj):
        if obj.email_verified:
            return format_html(
                '<span style="color: #22c55e; font-weight: bold;">Verified</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-weight: bold;">Unverified</span>'
        )
    email_verified_badge.short_description = "Email Status"
    email_verified_badge.admin_order_field = "email_verified"

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #22c55e;">Active</span>'
            )
        return format_html(
            '<span style="color: #ef4444;">Inactive</span>'
        )
    is_active_badge.short_description = "Status"
    is_active_badge.admin_order_field = "is_active"

    def is_staff_badge(self, obj):
        if obj.is_staff:
            return format_html(
                '<span style="color: #3b82f6; font-weight: bold;">Staff</span>'
            )
        return "—"
    is_staff_badge.short_description = "Role"

    def session_count(self, obj):
        count = getattr(obj, "_session_count", obj.refresh_tokens.filter(revoked=False).count())
        return format_html(
            '<a href="{}?user__id__exact={}">{}</a>',
            reverse("admin:authentication_refreshtoken_changelist"),
            obj.id,
            count,
        )
    session_count.short_description = "Sessions"

    def api_key_count(self, obj):
        count = getattr(obj, "_api_key_count", obj.api_keys.filter(revoked=False).count())
        return format_html(
            '<a href="{}?user__id__exact={}">{}</a>',
            reverse("admin:api_keys_apikey_changelist"),
            obj.id,
            count,
        )
    api_key_count.short_description = "API Keys"

    # -----------------------------------------------------------------------
    # Queryset optimization
    # -----------------------------------------------------------------------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with counts to avoid N+1 queries
        return qs.annotate(
            _session_count=Count("refresh_tokens", filter=Q(refresh_tokens__revoked=False)),
            _api_key_count=Count("api_keys", filter=Q(api_keys__revoked=False)),
        )

    # -----------------------------------------------------------------------
    # Bulk actions
    # -----------------------------------------------------------------------

    actions = [
        "verify_emails",
        "activate_users",
        "deactivate_users",
        "soft_delete_users",
        "revoke_all_sessions",
    ]

    def verify_emails(self, request, queryset):
        count = queryset.filter(email_verified=False).update(email_verified=True)
        self.message_user(request, f"{count} user(s) email verified.", messages.SUCCESS)
    verify_emails.short_description = "Verify selected users' emails"

    def activate_users(self, request, queryset):
        count = queryset.filter(is_active=False).update(is_active=True, deleted_at=None)
        self.message_user(request, f"{count} user(s) activated.", messages.SUCCESS)
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f"{count} user(s) deactivated.", messages.WARNING)
    deactivate_users.short_description = "Deactivate selected users"

    def soft_delete_users(self, request, queryset):
        count = 0
        for user in queryset.filter(deleted_at__isnull=True):
            user.soft_delete()
            count += 1
        self.message_user(request, f"{count} user(s) soft-deleted.", messages.WARNING)
    soft_delete_users.short_description = "Soft-delete selected users"

    def revoke_all_sessions(self, request, queryset):
        from authentication.models import RefreshToken
        count = RefreshToken.objects.filter(user__in=queryset, revoked=False).update(revoked=True)
        self.message_user(request, f"{count} session(s) revoked.", messages.SUCCESS)
    revoke_all_sessions.short_description = "Revoke all sessions for selected users"
