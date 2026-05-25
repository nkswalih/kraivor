"""
Workspace serializers.

Serializer responsibilities:
  - Input validation and type coercion
  - Slug auto-generation and uniqueness check
  - Read/write field separation (slug is write-once)
  - Nested member representation in workspace detail

Serializers do NOT enforce authorization — that is the permission layer's job.
Serializers do NOT call external services — that is the service layer's job.
"""

import re

from django.utils.text import slugify
from rest_framework import serializers

from .constants import WorkspaceRole
from .models import Workspace, WorkspaceMember


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """
    Serializes a workspace member for list/detail views.
    user_id is a UUID reference to identity.users — we return it as-is.
    The frontend resolves user display names via a separate /users/ endpoint.
    """

    class Meta:
        model = WorkspaceMember
        fields = [
            "id",
            "user_id",
            "role",
            "joined_at",
            "created_at",
        ]
        read_only_fields = ["id", "user_id", "joined_at", "created_at"]


class WorkspaceListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for workspace list views.
    Omits members list to keep the response fast.
    Includes the calling user's role for client-side permission rendering.
    """

    member_count = serializers.IntegerField(read_only=True)
    # Injected by the view via SerializerContext — the calling user's role
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "plan",
            "avatar_url",
            "description",
            "member_count",
            "current_user_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_current_user_role(self, obj: Workspace) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return None
        return obj.get_member_role(user_id)


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    """
    Full workspace detail including members.
    Used for GET /workspaces/{id}/.
    """

    members = WorkspaceMemberSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "owner_id",
            "plan",
            "settings",
            "avatar_url",
            "description",
            "members",
            "member_count",
            "current_user_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "owner_id",
            "plan",
            "members",
            "member_count",
            "current_user_role",
            "created_at",
            "updated_at",
        ]

    def get_current_user_role(self, obj: Workspace) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return None
        return obj.get_member_role(user_id)


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for POST /workspaces/.

    Slug:
      - Optional in request. If omitted, auto-generated from name.
      - Must be unique across all workspaces (including soft-deleted ones —
        we reserve slugs permanently to avoid URL confusion).
      - Immutable after creation (enforced in update serializer).
      - Validated: lowercase alphanumeric and hyphens only, 3–100 chars.
    """

    slug = serializers.SlugField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="URL-safe identifier. Auto-generated from name if omitted.",
    )

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "avatar_url",
            "description",
            "settings",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        if len(value) > 255:
            raise serializers.ValidationError("Name must be 255 characters or fewer.")
        return value

    def validate_slug(self, value: str) -> str:
        if not value:
            return value  # will be auto-generated in validate()

        value = value.lower().strip()

        # Only lowercase letters, digits, hyphens — no leading/trailing hyphens
        if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$", value) and len(value) > 1:
            raise serializers.ValidationError(
                "Slug must contain only lowercase letters, numbers, and hyphens, "
                "and cannot start or end with a hyphen."
            )
        if len(value) < 3:
            raise serializers.ValidationError("Slug must be at least 3 characters.")

        # Check uniqueness including soft-deleted (slugs are reserved permanently)
        if Workspace.all_objects.filter(slug=value).exists():
            raise serializers.ValidationError(
                f"The slug '{value}' is already taken."
            )
        return value

    def validate_settings(self, value: dict) -> dict:
        # Settings is free-form JSONB but we whitelist top-level keys
        # Unknown keys are stripped to prevent garbage accumulation.
        allowed_keys = {
            "default_branch",
            "ai_model_preference",
            "notifications_enabled",
            "theme",
            "timezone",
        }
        return {k: v for k, v in value.items() if k in allowed_keys}

    def validate(self, attrs: dict) -> dict:
        # Auto-generate slug from name if not provided
        if not attrs.get("slug"):
            base_slug = slugify(attrs["name"])
            if len(base_slug) < 3:
                base_slug = f"ws-{base_slug}"
            slug = self._unique_slug(base_slug)
            attrs["slug"] = slug
        return attrs

    @staticmethod
    def _unique_slug(base: str) -> str:
        """
        Append a numeric suffix until the slug is unique.
        Reserved slugs are checked against ALL workspaces (including deleted).
        """
        slug = base[:96]  # leave room for suffix
        if not Workspace.all_objects.filter(slug=slug).exists():
            return slug
        counter = 1
        while True:
            candidate = f"{slug}-{counter}"
            if not Workspace.all_objects.filter(slug=candidate).exists():
                return candidate
            counter += 1

    def create(self, validated_data: dict) -> Workspace:
        # owner_id is injected by the view, not from user input
        raise NotImplementedError(
            "Use WorkspaceService.create_workspace() — do not call serializer.save() directly."
        )


class WorkspaceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for PATCH /workspaces/{id}/.

    Slug and owner are NOT updatable after creation.
    Plan changes go through a billing flow (separate endpoint).
    """

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "avatar_url",
            "description",
            "settings",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_settings(self, value: dict) -> dict:
        allowed_keys = {
            "default_branch",
            "ai_model_preference",
            "notifications_enabled",
            "theme",
            "timezone",
        }
        # Merge with existing settings — PATCH semantics for JSONB
        existing = self.instance.settings if self.instance else {}
        merged = {**existing, **{k: v for k, v in value.items() if k in allowed_keys}}
        return merged


class MemberRoleUpdateSerializer(serializers.Serializer):
    """
    Used for PATCH /workspaces/{id}/members/{user_id}/ to change a member's role.
    Cannot be used to set role to 'owner' — ownership transfer is a separate flow.
    """

    role = serializers.ChoiceField(
        choices=[
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
            WorkspaceRole.VIEWER,
        ]
    )