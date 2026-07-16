import logging
import requests
import uuid
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.selectors import WorkspaceSelector
from apps.workspaces.serializers import (
    MemberRoleUpdateSerializer,
    WorkspaceInvitationCreateSerializer,
    WorkspaceInvitationSerializer,
    WorkspaceMemberSerializer,
)
from apps.workspaces.services import (
    InvitationError,
    InvitationService,
    WorkspaceLimitError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
)

from .workspaces import WorkspaceDetailView

logger = logging.getLogger(__name__)


def _resolve_member_users(member_data: list[dict]) -> dict[str, dict]:
    user_ids = [m["user_id"] for m in member_data if "user_id" in m]
    if not user_ids:
        return {}

    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/auth/internal/resolve-users-by-id/"
    try:
        resp = requests.post(
            endpoint,
            json={"user_ids": user_ids},
            headers={settings.INTERNAL_REQUEST_HEADER: settings.INTERNAL_REQUEST_SECRET},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("users", {})
    except requests.exceptions.RequestException:
        logger.warning("member_user_resolve.failed", extra={"user_ids": user_ids})
    return {}


def _enrich_member_data(data: list[dict], resolved: dict) -> list:
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
    return data


@extend_schema(tags=["Workspace Members"])
class MemberListCreateView(WorkspaceDetailView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List workspace members",
        responses={200: WorkspaceMemberSerializer(many=True)},
    )
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        members = WorkspaceSelector.get_members(workspace.id)
        data = WorkspaceMemberSerializer(members, many=True).data
        resolved = _resolve_member_users(data)
        return Response(_enrich_member_data(data, resolved))

    @extend_schema(
        summary="Invite member",
        request=WorkspaceInvitationCreateSerializer,
        responses={201: WorkspaceInvitationSerializer},
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        serializer = WorkspaceInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        actor_name = getattr(request, "user_name", "") or "A team member"

        try:
            invitation = InvitationService().create_invitation(
                workspace=workspace,
                actor_id=request.user_id,
                actor_name=actor_name,
                email=validated["email"],
                role=validated["role"],
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except (WorkspaceLimitError, InvitationError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(
            WorkspaceInvitationSerializer(
                invitation, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Workspace Members"])
class MemberDetailView(WorkspaceDetailView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update member role",
        request=MemberRoleUpdateSerializer,
        responses={200: WorkspaceMemberSerializer},
    )
    def patch(
        self, request: Request, workspace_pk: str | None = None, pk: str | None = None
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError as exc:
            raise NotFound("Member not found.") from exc

        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            member = WorkspaceService().update_member_role(
                workspace=workspace,
                actor_id=request.user_id,
                target_user_id=target_user_id,
                new_role=serializer.validated_data["role"],
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except WorkspaceNotFoundError as exc:
            raise NotFound("Member not found.") from exc

        data = WorkspaceMemberSerializer(member).data
        resolved = _resolve_member_users([data])
        return Response(_enrich_member_data([data], resolved)[0])

    @extend_schema(summary="Remove member", responses={204: None})
    def delete(
        self, request: Request, workspace_pk: str | None = None, pk: str | None = None
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError as exc:
            raise NotFound("Member not found.") from exc

        try:
            WorkspaceService().remove_member(
                workspace=workspace,
                actor_id=request.user_id,
                target_user_id=target_user_id,
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except WorkspaceNotFoundError as exc:
            raise NotFound("Member not found.") from exc

        return Response(status=status.HTTP_204_NO_CONTENT)
