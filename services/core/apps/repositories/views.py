"""
Repository views — KRV-021 (Repository Metadata Management).

View contract:
  - Extract and validate input via serializers
  - Delegate all business logic to the service layer
  - Translate service exceptions to HTTP responses
  - Return clean, typed responses

Authorization model:
  - All requests require a valid X-User-ID (IsAuthenticated)
  - Workspace membership is verified by _get_workspace_or_404():
      non-members receive a 404, not a 403, to avoid leaking workspace existence
  - Role checks (admin/owner for write operations) are enforced in the service
      layer; the service raises RepositoryPermissionError which views map to 403

Endpoints (all under /workspace/ gateway prefix → /api/ in Django):
  GET    /workspace/workspaces/{workspace_pk}/repos/              — list
  POST   /workspace/workspaces/{workspace_pk}/repos/              — connect
  DELETE /workspace/workspaces/{workspace_pk}/repos/{repo_id}/    — disconnect
"""

import logging
import uuid

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.views import WorkspaceContextMixin

from .serializers import RepositoryConnectSerializer, RepositorySerializer
from .services import (
    GitHubAPIError,
    GitHubAuthError,
    RepositoryAlreadyConnectedError,
    RepositoryNotFoundError,
    RepositoryPermissionError,
    RepositoryService,
)

logger = logging.getLogger(__name__)


class RepositoryView(WorkspaceContextMixin, APIView):
    """
    GET  /workspace/workspaces/{workspace_pk}/repos/
    POST /workspace/workspaces/{workspace_pk}/repos/

    GET  — list all connected repositories; any active workspace member may call this.
    POST — connect a GitHub repository; admin/owner only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk=None):
        """
        List all active repositories connected to the workspace.
        Available to all active workspace members (owner, admin, member, viewer).
        """
        workspace = self._get_workspace_or_404(workspace_pk)
        repositories = RepositoryService().list_repositories(workspace=workspace)
        return Response(RepositorySerializer(repositories, many=True).data)

    def post(self, request, workspace_pk=None):
        """
        Connect a GitHub repository to the workspace.

        The service verifies the actor's GitHub OAuth token, fetches repository
        metadata from the GitHub API, and creates (or restores) the repository
        record. Admin/owner role required.

        Returns HTTP 201 with the full repository representation on success.
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        serializer = RepositoryConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            repository = RepositoryService().connect_repository(
                workspace=workspace,
                actor_id=self._get_user_id(),
                github_repo=serializer.validated_data["github_repo"],
            )
        except RepositoryPermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except RepositoryAlreadyConnectedError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except (GitHubAuthError, GitHubAPIError) as exc:
            # Surface GitHub errors as 400 so the frontend can show actionable
            # messages ("reconnect your GitHub account", "check repo name", etc.)
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(
            RepositorySerializer(repository).data,
            status=status.HTTP_201_CREATED,
        )


class RepositoryDetailView(WorkspaceContextMixin, APIView):
    """
    DELETE /workspace/workspaces/{workspace_pk}/repos/{repo_id}/

    Disconnect a repository from the workspace (soft delete).
    Admin/owner role required.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, workspace_pk=None, repo_id=None):
        """
        Disconnect the repository identified by repo_id.

        Returns HTTP 204 No Content on success.
        Returns HTTP 404 if the repository does not exist in this workspace
        or has already been disconnected.
        """
        workspace = self._get_workspace_or_404(workspace_pk)

        try:
            repository_id = uuid.UUID(str(repo_id))
        except (ValueError, AttributeError) as exc:
            raise NotFound("Repository not found.") from exc

        try:
            RepositoryService().disconnect_repository(
                workspace=workspace,
                actor_id=self._get_user_id(),
                repository_id=repository_id,
            )
        except RepositoryPermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except RepositoryNotFoundError as exc:
            raise NotFound(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)
