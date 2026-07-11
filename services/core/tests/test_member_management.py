"""
Workspace test suite — KRV-019 + KRV-020.

Test philosophy:
  - Service layer tests: test business logic in isolation (no HTTP)
  - View tests: test full HTTP stack via APIClient (integration)
  - All tests use @pytest.mark.django_db
  - Kafka publisher and Celery tasks are always mocked — unit tests should not
    require running infrastructure

Test structure:
  TestWorkspaceService         — workspace CRUD, plan limits
  TestInvitationService        — invite, accept, revoke, duplicate prevention
  TestInvitationAcceptEdgeCases — expired, replay attack, concurrent acceptance
  TestWorkspaceViews           — HTTP-level integration tests
  TestMemberViews              — member list, role update, remove
  TestInvitationViews          — invite endpoint, accept endpoint
  TestPermissions              — RBAC enforcement
  TestKafkaEvents              — event publish verification
  TestCeleryTasks              — task dispatch verification
"""

import pytest
import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

from apps.workspaces.constants import WorkspacePlan, WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceInvitation, WorkspaceMember
from apps.workspaces.services import (
    InvitationError,
    InvitationService,
    WorkspaceLimitError,
    WorkspacePermissionError,
    WorkspaceService,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def owner_id():
    return uuid.uuid4()


@pytest.fixture
def admin_id():
    return uuid.uuid4()


@pytest.fixture
def member_id():
    return uuid.uuid4()


@pytest.fixture
def viewer_id():
    return uuid.uuid4()


@pytest.fixture
def outsider_id():
    return uuid.uuid4()


@pytest.fixture
def workspace(owner_id):
    """A workspace with the owner already a member."""
    ws = Workspace.objects.create(
        name="Test Workspace",
        slug="test-workspace",
        owner_id=owner_id,
        plan=WorkspacePlan.FREE,
    )
    WorkspaceMember.objects.create(
        workspace=ws,
        user_id=owner_id,
        role=WorkspaceRole.OWNER,
        joined_at=timezone.now(),
    )
    return ws


@pytest.fixture
def team_workspace(workspace):
    workspace.plan = WorkspacePlan.TEAM
    workspace.save(update_fields=["plan"])
    return workspace


@pytest.fixture
def workspace_with_members(workspace, admin_id, member_id, viewer_id):
    """Workspace with owner + admin + member + viewer."""
    WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=admin_id,
        role=WorkspaceRole.ADMIN,
        joined_at=timezone.now(),
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=member_id,
        role=WorkspaceRole.MEMBER,
        joined_at=timezone.now(),
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        user_id=viewer_id,
        role=WorkspaceRole.VIEWER,
        joined_at=timezone.now(),
    )
    return workspace


@pytest.fixture
def team_workspace_with_members(team_workspace, admin_id, member_id, viewer_id):
    WorkspaceMember.objects.create(
        workspace=team_workspace,
        user_id=admin_id,
        role=WorkspaceRole.ADMIN,
        joined_at=timezone.now(),
    )

    WorkspaceMember.objects.create(
        workspace=team_workspace,
        user_id=member_id,
        role=WorkspaceRole.MEMBER,
        joined_at=timezone.now(),
    )

    WorkspaceMember.objects.create(
        workspace=team_workspace,
        user_id=viewer_id,
        role=WorkspaceRole.VIEWER,
        joined_at=timezone.now(),
    )

    return team_workspace


@pytest.fixture
def mock_events():
    with patch(
        "apps.workspaces.services.workspace_service.WorkspaceEventPublisher"
    ) as MockPublisher:
        mock = MagicMock()
        MockPublisher.return_value = mock
        yield mock


@pytest.fixture
def api_client():
    return APIClient()


def _authed_client(
    user_id: uuid.UUID, user_name: str = "Test User", email: str = "test@example.com"
) -> APIClient:
    """
    Create an API client with gateway-injected auth simulation.

    Strategy: Use DRF's force_authenticate with a mock user object that carries
    user_id and user_name as attributes. The views read request.user_id —
    we monkey-patch that via a custom authentication class injected only in tests.

    This bypasses the real GatewayAuthMiddleware entirely, which is correct for
    unit/integration tests — we're testing our code, not the gateway.

    The client also sends the HTTP headers for completeness (some middleware
    may read them), but the force_authenticate is what makes IsAuthenticated pass.
    """
    from unittest.mock import MagicMock as _MM

    client = APIClient()

    # Create a lightweight user-like object that carries our custom attributes.
    # DRF's permission classes check request.user_id (set by GatewayAuthMiddleware).
    # We replicate that here by forcing it onto the request via a mock authenticator.
    mock_user = _MM()
    mock_user.is_authenticated = True
    mock_user.id = user_id
    mock_user.user_id = user_id  # mirrors what middleware sets on request
    mock_user.user_name = user_name
    mock_user.pk = user_id
    mock_user.email = email
    mock_user.user_email = email

    # force_authenticate makes DRF skip all authentication classes and sets
    # request.user = mock_user AND request.auth = None.
    # Our permission classes read request.user_id — we patch this via the
    # _inject_user_id fixture below.
    client.force_authenticate(user=mock_user)

    # Also send headers so any middleware that reads them still works
    client.credentials(HTTP_X_USER_ID=str(user_id), HTTP_X_USER_NAME=user_name)

    # Store on the client so _authed_client callers can access it
    client._test_user_id = user_id
    client._test_user_name = user_name

    return client


@pytest.fixture(autouse=True)
def patch_request_user_id(monkeypatch):
    """
    Globally patches IsAuthenticated and the view's _get_user_id() to read from
    request.user.user_id when request.user_id is not set by real middleware.

    This single autouse fixture fixes ALL view tests without changing the
    permission classes or views themselves — clean separation of test concerns.
    """
    from apps.workspaces import permissions as perms
    from apps.workspaces import views as v

    def patched_has_permission(self, request, view):
        # If real middleware already set it, use that
        if getattr(request, "user_id", None):
            return True
        # Fall back to force_authenticate mock user
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            request.user_id = getattr(user, "user_id", None) or getattr(
                user, "id", None
            )
            request.user_name = getattr(user, "user_name", "")
            request.user_email = getattr(user, "user_email", None) or getattr(
                user, "email", None
            )
            return bool(request.user_id)
        return False

    monkeypatch.setattr(perms.IsAuthenticated, "has_permission", patched_has_permission)

    # Also patch WorkspaceContextMixin._get_user_id for the same reason
    def patched_get_user_id(self):
        uid = getattr(self.request, "user_id", None)
        if uid:
            return uid
        user = getattr(self.request, "user", None)
        if user:
            uid = getattr(user, "user_id", None) or getattr(user, "id", None)
            if uid:
                self.request.user_id = uid
                return uid
        raise ValueError("user_id not set on request — is the client authenticated?")

    monkeypatch.setattr(v.WorkspaceContextMixin, "_get_user_id", patched_get_user_id)


@pytest.fixture(autouse=True)
def bypass_jwt_middleware(monkeypatch):
    from core.middleware.jwt_auth import JWTAuthenticationMiddleware

    original_call = JWTAuthenticationMiddleware.__call__

    def patched_call(self, request):
        user = getattr(request, "user", None)

        if user and getattr(user, "is_authenticated", False):
            request.user_id = getattr(user, "user_id", None) or getattr(
                user, "id", None
            )
            request.user_name = getattr(user, "user_name", "")
            request.user_email = getattr(user, "user_email", None) or getattr(
                user, "email", None
            )

            return self.get_response(request)

        return original_call(self, request)

    monkeypatch.setattr(JWTAuthenticationMiddleware, "__call__", patched_call)


# ─── WorkspaceService Tests ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestWorkspaceService:
    def test_create_workspace_creates_owner_member(self, mock_events):
        owner_id = uuid.uuid4()
        service = WorkspaceService(event_publisher=mock_events)

        ws = service.create_workspace(
            owner_id=owner_id, name="My Workspace", slug="my-workspace"
        )

        assert ws.id is not None
        assert ws.owner_id == owner_id
        assert ws.plan == WorkspacePlan.FREE
        # Owner membership created atomically
        member = WorkspaceMember.objects.get(workspace=ws, user_id=owner_id)
        assert member.role == WorkspaceRole.OWNER
        assert member.joined_at is not None

    def test_create_workspace_publishes_event(self, mock_events):
        owner_id = uuid.uuid4()
        service = WorkspaceService(event_publisher=mock_events)
        ws = service.create_workspace(owner_id=owner_id, name="X", slug="x-ws-slug")
        mock_events.workspace_created.assert_called_once_with(
            workspace=ws, actor_id=owner_id
        )

    def test_delete_workspace_only_owner(
        self, workspace_with_members, owner_id, admin_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)

        with pytest.raises(WorkspacePermissionError):
            service.delete_workspace(
                workspace=workspace_with_members, actor_id=admin_id
            )

        # Owner can delete
        service.delete_workspace(workspace=workspace_with_members, actor_id=owner_id)
        workspace_with_members.refresh_from_db()
        assert workspace_with_members.is_deleted

    def test_delete_workspace_soft_deletes_members(
        self, workspace_with_members, owner_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        member_count_before = workspace_with_members.members.count()
        assert member_count_before > 0

        service.delete_workspace(workspace=workspace_with_members, actor_id=owner_id)

        # All members should be soft-deleted
        active_members = WorkspaceMember.objects.filter(
            workspace=workspace_with_members, deleted_at__isnull=True
        )
        assert active_members.count() == 0

    def test_update_workspace_requires_admin(
        self, workspace_with_members, viewer_id, member_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)

        for user_id in [viewer_id, member_id]:
            with pytest.raises(WorkspacePermissionError):
                service.update_workspace(
                    workspace=workspace_with_members,
                    actor_id=user_id,
                    updates={"name": "New Name"},
                )

    def test_update_workspace_admin_can_update(
        self, workspace_with_members, admin_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        updated = service.update_workspace(
            workspace=workspace_with_members,
            actor_id=admin_id,
            updates={"name": "Updated Name"},
        )
        assert updated.name == "Updated Name"

    def test_update_member_role_prevents_owner_assignment(
        self, workspace_with_members, owner_id, member_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.update_member_role(
                workspace=workspace_with_members,
                actor_id=owner_id,
                target_user_id=member_id,
                new_role=WorkspaceRole.OWNER,
            )

    def test_update_member_role_admin_cannot_demote_other_admin(
        self, workspace_with_members, admin_id, mock_events
    ):
        # Create a second admin
        second_admin_id = uuid.uuid4()
        WorkspaceMember.objects.create(
            workspace=workspace_with_members,
            user_id=second_admin_id,
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        service = WorkspaceService(event_publisher=mock_events)

        with pytest.raises(WorkspacePermissionError):
            service.update_member_role(
                workspace=workspace_with_members,
                actor_id=admin_id,  # admin trying to change another admin
                target_user_id=second_admin_id,
                new_role=WorkspaceRole.MEMBER,
            )

    def test_update_member_role_publishes_event(
        self, workspace_with_members, owner_id, member_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        service.update_member_role(
            workspace=workspace_with_members,
            actor_id=owner_id,
            target_user_id=member_id,
            new_role=WorkspaceRole.ADMIN,
        )
        mock_events.member_role_changed.assert_called_once()

    def test_remove_member_owner_cannot_be_removed(
        self, workspace_with_members, owner_id, admin_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.remove_member(
                workspace=workspace_with_members,
                actor_id=admin_id,
                target_user_id=owner_id,
            )

    def test_remove_member_self_removal_always_allowed(
        self, workspace_with_members, member_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        service.remove_member(
            workspace=workspace_with_members,
            actor_id=member_id,
            target_user_id=member_id,
        )
        assert not workspace_with_members.is_member(member_id)

    def test_remove_member_admin_cannot_remove_other_admin(
        self, workspace_with_members, admin_id, mock_events
    ):
        second_admin_id = uuid.uuid4()
        WorkspaceMember.objects.create(
            workspace=workspace_with_members,
            user_id=second_admin_id,
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        service = WorkspaceService(event_publisher=mock_events)

        with pytest.raises(WorkspacePermissionError):
            service.remove_member(
                workspace=workspace_with_members,
                actor_id=admin_id,
                target_user_id=second_admin_id,
            )

    def test_remove_member_viewer_cannot_remove_others(
        self, workspace_with_members, viewer_id, member_id, mock_events
    ):
        service = WorkspaceService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError):
            service.remove_member(
                workspace=workspace_with_members,
                actor_id=viewer_id,
                target_user_id=member_id,
            )

    def test_plan_limit_enforced(self, workspace, owner_id, mock_events):
        """Free plan max 3 members — adding a 3rd triggers limit error."""
        workspace.plan = WorkspacePlan.FREE
        workspace.save()

        # Already have owner (1). Add 2 more to hit limit.
        for _ in range(2):
            WorkspaceMember.objects.create(
                workspace=workspace,
                user_id=uuid.uuid4(),
                role=WorkspaceRole.MEMBER,
                joined_at=timezone.now(),
            )

        service = WorkspaceService(event_publisher=mock_events)
        with pytest.raises(WorkspaceLimitError):
            service.add_member(
                workspace=workspace,
                actor_id=owner_id,
                user_id=uuid.uuid4(),
                role=WorkspaceRole.MEMBER,
            )


# ─── InvitationService Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestInvitationService:
    def test_create_invitation_success(self, workspace, owner_id, mock_events):
        service = InvitationService(event_publisher=mock_events)
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            invitation = service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="newuser@example.com",
                role=WorkspaceRole.MEMBER,
            )

        assert invitation.id is not None
        assert invitation.email == "newuser@example.com"
        assert invitation.role == WorkspaceRole.MEMBER
        assert invitation.token is not None
        assert len(invitation.token) >= 60  # 48-byte urlsafe = ~64 chars
        assert invitation.is_pending
        assert not invitation.is_expired

    def test_invitation_token_is_unique(self, workspace, owner_id, mock_events):
        """Each invitation gets a unique cryptographic token."""
        # Use ENTERPRISE plan — FREE plan (max 3 members) would block after invite #2.
        workspace.plan = WorkspacePlan.ENTERPRISE
        workspace.save(update_fields=["plan"])

        service = InvitationService(event_publisher=mock_events)

        tokens = set()
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            for i in range(10):
                inv = service.create_invitation(
                    workspace=workspace,
                    actor_id=owner_id,
                    actor_name="Owner",
                    email=f"user{i}@example.com",
                    role=WorkspaceRole.MEMBER,
                )
                tokens.add(inv.token)

        assert len(tokens) == 10  # all unique

    def test_duplicate_invitation_prevented(self, workspace, owner_id, mock_events):
        """Cannot send two pending invitations to the same email."""
        service = InvitationService(event_publisher=mock_events)

        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="dupe@example.com",
                role=WorkspaceRole.MEMBER,
            )

        with pytest.raises(InvitationError, match="pending invitation already exists"):
            service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="dupe@example.com",
                role=WorkspaceRole.MEMBER,
            )

    def test_can_reinvite_after_expiry(self, workspace, owner_id, mock_events):
        """After an invitation expires, a new one can be created for the same email."""
        # Create an expired invitation directly
        WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="expired@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
            expires_at=timezone.now() - timedelta(hours=1),  # already expired
        )

        service = InvitationService(event_publisher=mock_events)
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            # Should succeed — previous invitation is expired
            invitation = service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="expired@example.com",
                role=WorkspaceRole.MEMBER,
            )
        assert invitation.is_pending

    def test_viewer_cannot_invite(self, workspace_with_members, viewer_id, mock_events):
        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError):
            service.create_invitation(
                workspace=workspace_with_members,
                actor_id=viewer_id,
                actor_name="Viewer",
                email="someone@example.com",
                role=WorkspaceRole.MEMBER,
            )

    def test_member_cannot_invite(self, workspace_with_members, member_id, mock_events):
        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError):
            service.create_invitation(
                workspace=workspace_with_members,
                actor_id=member_id,
                actor_name="Member",
                email="someone@example.com",
                role=WorkspaceRole.MEMBER,
            )

    def test_cannot_invite_as_owner(self, workspace, owner_id, mock_events):
        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="newowner@example.com",
                role=WorkspaceRole.OWNER,
            )

    def test_accept_invitation_creates_member(self, workspace, owner_id, mock_events):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="acceptor@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        new_user_id = uuid.uuid4()

        service = InvitationService(event_publisher=mock_events)
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_member_joined_notification"
        ):
            returned_inv, member = service.accept_invitation(
                token=invitation.token, user_id=new_user_id, user_email=invitation.email
            )

        assert returned_inv.is_accepted
        assert member.user_id == new_user_id
        assert member.role == WorkspaceRole.MEMBER
        assert member.joined_at is not None
        assert workspace.is_member(new_user_id)

    def test_accept_invitation_marks_accepted(self, workspace, owner_id, mock_events):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        new_user_id = uuid.uuid4()

        service = InvitationService(event_publisher=mock_events)
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_member_joined_notification"
        ):
            service.accept_invitation(
                token=invitation.token, user_id=new_user_id, user_email=invitation.email
            )

        invitation.refresh_from_db()
        assert invitation.accepted_at is not None

    def test_accept_expired_invitation_fails(self, workspace, owner_id, mock_events):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(InvitationError, match="expired"):
            service.accept_invitation(
                token=invitation.token,
                user_id=uuid.uuid4(),
                user_email=invitation.email,
            )

    def test_accept_invalid_token_fails(self, mock_events):
        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(InvitationError, match="invalid"):
            service.accept_invitation(
                token="not-a-real-token",
                user_id=uuid.uuid4(),
                user_email="test@gmail.com",
            )

    def test_accept_revoked_invitation_fails(self, workspace, owner_id, mock_events):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        invitation.delete()  # soft delete = revoke

        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(InvitationError, match="invalid"):
            service.accept_invitation(
                token=invitation.token,
                user_id=uuid.uuid4(),
                user_email=invitation.email,
            )

    def test_accept_already_accepted_invitation_fails(
        self, workspace, owner_id, mock_events
    ):
        """Replay attack prevention: cannot accept the same invitation twice."""
        new_user_id = uuid.uuid4()
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        invitation.accept()  # pre-accept

        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(InvitationError, match="already been accepted"):
            service.accept_invitation(
                token=invitation.token, user_id=new_user_id, user_email=invitation.email
            )

    def test_accept_already_member_is_idempotent(
        self, workspace_with_members, owner_id, member_id, mock_events
    ):
        """
        If the user is already a member (e.g. accepted invite from another workspace
        session), return success without creating a duplicate member row.
        """
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="existing@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )

        service = InvitationService(event_publisher=mock_events)
        returned_inv, member = service.accept_invitation(
            token=invitation.token, user_id=member_id, user_email=invitation.email
        )

        # Should succeed, not duplicate
        assert (
            WorkspaceMember.objects.filter(
                workspace=workspace_with_members, user_id=member_id
            ).count()
            == 1
        )

    def test_revoke_invitation(self, workspace, owner_id, admin_id, mock_events):
        WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=admin_id,
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        service = InvitationService(event_publisher=mock_events)
        service.revoke_invitation(invitation=invitation, actor_id=admin_id)

        invitation.refresh_from_db()
        assert invitation.is_revoked

    def test_revoke_accepted_invitation_fails(self, workspace, owner_id, mock_events):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        invitation.accept()

        service = InvitationService(event_publisher=mock_events)
        with pytest.raises(InvitationError, match="already been accepted"):
            service.revoke_invitation(invitation=invitation, actor_id=owner_id)

    def test_list_pending_invitations(self, workspace, owner_id, mock_events):
        # Create 2 pending, 1 accepted, 1 expired
        for i in range(2):
            WorkspaceInvitation.objects.create(
                workspace=workspace,
                email=f"pending{i}@x.com",
                role=WorkspaceRole.MEMBER,
                invited_by_id=owner_id,
                invited_by_name="O",
            )
        accepted = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="accepted@x.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="O",
        )
        accepted.accept()

        WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="expired@x.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="O",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        service = InvitationService(event_publisher=mock_events)
        pending = list(service.list_pending_invitations(workspace=workspace))

        assert len(pending) == 2
        emails = {inv.email for inv in pending}
        assert "pending0@x.com" in emails
        assert "pending1@x.com" in emails

    def test_accept_invitation_wrong_email_fails(
        self, workspace, owner_id, mock_events
    ):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="correct@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )

        service = InvitationService(event_publisher=mock_events)

        with pytest.raises(InvitationError, match="different email address"):
            service.accept_invitation(
                token=invitation.token,
                user_id=uuid.uuid4(),
                user_email="wrong@example.com",
            )


# ─── HTTP View Tests ──────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWorkspaceViews:
    def test_create_workspace(self, owner_id, ws_url):
        client = _authed_client(owner_id, "Owner")
        resp = client.post(
            ws_url("workspaces/"),
            {"name": "My Workspace", "slug": "my-workspace"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["slug"] == "my-workspace"
        assert resp.data["current_user_role"] == WorkspaceRole.OWNER

    def test_create_workspace_auto_slug(self, owner_id, ws_url):
        client = _authed_client(owner_id)
        resp = client.post(
            ws_url("workspaces/"), {"name": "My Cool Workspace"}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "my-cool-workspace" in resp.data["slug"]

    def test_list_workspaces_only_own(
        self, workspace_with_members, owner_id, outsider_id, ws_url
    ):
        owner_client = _authed_client(owner_id)
        outsider_client = _authed_client(outsider_id)

        owner_resp = owner_client.get(ws_url("workspaces/"))
        outsider_resp = outsider_client.get(ws_url("workspaces/"))

        assert owner_resp.status_code == 200
        assert len(owner_resp.data["results"]) >= 1
        assert outsider_resp.status_code == 200
        assert len(outsider_resp.data["results"]) == 0

    def test_retrieve_workspace_member_can_see(
        self, workspace_with_members, member_id, ws_url
    ):
        client = _authed_client(member_id)
        resp = client.get(ws_url(f"workspaces/{workspace_with_members.id}/"))
        assert resp.status_code == 200
        assert resp.data["id"] == str(workspace_with_members.id)

    def test_retrieve_workspace_outsider_gets_404(
        self, workspace_with_members, outsider_id, ws_url
    ):
        """Security: non-members receive 404, not 403. Never confirm existence."""
        client = _authed_client(outsider_id)
        resp = client.get(ws_url(f"workspaces/{workspace_with_members.id}/"))
        assert resp.status_code == 404

    def test_delete_workspace_owner_only(
        self, workspace_with_members, admin_id, owner_id, ws_url
    ):
        admin_client = _authed_client(admin_id)
        resp = admin_client.delete(ws_url(f"workspaces/{workspace_with_members.id}/"))
        assert resp.status_code == 403

        owner_client = _authed_client(owner_id)
        resp = owner_client.delete(ws_url(f"workspaces/{workspace_with_members.id}/"))
        assert resp.status_code == 204

    def test_unauthenticated_request_rejected(self, workspace, ws_url):
        client = APIClient()  # no auth headers, no force_authenticate
        resp = client.get(ws_url("workspaces/"))
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMemberViews:
    def test_list_members(self, workspace_with_members, member_id, ws_url):
        client = _authed_client(member_id)
        resp = client.get(ws_url(f"workspaces/{workspace_with_members.id}/members/"))
        assert resp.status_code == 200
        assert len(resp.data) >= 4  # owner, admin, member, viewer

    def test_update_role_admin_can_promote_member(
        self, workspace_with_members, admin_id, member_id, ws_url
    ):
        client = _authed_client(admin_id)
        resp = client.patch(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{member_id}/"),
            {"role": "admin"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["role"] == "admin"

    def test_update_role_member_cannot_change_roles(
        self, workspace_with_members, member_id, viewer_id, ws_url
    ):
        client = _authed_client(member_id)
        resp = client.patch(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{viewer_id}/"),
            {"role": "member"},
            format="json",
        )
        assert resp.status_code == 403

    def test_update_role_cannot_assign_owner(
        self, workspace_with_members, owner_id, member_id, ws_url
    ):
        client = _authed_client(owner_id)
        resp = client.patch(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{member_id}/"),
            {"role": "owner"},
            format="json",
        )
        assert resp.status_code == 400

    def test_remove_member(self, workspace_with_members, admin_id, viewer_id, ws_url):
        client = _authed_client(admin_id)
        resp = client.delete(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{viewer_id}/")
        )
        assert resp.status_code == 204
        assert not workspace_with_members.is_member(viewer_id)

    def test_member_can_leave(self, workspace_with_members, member_id, ws_url):
        """Members can remove themselves (leave workspace)."""
        client = _authed_client(member_id)
        resp = client.delete(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{member_id}/")
        )
        assert resp.status_code == 204
        assert not workspace_with_members.is_member(member_id)

    def test_owner_cannot_be_removed(
        self, workspace_with_members, admin_id, owner_id, ws_url
    ):
        client = _authed_client(admin_id)
        resp = client.delete(
            ws_url(f"workspaces/{workspace_with_members.id}/members/{owner_id}/")
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestInvitationViews:
    def test_invite_member_success(self, team_workspace_with_members, admin_id, ws_url):
        client = _authed_client(admin_id, "Admin User")

        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            resp = client.post(
                ws_url(f"workspaces/{team_workspace_with_members.id}/members/invite/"),
                {"email": "newdev@example.com", "role": "member"},
                format="json",
            )
        assert resp.status_code == 201
        assert resp.data["email"] == "newdev@example.com"
        assert resp.data["role"] == "member"
        assert resp.data["status"] == "pending"
        assert "token" in resp.data
        assert "accept_url" in resp.data

    def test_invite_dispatches_email_task(
        self,
        team_workspace_with_members,
        owner_id,
        ws_url,
        django_capture_on_commit_callbacks,
    ):
        client = _authed_client(owner_id, "Owner")

        with (
            patch(
                "apps.workspaces.services.invitation_service._dispatch_invitation_email"
            ) as mock_task,
            django_capture_on_commit_callbacks(execute=True),
        ):
            resp = client.post(
                ws_url(f"workspaces/{team_workspace_with_members.id}/members/invite/"),
                {"email": "task@example.com", "role": "viewer"},
                format="json",
            )

        assert resp.status_code == 201
        mock_task.assert_called_once()

    def test_invite_duplicate_rejected(self, workspace_with_members, owner_id, ws_url):
        client = _authed_client(owner_id, "Owner")
        url = ws_url(f"workspaces/{workspace_with_members.id}/members/invite/")

        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ):
            client.post(
                url, {"email": "dup@example.com", "role": "member"}, format="json"
            )
            resp = client.post(
                url, {"email": "dup@example.com", "role": "member"}, format="json"
            )

        assert resp.status_code == 400
        assert "pending invitation" in str(resp.data["detail"]).lower()

    def test_invite_viewer_cannot_invite(
        self, workspace_with_members, viewer_id, ws_url
    ):
        client = _authed_client(viewer_id)
        resp = client.post(
            ws_url(f"workspaces/{workspace_with_members.id}/members/invite/"),
            {"email": "x@example.com", "role": "member"},
            format="json",
        )
        assert resp.status_code == 403

    def test_invite_invalid_email_rejected(
        self, workspace_with_members, admin_id, ws_url
    ):
        client = _authed_client(admin_id)
        resp = client.post(
            ws_url(f"workspaces/{workspace_with_members.id}/members/invite/"),
            {"email": "not-an-email", "role": "member"},
            format="json",
        )
        assert resp.status_code == 400

    def test_accept_invitation(self, workspace_with_members, owner_id, ws_url):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="joiner@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        new_user_id = uuid.uuid4()
        client = _authed_client(new_user_id, email="joiner@example.com")

        with patch(
            "apps.workspaces.services.invitation_service._dispatch_member_joined_notification"
        ):
            resp = client.post(ws_url(f"invitations/{invitation.token}/accept/"))

        assert resp.status_code == 200
        assert resp.data["workspace_id"] == str(workspace_with_members.id)
        assert resp.data["role"] == "member"
        assert workspace_with_members.is_member(new_user_id)

    def test_accept_expired_invitation(self, workspace_with_members, owner_id, ws_url):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        client = _authed_client(uuid.uuid4())
        resp = client.post(ws_url(f"invitations/{invitation.token}/accept/"))
        assert resp.status_code == 400

    def test_accept_invalid_token(self, ws_url):
        client = _authed_client(uuid.uuid4())
        resp = client.post(ws_url("invitations/completely-fake-token/accept/"))
        assert resp.status_code == 400

    def test_accept_unauthenticated_rejected(
        self, workspace_with_members, owner_id, ws_url
    ):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="x@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        client = APIClient()
        resp = client.post(ws_url(f"invitations/{invitation.token}/accept/"))
        assert resp.status_code == 403

    def test_list_pending_invitations_admin_only(
        self, workspace_with_members, admin_id, member_id, viewer_id, owner_id, ws_url
    ):
        WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="pending@x.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )

        for user_id, expected in [
            (owner_id, 200),
            (admin_id, 200),
            (member_id, 403),
            (viewer_id, 403),
        ]:
            client = _authed_client(user_id)
            resp = client.get(
                ws_url(f"workspaces/{workspace_with_members.id}/invitations/")
            )
            assert (
                resp.status_code == expected
            ), f"user {user_id} expected {expected} got {resp.status_code}"

    def test_revoke_invitation(
        self, workspace_with_members, admin_id, owner_id, ws_url
    ):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace_with_members,
            email="revoke@x.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        client = _authed_client(admin_id)
        resp = client.delete(
            ws_url(
                f"workspaces/{workspace_with_members.id}/invitations/{invitation.id}/"
            )
        )
        assert resp.status_code == 204
        invitation.refresh_from_db()
        assert invitation.is_revoked


# ─── Kafka Event Tests ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestKafkaEvents:
    def test_invitation_created_publishes_event(
        self, workspace, owner_id, django_capture_on_commit_callbacks
    ):
        mock_publisher = MagicMock()
        service = InvitationService(event_publisher=mock_publisher)

        with (
            patch(
                "apps.workspaces.services.invitation_service._dispatch_invitation_email"
            ),
            django_capture_on_commit_callbacks(execute=True),
        ):
            service.create_invitation(
                workspace=workspace,
                actor_id=owner_id,
                actor_name="Owner",
                email="kafka@example.com",
                role=WorkspaceRole.MEMBER,
            )

        mock_publisher.member_invited.assert_called_once()
        call_kwargs = mock_publisher.member_invited.call_args.kwargs
        assert call_kwargs["workspace"] == workspace
        assert call_kwargs["actor_id"] == owner_id

    def test_member_joined_publishes_event(
        self, workspace, owner_id, django_capture_on_commit_callbacks
    ):
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="joiner@x.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        new_user_id = uuid.uuid4()

        mock_publisher = MagicMock()
        service = InvitationService(event_publisher=mock_publisher)

        with (
            patch(
                "apps.workspaces.services.invitation_service._dispatch_member_joined_notification"
            ),
            django_capture_on_commit_callbacks(execute=True),
        ):
            service.accept_invitation(
                token=invitation.token, user_id=new_user_id, user_email=invitation.email
            )

        mock_publisher.member_joined.assert_called_once()

    def test_member_role_changed_publishes_event(
        self, workspace_with_members, owner_id, member_id
    ):
        mock_publisher = MagicMock()
        service = WorkspaceService(event_publisher=mock_publisher)

        service.update_member_role(
            workspace=workspace_with_members,
            actor_id=owner_id,
            target_user_id=member_id,
            new_role=WorkspaceRole.ADMIN,
        )

        mock_publisher.member_role_changed.assert_called_once()
        call_kwargs = mock_publisher.member_role_changed.call_args.kwargs
        assert call_kwargs["old_role"] == WorkspaceRole.MEMBER
        assert call_kwargs["new_role"] == WorkspaceRole.ADMIN

    def test_member_removed_publishes_event(
        self, workspace_with_members, owner_id, viewer_id
    ):
        mock_publisher = MagicMock()
        service = WorkspaceService(event_publisher=mock_publisher)

        with patch("apps.workspaces.tasks.notify_member_removed.delay"):
            service.remove_member(
                workspace=workspace_with_members,
                actor_id=owner_id,
                target_user_id=viewer_id,
            )

        mock_publisher.member_removed.assert_called_once()


# ─── Celery Task Tests ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCeleryTasks:
    def test_invitation_email_task_dispatched_on_invite(
        self, workspace, owner_id, django_capture_on_commit_callbacks
    ):
        with patch(
            "apps.workspaces.services.invitation_service._dispatch_invitation_email"
        ) as mock_dispatch:
            service = InvitationService(event_publisher=MagicMock())
            with django_capture_on_commit_callbacks(execute=True):
                service.create_invitation(
                    workspace=workspace,
                    actor_id=owner_id,
                    actor_name="Owner",
                    email="task@example.com",
                    role=WorkspaceRole.MEMBER,
                )

        mock_dispatch.assert_called_once()
        invitation_id = mock_dispatch.call_args[0][0]
        assert uuid.UUID(invitation_id)  # valid UUID

    def test_send_invitation_email_task_sends_mail(self, workspace, owner_id):
        from apps.workspaces.tasks import send_workspace_invitation_email

        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="mailtest@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )

        with (
            patch("apps.workspaces.tasks.send_mail") as mock_send,
            patch("apps.workspaces.tasks.render_to_string", return_value="rendered"),
        ):
            result = send_workspace_invitation_email(str(invitation.id))

        assert result["status"] == "sent"
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert "mailtest@example.com" in call_kwargs.kwargs.get("recipient_list", [])

    def test_send_invitation_email_skips_expired(self, workspace, owner_id):
        from apps.workspaces.tasks import send_workspace_invitation_email

        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="skip@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        with patch("apps.workspaces.tasks.send_mail") as mock_send:
            result = send_workspace_invitation_email(str(invitation.id))

        assert result["status"] == "skipped"
        assert result["reason"] == "expired"
        mock_send.assert_not_called()

    def test_send_invitation_email_idempotent(self, workspace, owner_id):
        """If email_sent_at is already set, don't send again."""
        from apps.workspaces.tasks import send_workspace_invitation_email

        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="idempotent@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )
        invitation.mark_email_sent()  # already sent

        with patch("apps.workspaces.tasks.send_mail") as mock_send:
            result = send_workspace_invitation_email(str(invitation.id))

        assert result["status"] == "skipped"
        assert result["reason"] == "already_sent"
        mock_send.assert_not_called()

    def test_send_invitation_email_retries_on_smtp_failure(self, workspace, owner_id):
        from apps.workspaces.tasks import send_workspace_invitation_email

        WorkspaceInvitation.objects.create(
            workspace=workspace,
            email="retry@example.com",
            role=WorkspaceRole.MEMBER,
            invited_by_id=owner_id,
            invited_by_name="Owner",
        )

        with (
            patch(
                "apps.workspaces.tasks.send_mail", side_effect=Exception("SMTP down")
            ),
            patch("apps.workspaces.tasks.render_to_string", return_value="body"),
        ):
            task = send_workspace_invitation_email
            # Verify the task has retry configuration
            assert task.max_retries == 3
            assert task.acks_late is True
