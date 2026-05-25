"""
Workspace views — DRF ViewSets.

View responsibilities (strictly limited):
  - Extract input from request
  - Call serializer for validation
  - Call service for business logic
  - Return serialized response

Views do NOT contain business logic. They are the HTTP adapter layer.

Endpoint map:
  POST   /workspace/workspaces/                    create workspace
  GET    /workspace/workspaces/                    list user's workspaces
  GET    /workspace/workspaces/{id}/               get workspace detail
  PATCH  /workspace/workspaces/{id}/               update workspace (admin+)
  DELETE /workspace/workspaces/{id}/               soft delete (owner only)

  GET    /workspace/workspaces/{id}/members/       list members
  POST   /workspace/workspaces/{id}/members/       add member (admin+)
  PATCH  /workspace/workspaces/{id}/members/{uid}/ update role (admin+)
  DELETE /workspace/workspaces/{id}/members/{uid}/ remove member

Pagination: cursor-based for lists (consistent order, no offset drift).
"""

import logging
import uuid

from django.db.models import Count, Prefetch
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .constants import WorkspaceRole
from .models import Workspace, WorkspaceMember
from .permissions import IsAuthenticated
from .serializers import (
    MemberRoleUpdateSerializer,
    WorkspaceCreateSerializer,
    WorkspaceDetailSerializer,
    WorkspaceListSerializer,
    WorkspaceMemberSerializer,
    WorkspaceUpdateSerializer,
)
from .services import (
    WorkspaceLimitError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
)

logger = logging.getLogger(__name__)


class WorkspaceCursorPagination(CursorPagination):
    """
    Cursor-based pagination for workspace lists.
    Cursor pagination is stable — safe when new workspaces are created during iteration.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"


class WorkspaceViewSet(ViewSet):
    """
    Workspace CRUD endpoints.

    Inherits from ViewSet (not ModelViewSet) for explicit control over
    each action's queryset, serializer, and permission class.
    This is intentional — ModelViewSet's magic causes more problems than it solves
    in a production service with non-trivial permission logic.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = WorkspaceCursorPagination

    def _get_service(self) -> WorkspaceService:
        return WorkspaceService()

    def _get_user_id(self) -> uuid.UUID:
        """Extract user_id set by GatewayAuthMiddleware."""
        return self.request.user_id

    def _get_workspace_or_404(self, pk: str) -> Workspace:
        """
        Fetch workspace by PK, ensuring the requesting user is a member.
        Returns 404 (not 403) for non-members — never confirm workspace existence.
        """
        try:
            workspace_id = uuid.UUID(pk)
        except ValueError:
            raise NotFound("Workspace not found.")

        user_id = self._get_user_id()

        # Annotate with member_count for use in serializers
        workspace = (
            Workspace.objects.filter(id=workspace_id)
            .annotate(member_count=Count("members"))
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(deleted_at__isnull=True).order_by("joined_at"),
                )
            )
            .first()
        )

        if not workspace:
            raise NotFound("Workspace not found.")

        # Verify membership — return 404 to non-members (security: don't leak existence)
        if not workspace.is_member(user_id):
            raise NotFound("Workspace not found.")

        return workspace

    # ─── List ─────────────────────────────────────────────────────────────────

    def list(self, request):
        """
        GET /workspace/workspaces/
        Returns all workspaces the current user is a member of.
        """
        user_id = self._get_user_id()

        # Get all workspace IDs for this user via membership
        member_workspace_ids = WorkspaceMember.objects.filter(
            user_id=user_id,
        ).values_list("workspace_id", flat=True)

        workspaces = (
            Workspace.objects.filter(id__in=member_workspace_ids)
            .annotate(member_count=Count("members"))
            .order_by("-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(workspaces, request)

        serializer = WorkspaceListSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    # ─── Create ───────────────────────────────────────────────────────────────

    def create(self, request):
        """
        POST /workspace/workspaces/
        Creates a new workspace. The requesting user becomes the owner.
        """
        user_id = self._get_user_id()

        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        service = self._get_service()
        try:
            workspace = service.create_workspace(
                owner_id=user_id,
                name=validated["name"],
                slug=validated["slug"],
                avatar_url=validated.get("avatar_url"),
                description=validated.get("description"),
                settings=validated.get("settings", {}),
            )
        except WorkspaceLimitError as e:
            raise ValidationError({"detail": str(e)})

        # Re-fetch with annotations for the response
        workspace = (
            Workspace.objects.filter(id=workspace.id)
            .annotate(member_count=Count("members"))
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(deleted_at__isnull=True),
                )
            )
            .first()
        )

        serializer = WorkspaceDetailSerializer(workspace, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ─── Retrieve ─────────────────────────────────────────────────────────────

    def retrieve(self, request, pk=None):
        """
        GET /workspace/workspaces/{id}/
        """
        workspace = self._get_workspace_or_404(pk)
        serializer = WorkspaceDetailSerializer(workspace, context={"request": request})
        return Response(serializer.data)

    # ─── Update ───────────────────────────────────────────────────────────────

    def partial_update(self, request, pk=None):
        """
        PATCH /workspace/workspaces/{id}/
        Admin or owner only.
        """
        workspace = self._get_workspace_or_404(pk)
        user_id = self._get_user_id()

        # Check admin permission before deserializing — fail fast
        member = workspace.get_member(user_id)
        if not member or not member.can_admin:
            raise PermissionDenied("Only workspace admins and owners can update settings.")

        serializer = WorkspaceUpdateSerializer(
            workspace, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        service = self._get_service()
        updated_workspace = service.update_workspace(
            workspace=workspace,
            actor_id=user_id,
            updates=serializer.validated_data,
        )

        response_serializer = WorkspaceDetailSerializer(
            updated_workspace, context={"request": request}
        )
        return Response(response_serializer.data)

    # ─── Delete ───────────────────────────────────────────────────────────────

    def destroy(self, request, pk=None):
        """
        DELETE /workspace/workspaces/{id}/
        Owner only. Soft delete.
        """
        workspace = self._get_workspace_or_404(pk)
        user_id = self._get_user_id()

        service = self._get_service()
        try:
            service.delete_workspace(workspace=workspace, actor_id=user_id)
        except WorkspacePermissionError as e:
            raise PermissionDenied(str(e))

        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceMemberViewSet(ViewSet):
    """
    Member management endpoints nested under workspaces.

    Routes (registered as nested router):
      GET    /workspace/workspaces/{workspace_pk}/members/
      POST   /workspace/workspaces/{workspace_pk}/members/
      PATCH  /workspace/workspaces/{workspace_pk}/members/{user_id}/
      DELETE /workspace/workspaces/{workspace_pk}/members/{user_id}/
    """

    permission_classes = [IsAuthenticated]

    def _get_service(self) -> WorkspaceService:
        return WorkspaceService()

    def _get_user_id(self) -> uuid.UUID:
        return self.request.user_id

    def _get_workspace_or_404(self, workspace_pk: str) -> Workspace:
        try:
            workspace_id = uuid.UUID(workspace_pk)
        except ValueError:
            raise NotFound("Workspace not found.")

        user_id = self._get_user_id()
        workspace = Workspace.objects.filter(id=workspace_id).first()

        if not workspace or not workspace.is_member(user_id):
            raise NotFound("Workspace not found.")

        return workspace

    def list(self, request, workspace_pk=None):
        """GET /workspace/workspaces/{workspace_pk}/members/"""
        workspace = self._get_workspace_or_404(workspace_pk)
        members = workspace.members.order_by("joined_at")
        serializer = WorkspaceMemberSerializer(members, many=True)
        return Response(serializer.data)

    def create(self, request, workspace_pk=None):
        """
        POST /workspace/workspaces/{workspace_pk}/members/
        Body: { user_id: uuid, role: "member"|"admin"|"viewer" }
        Requires admin.
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        # Validate input
        user_id_raw = request.data.get("user_id")
        role = request.data.get("role", WorkspaceRole.MEMBER)

        if not user_id_raw:
            raise ValidationError({"user_id": "This field is required."})

        try:
            user_id = uuid.UUID(str(user_id_raw))
        except ValueError:
            raise ValidationError({"user_id": "Must be a valid UUID."})

        if role not in [WorkspaceRole.ADMIN, WorkspaceRole.MEMBER, WorkspaceRole.VIEWER]:
            raise ValidationError({"role": f"Invalid role: {role}"})

        service = self._get_service()
        try:
            member = service.add_member(
                workspace=workspace,
                actor_id=actor_id,
                user_id=user_id,
                role=role,
            )
        except WorkspacePermissionError as e:
            raise PermissionDenied(str(e))
        except WorkspaceLimitError as e:
            raise ValidationError({"detail": str(e)})
        except WorkspaceServiceError as e:
            raise ValidationError({"detail": str(e)})

        serializer = WorkspaceMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, workspace_pk=None, pk=None):
        """
        PATCH /workspace/workspaces/{workspace_pk}/members/{user_id}/
        Change a member's role. pk here is the target user_id.
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError:
            raise NotFound("Member not found.")

        serializer = MemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = self._get_service()
        try:
            member = service.update_member_role(
                workspace=workspace,
                actor_id=actor_id,
                target_user_id=target_user_id,
                new_role=serializer.validated_data["role"],
            )
        except WorkspacePermissionError as e:
            raise PermissionDenied(str(e))
        except WorkspaceNotFoundError:
            raise NotFound("Member not found.")

        response_serializer = WorkspaceMemberSerializer(member)
        return Response(response_serializer.data)

    def destroy(self, request, workspace_pk=None, pk=None):
        """
        DELETE /workspace/workspaces/{workspace_pk}/members/{user_id}/
        pk is the target user_id. Users can remove themselves (leave).
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        actor_id = self._get_user_id()

        try:
            target_user_id = uuid.UUID(str(pk))
        except ValueError:
            raise NotFound("Member not found.")

        service = self._get_service()
        try:
            service.remove_member(
                workspace=workspace,
                actor_id=actor_id,
                target_user_id=target_user_id,
            )
        except WorkspacePermissionError as e:
            raise PermissionDenied(str(e))
        except WorkspaceNotFoundError:
            raise NotFound("Member not found.")

        return Response(status=status.HTTP_204_NO_CONTENT)


# Re-export service error for views that catch it without importing services directly
WorkspaceServiceError = WorkspacePermissionError.__bases__[0]