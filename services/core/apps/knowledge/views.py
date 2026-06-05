"""
Knowledge Space views — KRV-022 (Knowledge Workspace / Infinite Canvas).

View contract:
  - Extract and validate input via serializers
  - Delegate all business logic to the service layer
  - Translate service exceptions to HTTP responses
  - Return clean, typed responses

Two view classes follow two distinct URL shapes:

  KnowledgeSpaceListCreateView  — workspace-scoped (uses WorkspaceContextMixin)
    GET  /workspace/workspaces/{workspace_pk}/knowledge/?search=
    POST /workspace/workspaces/{workspace_pk}/knowledge/

  KnowledgeSpaceDetailView      — resource-scoped (owns its own membership guard)
    GET    /workspace/knowledge/{pk}/
    PUT    /workspace/knowledge/{pk}/
    DELETE /workspace/knowledge/{pk}/

Authorization:
  Membership check for list/create uses _get_workspace_or_404() from
  WorkspaceContextMixin (identical to repositories).

  For detail, _get_knowledge_space_or_404() fetches the knowledge space
  with select_related("workspace") then verifies workspace membership via
  workspace.is_member(). Non-members receive 404, not 403, to avoid
  leaking existence information — the same security model used by
  _get_workspace_or_404().

  Role enforcement (can_write / can_admin) happens inside the service;
  the service raises KnowledgePermissionError which the view maps to 403.
"""

import logging
import uuid

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.views import WorkspaceContextMixin

from .models import KnowledgeSpace
from .serializers import (
    KnowledgeSpaceCreateSerializer,
    KnowledgeSpaceListSerializer,
    KnowledgeSpaceSerializer,
    KnowledgeSpaceUpdateSerializer,
)
from .services import (
    KnowledgePermissionError,
    KnowledgeSpaceNotFoundError,
    KnowledgeSpaceService,
)

logger = logging.getLogger(__name__)


# ─── List + Create ────────────────────────────────────────────────────────────

class KnowledgeSpaceListCreateView(WorkspaceContextMixin, APIView):
    """
    GET  /workspace/workspaces/{workspace_pk}/knowledge/
    POST /workspace/workspaces/{workspace_pk}/knowledge/

    GET  — list all active knowledge spaces in the workspace.
           Accepts optional ?search= query parameter that filters by name
           and description (case-insensitive OR).
           Available to all active workspace members (all roles).

    POST — create a new knowledge space (infinite canvas).
           Requires can_write role (owner, admin, or member).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk=None):
        """
        List knowledge spaces, with optional name/description search.
        Any active workspace member (including viewers) may call this.
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        search = request.query_params.get("search", "").strip() or None

        knowledge_spaces = KnowledgeSpaceService().list_knowledge_spaces(
            workspace=workspace,
            search=search,
        )
        return Response(
            KnowledgeSpaceListSerializer(knowledge_spaces, many=True).data
        )

    def post(self, request, workspace_pk=None):
        """
        Create a knowledge space. Requires can_write (member, admin, or owner).
        Returns HTTP 201 with the full representation (including canvas_data).
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        serializer = KnowledgeSpaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            knowledge_space = KnowledgeSpaceService().create_knowledge_space(
                workspace=workspace,
                actor_id=self._get_user_id(),
                name=validated["name"],
                description=validated.get("description"),
                canvas_data=validated.get("canvas_data"),
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            KnowledgeSpaceSerializer(knowledge_space).data,
            status=status.HTTP_201_CREATED,
        )


# ─── Detail (Retrieve / Update / Delete) ─────────────────────────────────────

class KnowledgeSpaceDetailView(APIView):
    """
    GET    /workspace/knowledge/{pk}/
    PUT    /workspace/knowledge/{pk}/
    DELETE /workspace/knowledge/{pk}/

    These endpoints are not nested under /workspaces/ because the client
    already holds the knowledge space UUID after the list/create call.
    The workspace membership check is performed inside
    _get_knowledge_space_or_404() before any operation.
    """

    permission_classes = [IsAuthenticated]

    def _get_knowledge_space_or_404(self, pk) -> KnowledgeSpace:
        """
        F 
        Returns 404 for both "doesn't exist" and "requesting user is not a
        workspace member" to avoid leaking information about workspace contents
        to outsiders — same security model as WorkspaceContextMixin.

        select_related("workspace") avoids a separate workspace query while
        still allowing workspace.is_member() to run its own membership check.
        """
        try:
            ks_id = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
        except (ValueError, AttributeError) as exc:
            raise NotFound("Knowledge space not found.") from exc

        user_id = self.request.user_id

        ks = (
            KnowledgeSpace.objects
            .select_related("workspace")
            .filter(id=ks_id)
            .first()
        )

        if not ks or not ks.workspace.is_member(user_id):
            raise NotFound("Knowledge space not found.")

        return ks

    def get(self, request, pk=None):
        """
        Retrieve a knowledge space including its full canvas_data.
        Any active workspace member (including viewers) may call this.
        """
        knowledge_space = self._get_knowledge_space_or_404(pk)
        return Response(KnowledgeSpaceSerializer(knowledge_space).data)

    def put(self, request, pk=None):
        """
        Full update of a knowledge space.

        name is required. description and canvas_data are optional — absent
        fields are preserved (practical concession for large canvas payloads).

        Requires can_write role (member, admin, or owner).
        Returns HTTP 200 with the updated full representation.
        """
        knowledge_space = self._get_knowledge_space_or_404(pk)

        serializer = KnowledgeSpaceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = KnowledgeSpaceService().update_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=self.request.user_id,
                updates=serializer.validated_data,
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(KnowledgeSpaceSerializer(updated).data)

    def delete(self, request, pk=None):
        """
        Soft-delete a knowledge space.
        Requires can_admin role (admin or owner).
        Returns HTTP 204 No Content on success.
        """
        knowledge_space = self._get_knowledge_space_or_404(pk)

        try:
            KnowledgeSpaceService().delete_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=self.request.user_id,
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)