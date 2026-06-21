import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.selectors import WorkspaceSelector
from apps.workspaces.serializers import (
    InvitationAcceptResponseSerializer,
    WorkspaceInvitationSerializer,
)
from apps.workspaces.services import (
    InvitationError,
    InvitationService,
    WorkspacePermissionError,
)

from .workspaces import WorkspaceDetailView


@extend_schema(tags=["Workspace Invitations"])
class InvitationListAdminView(WorkspaceDetailView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List pending invitations",
        responses={200: WorkspaceInvitationSerializer(many=True)},
    )
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        member = workspace.get_member(request.user_id)
        if not member or not member.can_admin:
            raise PermissionDenied(
                "Only workspace admins can view pending invitations."
            )
        invitations = InvitationService().list_pending_invitations(workspace=workspace)
        return Response(WorkspaceInvitationSerializer(invitations, many=True).data)


@extend_schema(tags=["Workspace Invitations"])
class InvitationRevokeView(WorkspaceDetailView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Revoke invitation",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, workspace_pk: str | None = None, invitation_id: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk, request.user_id)
        try:
            inv_id = uuid.UUID(str(invitation_id))
        except ValueError as exc:
            raise NotFound("Invitation not found.") from exc

        invitation = WorkspaceSelector.get_invitation(inv_id, workspace.id)
        if not invitation:
            raise NotFound("Invitation not found.")

        try:
            InvitationService().revoke_invitation(
                invitation=invitation, actor_id=request.user_id
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except InvitationError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Workspace Invitations"])
class InvitationAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Accept invitation",
        responses={200: InvitationAcceptResponseSerializer},
    )
    def post(self, request: Request, token: str | None = None) -> Response:
        if not token:
            raise NotFound("Invalid invitation link.")

        user_id = getattr(request, "user_id", None)
        if not user_id:
            raise PermissionDenied("You must be signed in to accept an invitation.")

        try:
            invitation, member = InvitationService().accept_invitation(
                token=token, user_id=user_id, user_email=request.user_email
            )
        except InvitationError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except Exception:
            logger = __import__("logging").getLogger(__name__)
            logger.exception(
                "invitation.accept.unexpected_error",
                extra={"token": token[:8] + "...", "user_id": str(user_id)},
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
