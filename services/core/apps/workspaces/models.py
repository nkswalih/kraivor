"""
Workspace models — core multi-tenancy boundary for Kraivor.

KRV-019 defined: Workspace, WorkspaceMember, TimestampedModel, SoftDelete*
KRV-020 adds:   WorkspaceInvitation

Design rules (system design §6):
  - All PKs are UUIDs
  - Soft deletes everywhere (deleted_at TIMESTAMPTZ)
  - created_at / updated_at on every table
  - Row-Level Security enforced via migration (see 0002_rls.py)
"""

import secrets
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone

from .constants import WorkspacePlan, WorkspaceRole

# ─── Soft Delete Infrastructure ───────────────────────────────────────────────


class SoftDeleteQuerySet(models.QuerySet):
    """Base queryset that excludes soft-deleted rows by default."""

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Bulk soft delete — never issues SQL DELETE."""
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

    updated_at is maintained both by Django auto_now AND a PostgreSQL trigger
    (migration 0001) so bulk updates via QuerySet.update() also set it correctly.
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
        """Permanent delete."""
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ─── Workspace ─────────────────────────────────────────────────────────────────


class Workspace(TimestampedModel):
    """
    Multi-tenancy boundary. Every resource in Kraivor belongs to a workspace.

    Slug is the human-readable unique identifier used in URLs.
    Plan determines feature limits enforced at the API/service layer.
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
        indexes = [
            models.Index(
                fields=["owner_id", "deleted_at"], name="idx_workspaces_owner_active"
            ),
            models.Index(
                fields=["plan", "deleted_at"], name="idx_workspaces_plan_active"
            ),
        ]

    def __str__(self):
        return f"Workspace({self.slug})"

    def get_member(self, user_id: uuid.UUID) -> "WorkspaceMember | None":
        """Return the active WorkspaceMember for this user, or None."""
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
        return self.members.count()


# ─── Workspace Member ──────────────────────────────────────────────────────────


class WorkspaceMember(TimestampedModel):
    """
    Membership junction table between a workspace and an identity service user.

    Role hierarchy (highest → lowest): owner > admin > member > viewer.
    The owner member record is created atomically with the workspace.
    There is always exactly one owner per workspace.

    user_id is a UUID reference to identity.users — no FK to avoid
    cross-service database coupling (system design §1: "Service owns its data").
    """

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="members"
    )
    user_id = models.UUIDField(
        db_index=True, help_text="identity.users.id — cross-service ref, no DB FK."
    )
    role = models.CharField(
        max_length=20,
        choices=WorkspaceRole.choices,
        default=WorkspaceRole.MEMBER,
        db_index=True,
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user accepted the invitation. Null for direct adds.",
    )
    invited_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="identity.users.id of the inviter. Audit trail.",
    )

    class Meta:
        db_table = "workspace_members"
        unique_together = [("workspace", "user_id")]
        # SoftDeleteManager must be the default manager so that reverse FK
        # accessors (workspace.members) also use it and expose .alive().
        # Without this, workspace.members returns a plain RelatedManager
        # that has no .alive() method.
        default_manager_name = "objects"
        indexes = [
            models.Index(
                fields=["user_id", "deleted_at"], name="idx_members_user_active"
            ),
            models.Index(
                fields=["workspace", "role"], name="idx_members_workspace_role"
            ),
        ]

    def __str__(self):
        return f"Member({self.user_id}@{self.workspace.slug}:{self.role})"

    @property
    def can_admin(self) -> bool:
        return self.role in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN)

    @property
    def can_write(self) -> bool:
        return self.role in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.MEMBER,
        )

    @property
    def is_owner(self) -> bool:
        return self.role == WorkspaceRole.OWNER


# ─── Workspace Invitation ──────────────────────────────────────────────────────

INVITATION_EXPIRY_HOURS = 48  # default invitation lifespan


def _default_token() -> str:
    """
    Generate a cryptographically secure URL-safe token.
    32 bytes = 64 hex chars — sufficient entropy to prevent brute-force.
    secrets.token_urlsafe is the Python stdlib recommendation for tokens.
    """
    return secrets.token_urlsafe(48)  # 48 bytes → 64-char URL-safe string


def _default_expiry():
    return timezone.now() + timedelta(hours=INVITATION_EXPIRY_HOURS)


class WorkspaceInvitation(TimestampedModel):
    """
    Pending invitation for a user (identified by email) to join a workspace.

    Lifecycle:
      PENDING  → invitation created, email sent, user hasn't accepted yet
      ACCEPTED → user clicked the link and joined; accepted_at is set
      EXPIRED  → expires_at passed without acceptance (checked at accept time)
      REVOKED  → soft-deleted by an admin before acceptance

    Security design:
      - Token is a 64-char cryptographically random string (not UUID, not sequential)
      - Token is stored in plaintext (it's not a secret like a password — it IS the
        credential, similar to a password reset token). Acceptable because:
          a) Short TTL (48h), b) One-time use, c) HTTPS-only transmission
      - Replay attack prevention: accepted_at checked before creating membership
      - Duplicate invite prevention: enforced at service layer + DB unique index

    The invitation is scoped to an email address, not a user_id. This allows
    inviting users who don't have a Kraivor account yet.
    When they sign up and accept, the identity service links their account to the email.
    """

    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField(
        db_index=True,
        help_text="Invited email address. May or may not have a Kraivor account.",
    )
    role = models.CharField(
        max_length=20,
        choices=[
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
            (WorkspaceRole.VIEWER, "Viewer"),
        ],
        default=WorkspaceRole.MEMBER,
        help_text="Role the invitee will receive upon acceptance.",
    )
    token = models.CharField(
        max_length=128,
        unique=True,
        default=_default_token,
        db_index=True,
        help_text="Secure random URL token. Unique, one-time use.",
    )
    invited_by_id = models.UUIDField(
        help_text="identity.users.id of the user who sent the invitation.",
        db_index=True,
    )
    # Display name of inviter — denormalized to avoid cross-service lookup in email
    invited_by_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Denormalized inviter display name for email rendering.",
    )
    expires_at = models.DateTimeField(
        default=_default_expiry,
        db_index=True,
        help_text="Invitation expires after this time. Default: 48 hours from creation.",
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Set when the invitation is accepted. Null = pending.",
    )
    # Tracks delivery status — useful for resend logic and debugging
    email_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invitation email was successfully sent.",
    )

    class Meta:
        db_table = "workspace_invitations"
        indexes = [
            # Hot path: check for duplicate pending invites for an email in a workspace
            models.Index(
                fields=["workspace", "email", "accepted_at"], name="idx_inv_ws_email"
            ),
            # Hot path: look up by token on acceptance
            models.Index(fields=["token", "accepted_at"], name="idx_inv_token_acc"),
            # Admin view: list pending invitations for a workspace
            models.Index(
                fields=["workspace", "expires_at", "accepted_at"],
                name="idx_invitations_pending",
            ),
        ]

    def __str__(self):
        status = (
            "accepted"
            if self.accepted_at
            else ("expired" if self.is_expired else "pending")
        )
        return f"Invitation({self.email}→{self.workspace.slug}:{self.role}:{status})"

    # ── State properties ──────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_revoked(self) -> bool:
        return self.is_deleted

    @property
    def is_pending(self) -> bool:
        return not self.is_accepted and not self.is_expired and not self.is_revoked

    @property
    def status(self) -> str:
        if self.is_accepted:
            return "accepted"
        if self.is_revoked:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "pending"

    def accept(self) -> None:
        """Mark the invitation as accepted. Call within atomic transaction."""
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_at", "updated_at"])

    def mark_email_sent(self) -> None:
        """Record when the invitation email was dispatched."""
        self.email_sent_at = timezone.now()
        self.save(update_fields=["email_sent_at", "updated_at"])

    @property
    def accept_url(self) -> str:
        """Frontend URL the invitee clicks to accept the invitation."""
        from django.conf import settings

        base = getattr(settings, "FRONTEND_BASE_URL", "https://localhost")
        return f"{base}/invitations/{self.token}"
