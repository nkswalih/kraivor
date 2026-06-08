"""
Workspace views — KRV-019 (workspace CRUD) + KRV-020 (member management + invitations).

View contract:
  - Extract and validate input via serializers
  - Delegate business logic to service layer
  - Translate service exceptions to HTTP responses
  - Return clean, typed responses

New in KRV-020:
  WorkspaceMemberViewSet    — list, invite, update role, remove
  InvitationAcceptView      — POST /workspace/invitations/{token}/accept/

All authorization is layered:
  1. IsAuthenticated (gateway header present)
  2. Workspace membership check inside _get_workspace_or_404()
  3. Role checks inside service methods (raises WorkspacePermissionError)
"""

import logging
import uuid

from django.db.models import Count, Prefetch, Q
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .models import Workspace, WorkspaceInvitation, WorkspaceMember
from .permissions import IsAuthenticated
from .serializers import (
    InvitationAcceptResponseSerializer,
    MemberRoleUpdateSerializer,
    WorkspaceCreateSerializer,
    WorkspaceDetailSerializer,
    WorkspaceInvitationCreateSerializer,
    WorkspaceInvitationSerializer,
    WorkspaceListSerializer,
    WorkspaceMemberSerializer,
    WorkspaceUpdateSerializer,
)
from .services import (
    InvitationError,
    InvitationService,
    WorkspaceLimitError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
)

logger = logging.getLogger(__name__)


def _resolve_member_users(member_data: list[dict]) -> dict[str, dict]:
    """
    Batch-resolve user info (name, email) for a list of serialized member dicts.
    Calls the Identity internal API.

    Returns a dict keyed by user_id: {"id", "name", "email", "avatar_url"}.
    """
    import requests
    from django.conf import settings

    user_ids = [m["user_id"] for m in member_data if "user_id" in m]
    if not user_ids:
        return {}

    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/auth/internal/resolve-users-by-id/"
    try:
        resp = requests.post(
            endpoint,
            json={"user_ids": user_ids},
            headers={settings.INTERNAL_REQUEST_HEADER: "1"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("users", {})
    except requests.exceptions.RequestException:
        logger.warning("member_user_resolve.failed", extra={"user_ids": user_ids})
    return {}


class WorkspaceCursorPagination(CursorPagination):
    """Stable cursor pagination — safe during concurrent workspace creation."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"


# ─── Mixins ───────────────────────────────────────────────────────────────────


class WorkspaceContextMixin:
    """
    Common helpers shared across workspace viewsets.
    Provides: _get_user_id(), _get_workspace_or_404()
    """

    def _get_user_id(self) -> uuid.UUID:
        """Extract user_id injected by GatewayAuthMiddleware from X-User-ID header."""
        return self.request.user_id

    def _get_actor_name(self) -> str:
        """
        Extract the actor's display name from the request context.
        The gateway injects X-User-Name if available. Falls back to 'A team member'.
        """
        return getattr(self.request, "user_name", "") or "A team member"

    def _get_workspace_or_404(self, pk) -> Workspace:
        """
        Fetch workspace by PK. Returns 404 for both 'not found' and 'not a member'.
        Security: never reveal whether a workspace exists to non-members.

        pk may arrive as a uuid.UUID (from Django's <uuid:pk> URL converter) or
        as a string (when called internally). Both are handled safely.
        """
        try:
            workspace_id = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
        except (ValueError, AttributeError) as exc:
            raise NotFound("Workspace not found.") from exc

        user_id = self._get_user_id()

        workspace = (
            Workspace.objects.filter(id=workspace_id)
            .annotate(
                active_member_count=Count("members", filter=Q(members__deleted_at__isnull=True))
            )
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(deleted_at__isnull=True).order_by(
                        "joined_at"
                    ),
                )
            )
            .first()
        )

        if not workspace or not workspace.is_member(user_id):
            raise NotFound("Workspace not found.")

        return workspace


# ─── Workspace ViewSet (KRV-019) ──────────────────────────────────────────────


class WorkspaceViewSet(WorkspaceContextMixin, ViewSet):
    """
    Core workspace CRUD endpoints.

    GET    /workspace/workspaces/           list
    POST   /workspace/workspaces/           create
    GET    /workspace/workspaces/{id}/      retrieve
    PATCH  /workspace/workspaces/{id}/      partial_update
    DELETE /workspace/workspaces/{id}/      destroy
    """

    permission_classes = [IsAuthenticated]
    pagination_class = WorkspaceCursorPagination

    def list(self, request):
        user_id = self._get_user_id()
        member_workspace_ids = WorkspaceMember.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True,
        ).values_list("workspace_id", flat=True)

        workspaces = (
            Workspace.objects.filter(id__in=member_workspace_ids)
            .annotate(
                active_member_count=Count("members", filter=Q(members__deleted_at__isnull=True))
            )
            .order_by("-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(workspaces, request)
        serializer = WorkspaceListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    def create(self, request):
        user_id = self._get_user_id()
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            workspace = WorkspaceService().create_workspace(
                owner_id=user_id,
                name=validated["name"],
                slug=validated["slug"],
                avatar_url=validated.get("avatar_url"),
                description=validated.get("description"),
                settings=validated.get("settings", {}),
            )
        except WorkspaceLimitError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        from django.db.models import Q

        workspace = (
            Workspace.objects.filter(id=workspace.id)
            .annotate(
                active_member_count=Count("members", filter=Q(members__deleted_at__isnull=True))
            )
            .prefetch_related(
                Prefetch(
                    "members", queryset=WorkspaceMember.objects.filter(deleted_at__isnull=True)
                )
            )
            .first()
        )
        return Response(
            WorkspaceDetailSerializer(workspace, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        workspace = self._get_workspace_or_404(pk)
        return Response(WorkspaceDetailSerializer(workspace, context={"request": request}).data)

    def partial_update(self, request, pk=None):
        workspace = self._get_workspace_or_404(pk)
        serializer = WorkspaceUpdateSerializer(workspace, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated = WorkspaceService().update_workspace(
                workspace=workspace,
                actor_id=self._get_user_id(),
                updates=serializer.validated_data,
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(WorkspaceDetailSerializer(updated, context={"request": request}).data)

    def destroy(self, request, pk=None):
        workspace = self._get_workspace_or_404(pk)
        try:
            WorkspaceService().delete_workspace(
                workspace=workspace,
                actor_id=self._get_user_id(),
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Member ViewSet (KRV-020) ─────────────────────────────────────────────────


class WorkspaceMemberViewSet(WorkspaceContextMixin, ViewSet):
    """
    Member management endpoints nested under workspaces.

    GET    /workspace/workspaces/{workspace_pk}/members/
    POST   /workspace/workspaces/{workspace_pk}/members/invite/   (custom action)
    PATCH  /workspace/workspaces/{workspace_pk}/members/{pk}/
    DELETE /workspace/workspaces/{workspace_pk}/members/{pk}/

    Note: {pk} in member endpoints is the target user_id (UUID), not member row id.
    This is more intuitive for API consumers — they know user IDs, not member row IDs.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request, workspace_pk=None):
        """
        GET /workspace/workspaces/{workspace_pk}/members/

        Returns all active members ordered by joined_at.
        Includes resolved user info (name, email) via the Identity service.
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        members = workspace.members.filter(deleted_at__isnull=True).order_by(
            "joined_at", "created_at"
        )
        data = WorkspaceMemberSerializer(members, many=True).data
        resolved = _resolve_member_users(data)
        for m in data:
            uid = m["user_id"]
            info = resolved.get(uid)
            if info:
                m["user"] = {
                    "id": uid,
                    "name": info.get("name", uid[:8]),
                    "email": info.get("email", ""),
                    "avatar_url": info.get("avatar_url", None),
                }
        return Response(data)

    def invite(self, request, workspace_pk=None):
        """
        POST /workspace/workspaces/{workspace_pk}/members/invite/

        Creates a pending invitation and dispatches the email asynchronously.
        Returns the invitation object so the frontend can show a success state
        and optionally display the invite link for manual sharing.
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        serializer = WorkspaceInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            invitation = InvitationService().create_invitation(
                workspace=workspace,
                actor_id=self._get_user_id(),
                actor_name=self._get_actor_name(),
                email=validated["email"],
                role=validated["role"],
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except (WorkspaceLimitError, InvitationError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(
            WorkspaceInvitationSerializer(invitation, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, workspace_pk=None, pk=None):
        """
        PATCH /workspace/workspaces/{workspace_pk}/members/{user_id}/

        Change a member's role. {pk} = target user_id.
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError as exc:
            raise NotFound("Member not found.") from exc

        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            member = WorkspaceService().update_member_role(
                workspace=workspace,
                actor_id=self._get_user_id(),
                target_user_id=target_user_id,
                new_role=serializer.validated_data["role"],
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except WorkspaceNotFoundError as exc:
            raise NotFound("Member not found.") from exc

        data = WorkspaceMemberSerializer(member).data
        resolved = _resolve_member_users([data])
        uid = data["user_id"]
        info = resolved.get(uid)
        if info:
            data["user"] = {
                "id": uid,
                "name": info.get("name", uid[:8]),
                "email": info.get("email", ""),
                "avatar_url": info.get("avatar_url", None),
            }
        return Response(data)

    def destroy(self, request, workspace_pk=None, pk=None):
        """
        DELETE /workspace/workspaces/{workspace_pk}/members/{user_id}/

        Remove a member. {pk} = target user_id.
        Members can remove themselves (leave). Admins can remove others.
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError as exc:
            raise NotFound("Member not found.") from exc

        try:
            WorkspaceService().remove_member(
                workspace=workspace,
                actor_id=self._get_user_id(),
                target_user_id=target_user_id,
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except WorkspaceNotFoundError as exc:
            raise NotFound("Member not found.") from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Invitation Admin Views ───────────────────────────────────────────────────


class WorkspaceInvitationListView(WorkspaceContextMixin, APIView):
    """
    GET /workspace/workspaces/{workspace_pk}/invitations/

    List pending invitations for a workspace.
    Admin/owner only — viewers and members don't see pending invites.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        user_id = self._get_user_id()

        member = workspace.get_member(user_id)
        if not member or not member.can_admin:
            raise PermissionDenied("Only workspace admins can view pending invitations.")

        invitations = InvitationService().list_pending_invitations(workspace=workspace)
        return Response(WorkspaceInvitationSerializer(invitations, many=True).data)


class InvitationRevokeView(WorkspaceContextMixin, APIView):
    """
    DELETE /workspace/workspaces/{workspace_pk}/invitations/{invitation_id}/

    Revoke a pending invitation. Admin/owner only.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, workspace_pk=None, invitation_id=None):
        workspace = self._get_workspace_or_404(workspace_pk)

        try:
            inv_id = uuid.UUID(str(invitation_id))
        except ValueError as exc:
            raise NotFound("Invitation not found.") from exc

        try:
            invitation = WorkspaceInvitation.objects.select_related("workspace").get(
                id=inv_id,
                workspace=workspace,
            )
        except WorkspaceInvitation.DoesNotExist as exc:
            raise NotFound("Invitation not found.") from exc

        try:
            InvitationService().revoke_invitation(
                invitation=invitation,
                actor_id=self._get_user_id(),
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except InvitationError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Invitation Accept View (KRV-020) ─────────────────────────────────────────


class InvitationAcceptView(APIView):
    """
    POST /workspace/invitations/{token}/accept/

    The critical user journey endpoint:
      1. User receives invitation email
      2. Clicks the accept link → frontend redirects to this endpoint
      3. Gateway verifies JWT (user must be signed in or sign up first)
      4. This endpoint validates the token and creates the membership

    Public-ish endpoint: the token IS the credential.
    The user must still be authenticated (JWT required) because we need their
    user_id to create the WorkspaceMember record.

    Rate limiting: enforced at gateway level (lower limit for unauthenticated,
    standard limit for authenticated). The token's one-time use prevents brute-force.
    """

    permission_classes = [IsAuthenticated]  # must be authenticated to accept

    def post(self, request, token=None):
        if not token:
            raise NotFound("Invalid invitation link.")

        user_id = getattr(request, "user_id", None)
        if not user_id:
            raise PermissionDenied("You must be signed in to accept an invitation.")

        try:
            invitation, member = InvitationService().accept_invitation(
                token=token,
                user_id=user_id,
                user_email=request.user_email,
            )
        except InvitationError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except Exception as exc:
            logger.error(
                "invitation.accept.unexpected_error",
                extra={
                    "token": token[:8] + "...",  # log prefix only, not full token
                    "user_id": str(user_id),
                    "error": str(exc),
                },
            )
            raise

        workspace = invitation.workspace
        response_data = {
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
            "role": member.role,
            "joined_at": member.joined_at,
            "message": f"Welcome to {workspace.name}! You joined as {member.role}.",
        }

        serializer = InvitationAcceptResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
