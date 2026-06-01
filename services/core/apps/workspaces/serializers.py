"""
Workspace serializers — KRV-019 (workspace CRUD) + KRV-020 (invitations).

Serializer contract:
  - Validate and coerce input
  - Never enforce authorization (that's permissions + service layer)
  - Never call external services (that's the service layer)
  - Output shape is the API contract — change carefully

Invitation serializers added in KRV-020:
  WorkspaceInvitationCreateSerializer  — POST /members/invite/
  WorkspaceInvitationSerializer        — response shape for invitations
  InvitationAcceptSerializer           — POST /invitations/{token}/accept/
"""

import re

from django.utils.text import slugify
from rest_framework import serializers

from .constants import WorkspaceRole
from .models import Workspace, WorkspaceInvitation, WorkspaceMember

# ─── Member Serializers ────────────────────────────────────────────────────────

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """
    Full member representation.
    user_id is a UUID ref to identity.users — frontend resolves display names
    via a separate identity service call (or the JWT payload for the current user).
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceMember
        fields = [
            "id",
            "user_id",
            "role",
            "status",
            "joined_at",
            "invited_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status(self, obj: WorkspaceMember) -> str:
        return "active" if not obj.is_deleted else "removed"


class MemberRoleUpdateSerializer(serializers.Serializer):
    """
    Used for PATCH /workspaces/{id}/members/{user_id}/ to change a member's role.
    Cannot set role to 'owner' — ownership transfer is a separate flow.
    """

    role = serializers.ChoiceField(
        choices=[
            (WorkspaceRole.OWNER, "Owner"),
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
            (WorkspaceRole.VIEWER, "Viewer"),
        ]
    )

    def validate_role(self, value: str) -> str:
        if value == WorkspaceRole.OWNER:
            raise serializers.ValidationError("Ownership transfer is a separate flow.")
        return value

# ─── Workspace Serializers (KRV-019) ──────────────────────────────────────────

class WorkspaceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views. No members list."""

    active_member_count = serializers.IntegerField(read_only=True)
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "plan", "avatar_url", "description",
            "active_member_count", "current_user_role", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_current_user_role(self, obj: Workspace) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        user_id = getattr(request, "user_id", None)
        return obj.get_member_role(user_id) if user_id else None


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    """Full workspace detail including members."""

    members = WorkspaceMemberSerializer(many=True, read_only=True)
    active_member_count = serializers.IntegerField(read_only=True)
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "owner_id", "plan", "settings",
            "avatar_url", "description", "members", "active_member_count",
            "current_user_role", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "owner_id", "plan", "members",
            "active_member_count", "current_user_role", "created_at", "updated_at",
        ]

    def get_current_user_role(self, obj: Workspace) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        user_id = getattr(request, "user_id", None)
        return obj.get_member_role(user_id) if user_id else None


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """POST /workspaces/ input serializer."""

    slug = serializers.SlugField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "avatar_url", "description", "settings", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_slug(self, value: str) -> str:
        if not value:
            return value
        value = value.lower().strip()
        if len(value) > 1 and not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$", value):
            raise serializers.ValidationError(
                "Slug must contain only lowercase letters, numbers, and hyphens."
            )
        if len(value) < 3:
            raise serializers.ValidationError("Slug must be at least 3 characters.")
        if Workspace.all_objects.filter(slug=value).exists():
            raise serializers.ValidationError(f"The slug '{value}' is already taken.")
        return value

    def validate_settings(self, value: dict) -> dict:
        allowed = {"default_branch", "ai_model_preference", "notifications_enabled", "theme", "timezone"}
        return {k: v for k, v in value.items() if k in allowed}

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("slug"):
            attrs["slug"] = self._unique_slug(slugify(attrs["name"]))
        return attrs

    @staticmethod
    def _unique_slug(base: str) -> str:
        slug = base[:96] or "workspace"
        if len(slug) < 3:
            slug = f"ws-{slug}"
        if not Workspace.all_objects.filter(slug=slug).exists():
            return slug
        counter = 1
        while True:
            candidate = f"{slug}-{counter}"
            if not Workspace.all_objects.filter(slug=candidate).exists():
                return candidate
            counter += 1

    def create(self, validated_data: dict) -> Workspace:
        raise NotImplementedError("Use WorkspaceService.create_workspace()")


class WorkspaceUpdateSerializer(serializers.ModelSerializer):
    """PATCH /workspaces/{id}/ — slug and owner are immutable."""

    class Meta:
        model = Workspace
        fields = ["id", "name", "avatar_url", "description", "settings", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_settings(self, value: dict) -> dict:
        allowed = {"default_branch", "ai_model_preference", "notifications_enabled", "theme", "timezone"}
        existing = self.instance.settings if self.instance else {}
        return {**existing, **{k: v for k, v in value.items() if k in allowed}}


# ─── Invitation Serializers (KRV-020) ─────────────────────────────────────────

class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    """
    Read serializer for invitation responses.
    Token is included in admin list views and the creation response.
    The frontend uses it to build the accept URL for copy-paste sharing.
    """

    status = serializers.ReadOnlyField()
    accept_url = serializers.ReadOnlyField()

    workspace_name = serializers.CharField(
        source="workspace.name",
        read_only=True,
    )

    workspace_slug = serializers.CharField(
        source="workspace.slug",
        read_only=True,
    )

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id",
            "workspace_id",
            "workspace_name",
            "workspace_slug",
            "email",
            "role",
            "token",
            "invited_by_id",
            "invited_by_name",
            "status",
            "accept_url",
            "expires_at",
            "accepted_at",
            "email_sent_at",
            "created_at",
        ]
        read_only_fields = fields


class WorkspaceInvitationCreateSerializer(serializers.Serializer):
    """
    POST /workspaces/{id}/members/invite/

    Validates the invite request payload.
    email: target recipient
    role:  role they'll receive (cannot be 'owner')

    We accept invited_by_name from the request context (set by the view from
    the JWT sub claim display name) — not from user input.
    """

    email = serializers.EmailField(
        help_text="Email address of the person being invited."
    )
    role = serializers.ChoiceField(
        choices=[
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
            (WorkspaceRole.VIEWER, "Viewer"),
        ],
        default=WorkspaceRole.MEMBER,
    )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class InvitationAcceptSerializer(serializers.Serializer):
    """
    POST /workspace/invitations/{token}/accept/

    The token comes from the URL path, not the body.
    The user_id comes from the gateway header (request.user_id).
    No body fields required — the token IS the credential.
    """
    # No input fields — token is path param, user is from gateway header
    pass


class InvitationAcceptResponseSerializer(serializers.Serializer):
    """Response shape after successfully accepting an invitation."""

    workspace_id = serializers.UUIDField()
    workspace_name = serializers.CharField()
    workspace_slug = serializers.CharField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()
    message = serializers.CharField()