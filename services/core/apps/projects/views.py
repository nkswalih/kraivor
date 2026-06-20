"""HTTP views for the projects application.

All views inherit from ``WorkspaceContextMixin`` which provides
``_get_workspace_or_404(workspace_pk)`` — this validates that the requesting
user is a member of the workspace and returns 404 if not (avoiding workspace
existence leaks).

Design:
  - Permission classes vary by method: read operations require only
    ``IsAuthenticated``; mutating operations (PATCH, DELETE) also enforce
    ``IsProjectOwnerOrWorkspaceAdmin`` at the object level.
  - All URL kwargs (``workspace_pk``, ``project_id``, ``task_id`` etc.) are
    passed as keyword arguments by Django's URL resolver.
  - Pagination uses ``StandardPagination`` (page-based with configurable size).
"""

import logging

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.views import WorkspaceContextMixin
from core.pagination import StandardPagination

from .permissions import IsProjectOwnerOrWorkspaceAdmin
from .serializers import (
    ProjectCreateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
    TaskCreateSerializer,
    TaskDependencySerializer,
    TaskKnowledgeLinkSerializer,
    TaskRepositoryLinkSerializer,
    TaskSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
)
from .services import AIRecommendationService, ProjectService, TaskService

logger = logging.getLogger(__name__)


class ProjectListCreateView(WorkspaceContextMixin, APIView):
    """GET  /api/workspaces/<pk>/projects/  — list projects (optional ``?status=`` filter)
    POST /api/workspaces/<pk>/projects/  — create a new project."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List projects",
        tags=["Projects"],
        responses={200: ProjectSerializer(many=True)},
    )
    def get(self, request: Request, workspace_pk) -> Response:
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
        tags=["Projects"],
        request=ProjectCreateSerializer,
        responses={201: ProjectSerializer},
    )
    def post(self, request: Request, workspace_pk) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        serializer = ProjectCreateSerializer(
            data=request.data,
            context={
                "workspace_id": str(workspace.id),
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)
        project = ProjectService.create(
            workspace_id=str(workspace.id),
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(WorkspaceContextMixin, APIView):
    """GET /api/workspaces/<pk>/projects/<id>/    — retrieve project
    PATCH  — update project (owner/admin only)
    DELETE — soft-delete project (owner/admin only)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get project",
        tags=["Projects"],
        responses={200: ProjectSerializer},
    )
    def get(self, request: Request, workspace_pk, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update project",
        tags=["Projects"],
        request=ProjectUpdateSerializer,
        responses={200: ProjectSerializer},
    )
    def patch(self, request: Request, workspace_pk, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )
        self.check_object_permissions(request, project)

        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        project = ProjectService.update(
            project=project,
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete project",
        tags=["Projects"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, workspace_pk, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )
        self.check_object_permissions(request, project)
        ProjectService.delete(project=project, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAuthenticated(), IsProjectOwnerOrWorkspaceAdmin()]
        return [IsAuthenticated()]


class ProjectTaskListView(WorkspaceContextMixin, APIView):
    """GET /api/workspaces/<pk>/projects/<id>/tasks/ — paginated task list for a project.

    Supports ``?status=``, ``?assignee_id=``, ``?priority=`` filters.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List project tasks",
        tags=["Projects"],
        responses={200: OpenApiResponse(description="Paginated task list response")},
    )
    def get(self, request: Request, workspace_pk, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )

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


class ProjectAIRecommendationsView(WorkspaceContextMixin, APIView):
    """GET /api/workspaces/<pk>/projects/<id>/ai/recommendations/ — stubbed AI suggestions.

    Currently returns empty lists for all recommendation types. Phase marker
    indicates this is a stub awaiting ML service integration.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get AI recommendations",
        tags=["Projects"],
        responses={200: OpenApiResponse(description="AI recommendations")},
    )
    def get(self, request: Request, workspace_pk, project_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )
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


class TaskListCreateView(WorkspaceContextMixin, APIView):
    """GET  /api/workspaces/<pk>/tasks/  — paginated workspace-level task list
    POST /api/workspaces/<pk>/tasks/  — create a task (requires ``project_id`` in body).

    Supports ``?project_id=``, ``?status=``, ``?assignee_id=``, ``?priority=`` filters.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List tasks",
        tags=["Projects"],
        responses={200: OpenApiResponse(description="Paginated task list response")},
    )
    def get(self, request: Request, workspace_pk) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        tasks = TaskService.list_for_workspace(
            workspace_id=str(workspace.id),
            project_id=request.query_params.get("project_id"),
            status=request.query_params.get("status"),
            assignee_id=request.query_params.get("assignee_id"),
            priority=request.query_params.get("priority"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create task",
        tags=["Projects"],
        request=TaskCreateSerializer,
        responses={201: TaskSerializer},
    )
    def post(self, request: Request, workspace_pk) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"project_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=str(workspace.id),
        )

        serializer = TaskCreateSerializer(
            data=request.data,
            context={
                "workspace_id": str(workspace.id),
                "project_id": str(project_id),
            },
        )
        serializer.is_valid(raise_exception=True)
        task = TaskService.create(
            project=project,
            reporter_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(WorkspaceContextMixin, APIView):
    """GET    /api/workspaces/<pk>/tasks/<id>/ — retrieve task
    PATCH   — update task fields
    DELETE  — soft-delete task (includes cascading to subtasks)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get task",
        tags=["Projects"],
        responses={200: TaskSerializer},
    )
    def get(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update task",
        tags=["Projects"],
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update(
            task=task,
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete task",
        tags=["Projects"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        TaskService.delete(task=task, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskStatusUpdateView(WorkspaceContextMixin, APIView):
    """PATCH /api/workspaces/<pk>/tasks/<id>/status/ — dedicated status + position update.

    Separate from the general PATCH to allow position-based reordering within
    status columns. Accepts ``status`` (required) and ``position`` (optional).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update task status",
        tags=["Projects"],
        request=TaskStatusUpdateSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_status(
            task=task,
            new_status=serializer.validated_data["status"],
            position=serializer.validated_data.get("position"),
            user_id=request.user_id,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)


class TaskDependencyView(WorkspaceContextMixin, APIView):
    """POST /api/workspaces/<pk>/tasks/<id>/dependencies/ — add a dependency.

    Validates: no self-dependency, no circular dependency (BFS, max depth 10).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add task dependency",
        tags=["Projects"],
        request=TaskDependencySerializer,
        responses={201: OpenApiResponse(description="Dependency created")},
    )
    def post(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        serializer = TaskDependencySerializer(
            data=request.data,
            context={"workspace_id": str(workspace.id)},
        )
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_dependency(
            task=task,
            target_task_id=str(serializer.validated_data["target_task_id"]),
            relationship_type=serializer.validated_data["relationship_type"],
            user_id=request.user_id,
        )
        return Response(
            {"id": str(link.id), "relationship_type": link.relationship_type},
            status=status.HTTP_201_CREATED,
        )


class TaskDependencyDestroyView(WorkspaceContextMixin, APIView):
    """DELETE /api/workspaces/<pk>/tasks/<id>/dependencies/<dep_id>/ — remove a dependency."""

    @extend_schema(
        summary="Remove task dependency",
        tags=["Projects"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk, task_id: str, dependency_id: str
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        TaskService.remove_dependency(
            task=task,
            dependency_id=str(dependency_id),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskRepositoryLinkDestroyView(WorkspaceContextMixin, APIView):
    """DELETE /api/workspaces/<pk>/tasks/<id>/repositories/<link_id>/ — remove a repository link."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove repository link from task",
        tags=["Projects"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk, task_id: str, link_id: str
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        TaskService.remove_repository(task=task, link_id=str(link_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskKnowledgeLinkDestroyView(WorkspaceContextMixin, APIView):
    """DELETE /api/workspaces/<pk>/tasks/<id>/knowledge/<link_id>/ — remove a knowledge link."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove knowledge link from task",
        tags=["Projects"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk, task_id: str, link_id: str
    ) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        TaskService.remove_knowledge(task=task, link_id=str(link_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskRepositoryLinkView(WorkspaceContextMixin, APIView):
    """POST /api/workspaces/<pk>/tasks/<id>/repositories/ — link a repository to the task.

    Validates that the repository exists in the same workspace.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Link repository to task",
        tags=["Projects"],
        request=TaskRepositoryLinkSerializer,
        responses={201: OpenApiResponse(description="Repository linked")},
    )
    def post(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        serializer = TaskRepositoryLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_repository(
            task=task,
            repository_id=str(serializer.validated_data["repository_id"]),
            workspace_id=str(workspace.id),
        )
        return Response(
            {"id": str(link.id), "repository_id": str(link.repository_id)},
            status=status.HTTP_201_CREATED,
        )


class TaskKnowledgeLinkView(WorkspaceContextMixin, APIView):
    """POST /api/workspaces/<pk>/tasks/<id>/knowledge/ — link a knowledge space to the task.

    Validates that the knowledge space exists in the same workspace.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Link knowledge space to task",
        tags=["Projects"],
        request=TaskKnowledgeLinkSerializer,
        responses={201: OpenApiResponse(description="Knowledge space linked")},
    )
    def post(self, request: Request, workspace_pk, task_id: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=str(workspace.id),
        )
        serializer = TaskKnowledgeLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_knowledge(
            task=task,
            knowledge_space_id=str(serializer.validated_data["knowledge_space_id"]),
            workspace_id=str(workspace.id),
        )
        return Response(
            {"id": str(link.id), "knowledge_space_id": str(link.knowledge_space_id)},
            status=status.HTTP_201_CREATED,
        )
