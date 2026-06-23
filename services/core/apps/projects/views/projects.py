import logging
from typing import TYPE_CHECKING

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from core.pagination import StandardPagination

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace

from ..permissions import IsProjectOwnerOrWorkspaceAdmin
from ..serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    TaskSerializer,
)
from ..services import AIRecommendationService, ProjectService, TaskService

logger = logging.getLogger(__name__)


class WorkspaceContextMixin:
    def _get_user_id(self) -> str:
        return self.request.user_id

    def _get_workspace_or_404(self, workspace_pk: str) -> "Workspace":
        from apps.workspaces.selectors import WorkspaceSelector

        user_id = self._get_user_id()
        workspace = WorkspaceSelector.get_workspace_for_user(workspace_pk, user_id)
        if not workspace:
            from rest_framework.exceptions import NotFound

            raise NotFound("Workspace not found.")
        return workspace


@extend_schema(tags=["Projects"])
class ProjectListView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List projects",
        responses={200: ProjectSerializer(many=True)},
    )
    def get(self, request: Request, workspace_pk: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        status_filter = request.query_params.get("status")
        projects = ProjectService.list_for_workspace(
            workspace_id=str(workspace.id),
            status=status_filter,
            user_id=request.user_id,
        )
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Create project",
        request=ProjectCreateSerializer,
        responses={201: ProjectSerializer},
    )
    def post(self, request: Request, workspace_pk: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        serializer = ProjectCreateSerializer(
            data=request.data,
            context={"workspace_id": str(workspace.id), "request": request},
        )
        serializer.is_valid(raise_exception=True)
        project = ProjectService.create(
            workspace_id=str(workspace.id),
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Projects"])
class ProjectDetailView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get project",
        responses={200: ProjectSerializer},
    )
    def get(self, request: Request, workspace_pk: str, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update project",
        request=ProjectUpdateSerializer,
        responses={200: ProjectSerializer},
    )
    def patch(self, request: Request, workspace_pk: str, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id), workspace_id=str(workspace.id)
        )
        self.check_object_permissions(request, project)
        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = ProjectService.update(
            project=project, user_id=request.user_id, **serializer.validated_data
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete project",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, workspace_pk: str, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id), workspace_id=str(workspace.id)
        )
        self.check_object_permissions(request, project)
        ProjectService.delete(project=project, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self) -> list[type[BasePermission]]:
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAuthenticated(), IsProjectOwnerOrWorkspaceAdmin()]
        return [IsAuthenticated()]


@extend_schema(tags=["Projects"])
class ProjectTaskListView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List project tasks",
        responses={200: OpenApiResponse(description="Paginated task list response")},
    )
    def get(self, request: Request, workspace_pk: str, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        ProjectService.get(project_id=str(project_id), workspace_id=str(workspace.id))
        tasks = TaskService.list_for_project(
            project_id=str(project_id),
            status=request.query_params.get("status"),
            assignee_id=request.query_params.get("assignee_id"),
            priority=request.query_params.get("priority"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=["Projects"])
class ProjectAIRecommendationsView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get AI recommendations",
        responses={200: OpenApiResponse(description="AI recommendations")},
    )
    def get(self, request: Request, workspace_pk: str, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        ProjectService.get(project_id=str(project_id), workspace_id=str(workspace.id))
        return Response(
            {
                "suggested_tasks": AIRecommendationService.suggest_tasks_from_description(
                    project_id=str(project_id), description=""
                ),
                "blocked_risk": AIRecommendationService.detect_blocked_tasks(
                    project_id=str(project_id)
                ),
                "suggested_dependencies": [],
                "generated_at": timezone.now().isoformat(),
                "phase": "stub",
            },
            status=status.HTTP_200_OK,
        )
