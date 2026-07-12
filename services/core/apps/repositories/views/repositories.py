from typing import TYPE_CHECKING

import logging
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace

from ..github_app.serializers import InstallationRepoItemSerializer
from ..github_app.services import GitHubAppInstallationService
from ..serializers import RepositoryConnectSerializer, RepositorySerializer
from ..services import (
    GitHubAPIError,
    GitHubAuthError,
    RepositoryAlreadyConnectedError,
    RepositoryNotFoundError,
    RepositoryPermissionError,
    RepositoryService,
)

logger = logging.getLogger(__name__)


class WorkspaceContextMixin:
    def _get_user_id(self) -> str:
        return self.request.user_id

    def _get_workspace_or_404(self, workspace_pk: str) -> "Workspace":
        from apps.workspaces.selectors import WorkspaceSelector

        workspace = WorkspaceSelector.get_workspace_for_user(
            workspace_pk, self._get_user_id()
        )
        if not workspace:
            from rest_framework.exceptions import NotFound

            raise NotFound("Workspace not found.")
        return workspace

    def _get_actor_name(self) -> str:
        return getattr(self.request, "user_name", "") or "A team member"


@extend_schema(tags=["Repositories"])
class RepositoryListView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List repositories", responses={200: RepositorySerializer(many=True)}
    )
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        repos = RepositoryService().list_repositories(workspace=workspace)
        return Response(RepositorySerializer(repos, many=True).data)

    @extend_schema(
        summary="Connect repository",
        request=RepositoryConnectSerializer,
        responses={201: RepositorySerializer},
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        serializer = RepositoryConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            repo = RepositoryService().connect_repository(
                workspace=workspace,
                actor_id=request.user_id,
                **serializer.validated_data,
            )
        except RepositoryPermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except RepositoryAlreadyConnectedError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        except (GitHubAPIError, GitHubAuthError) as exc:
            raise ValidationError({"detail": f"GitHub error: {exc}"}) from exc
        return Response(RepositorySerializer(repo).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Repositories"])
class RepositoryDetailView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get repository", responses={200: RepositorySerializer})
    def get(
        self,
        request: Request,
        workspace_pk: str | None = None,
        repo_id: str | None = None,
    ) -> Response:
        self._get_workspace_or_404(workspace_pk)
        repo = RepositoryService().get_repository(
            repo_id=repo_id, workspace_id=workspace_pk
        )
        if not repo:
            raise NotFound("Repository not found.")
        return Response(RepositorySerializer(repo).data)

    @extend_schema(
        summary="Disconnect repository",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self,
        request: Request,
        workspace_pk: str | None = None,
        repo_id: str | None = None,
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        try:
            RepositoryService().disconnect_repository(
                repository_id=repo_id, workspace=workspace, actor_id=request.user_id
            )
        except RepositoryPermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except RepositoryNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Repositories"])
class GitHubRepoSearchView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Search GitHub repositories")
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        query = request.query_params.get("search") or request.query_params.get("q", "")
        query = query.strip()
        service = GitHubAppInstallationService()
        repos = service.list_available_repos(workspace=workspace, search=query)
        return Response(InstallationRepoItemSerializer(repos, many=True).data)
