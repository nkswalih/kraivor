"""
Workspace models — core multi-tenancy boundary for Kraivor.

Every piece of content (repos, notes, projects, analyses) belongs to a workspace.
Workspace isolation is enforced at two layers:
  1. Application layer — queryset filtering via WorkspaceQuerySet
  2. Database layer — Row-Level Security policies (see migrations/0002_rls.py)

Design rules from system design doc:
  - All PKs are UUIDs (gen_random_uuid), never auto-incrementing ints
  - Soft deletes everywhere (deleted_at TIMESTAMPTZ)
  - created_at / updated_at on every table (updated_at via DB trigger)
  - RLS on every table in the core schema
"""

import uuid

from django.db import models
from django.utils import timezone

from .constants import WorkspacePlan, WorkspaceRole


class SoftDeleteQuerySet(models.QuerySet):
    """Base queryset that filters out soft-deleted rows."""

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft delete — sets deleted_at, never issues SQL DELETE."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Permanent delete. Use only in tests / data-purge jobs."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class TimestampedModel(models.Model):
    """
    Abstract base: UUID pk, soft delete, created_at / updated_at.

    updated_at is also maintained by a PostgreSQL trigger (see migration)
    so it stays accurate even on bulk updates that bypass Django ORM.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # bypasses soft-delete filter — use carefully

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete this instance."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanent delete. Use only when explicitly needed."""
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class Workspace(TimestampedModel):
    """
    Multi-tenancy boundary. Every resource in Kraivor belongs to a workspace.

    Slug is the human-readable unique identifier used in URLs:
      /workspace/{slug}/analysis/
      /workspace/{slug}/ai/

    Plan determines feature limits and is enforced at the API layer (not here).
    Settings JSONB stores per-workspace feature flags and UI preferences.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="URL-safe unique identifier. Immutable after creation.",
    )
    owner_id = models.UUIDField(
        db_index=True,
        help_text="identity.users.id — denormalized for query efficiency.",
    )
    plan = models.CharField(
        max_length=20,
        choices=WorkspacePlan.choices,
        default=WorkspacePlan.FREE,
        db_index=True,
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workspace-scoped feature flags and preferences.",
    )
    avatar_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True, max_length=500)

    class Meta:
        db_table = "workspaces"
        # Compound index: listing active workspaces for an owner is the hot path
        indexes = [
            models.Index(
                fields=["owner_id", "deleted_at"],
                name="idx_workspaces_owner_active",
            ),
            models.Index(
                fields=["plan", "deleted_at"],
                name="idx_workspaces_plan_active",
            ),
        ]

    def __str__(self):
        return f"Workspace({self.slug})"

    def get_member(self, user_id: uuid.UUID) -> "WorkspaceMember | None":
        """Return the WorkspaceMember for this user, or None."""
        try:
            return self.members.get(user_id=user_id)
        except WorkspaceMember.DoesNotExist:
            return None

    def get_member_role(self, user_id: uuid.UUID) -> "str | None":
        member = self.get_member(user_id)
        return member.role if member else None

    def is_owner(self, user_id: uuid.UUID) -> bool:
        return self.owner_id == user_id

    def is_member(self, user_id: uuid.UUID) -> bool:
        return self.members.filter(user_id=user_id).exists()

    @property
    def member_count(self):
        if hasattr(self, "_member_count_cache"):
            return self._member_count_cache
        return self.members.count()

    @member_count.setter
    def member_count(self, value):
        self._member_count_cache = value


class WorkspaceMember(TimestampedModel):
    """
    Membership junction table between a workspace and an identity service user.

    Role determines what actions the user can perform within the workspace.
    Role hierarchy (highest to lowest): owner > admin > member > viewer.

    The owner member record is created automatically when the workspace is
    created. There is always exactly one owner per workspace.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user_id = models.UUIDField(
        db_index=True,
        help_text="identity.users.id — FK enforced at application layer.",
    )
    role = models.CharField(
        max_length=20,
        choices=WorkspaceRole.choices,
        default=WorkspaceRole.MEMBER,
        db_index=True,
    )
    # When the member accepted an invitation (null = pending or direct add)
    joined_at = models.DateTimeField(null=True, blank=True)
    # Who added this member (for audit trail)
    invited_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "workspace_members"
        # One user can only have one active role per workspace
        unique_together = [("workspace", "user_id")]
        indexes = [
            models.Index(
                fields=["user_id", "deleted_at"],
                name="idx_members_user_active",
            ),
            models.Index(
                fields=["workspace", "role"],
                name="idx_members_workspace_role",
            ),
        ]

    def __str__(self):
        return f"Member({self.user_id}@{self.workspace.slug}:{self.role})"

    @property
    def can_admin(self) -> bool:
        return self.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

    @property
    def can_write(self) -> bool:
        return self.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN, WorkspaceRole.MEMBER)

    @property
    def is_owner(self) -> bool:
        return self.role == WorkspaceRole.OWNER