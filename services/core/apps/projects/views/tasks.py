import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from core.pagination import StandardPagination

from ..serializers import (
    TaskCreateSerializer,
    TaskDependencySerializer,
    TaskKnowledgeLinkSerializer,
    TaskRepositoryLinkSerializer,
    TaskSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
)
from ..services import ProjectService, TaskService
from .projects import WorkspaceContextMixin

logger = logging.getLogger(__name__)


@extend_schema(tags=["Tasks"])
class TaskListView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List tasks",
        responses={200: OpenApiResponse(description="Paginated task list")},
    )
    def get(self, request: Request, workspace_pk: str) -> Response:
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
        request=TaskCreateSerializer,
        responses={201: TaskSerializer},
    )
    def post(self, request: Request, workspace_pk: str) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"project_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project = ProjectService.get(
            project_id=str(project_id), workspace_id=str(workspace.id)
        )
        serializer = TaskCreateSerializer(
            data=request.data,
            context={"workspace_id": str(workspace.id), "project_id": str(project_id)},
        )
        serializer.is_valid(raise_exception=True)
        task = TaskService.create(
            project=project, reporter_id=request.user_id, **serializer.validated_data
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Tasks"])
class TaskDetailView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get task", responses={200: TaskSerializer})
    def get(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Update task",
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update(
            task=task, user_id=request.user_id, **serializer.validated_data
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Delete task",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        TaskService.delete(task=task, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Tasks"])
class TaskStatusUpdateView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update task status",
        request=TaskStatusUpdateSerializer,
        responses={200: TaskSerializer},
    )
    def patch(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_status(
            task=task,
            new_status=serializer.validated_data["status"],
            position=serializer.validated_data.get("position"),
            user_id=request.user_id,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)


@extend_schema(tags=["Tasks"])
class TaskDependencyView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add task dependency",
        request=TaskDependencySerializer,
        responses={201: OpenApiResponse(description="Dependency created")},
    )
    def post(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        serializer = TaskDependencySerializer(
            data=request.data, context={"workspace_id": str(workspace_pk)}
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


@extend_schema(tags=["Tasks"])
class TaskDependencyDestroyView(WorkspaceContextMixin, APIView):
    @extend_schema(
        summary="Remove task dependency",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk: str, task_id: str, dependency_id: str
    ) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        TaskService.remove_dependency(task=task, dependency_id=str(dependency_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Tasks"])
class TaskRepositoryLinkView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Link repository to task",
        request=TaskRepositoryLinkSerializer,
        responses={201: OpenApiResponse(description="Repository linked")},
    )
    def post(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        serializer = TaskRepositoryLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_repository(
            task=task,
            repository_id=str(serializer.validated_data["repository_id"]),
            workspace_id=str(workspace_pk),
        )
        return Response({"id": str(link.id)}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Tasks"])
class TaskRepositoryLinkDestroyView(WorkspaceContextMixin, APIView):
    @extend_schema(
        summary="Remove repository link from task",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk: str, task_id: str, link_id: str
    ) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        TaskService.remove_repository(task=task, link_id=str(link_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Tasks"])
class TaskKnowledgeLinkView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Link knowledge space to task",
        request=TaskKnowledgeLinkSerializer,
        responses={201: OpenApiResponse(description="Knowledge space linked")},
    )
    def post(self, request: Request, workspace_pk: str, task_id: str) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        serializer = TaskKnowledgeLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_knowledge(
            task=task,
            knowledge_space_id=str(serializer.validated_data["knowledge_space_id"]),
            workspace_id=str(workspace_pk),
        )
        return Response({"id": str(link.id)}, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Tasks"])
class TaskKnowledgeLinkDestroyView(WorkspaceContextMixin, APIView):
    @extend_schema(
        summary="Remove knowledge link from task",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(
        self, request: Request, workspace_pk: str, task_id: str, link_id: str
    ) -> Response:
        self._get_workspace_or_404(workspace_pk)
        task = TaskService.get(task_id=str(task_id), workspace_id=str(workspace_pk))
        TaskService.remove_knowledge(task=task, link_id=str(link_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
