import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsProjectOwnerOrWorkspaceAdmin, IsWorkspaceMember
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
from core.pagination import StandardPagination
from .services import AIRecommendationService, ProjectService, TaskService

logger = logging.getLogger(__name__)


class ProjectListCreateView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status")
        projects = ProjectService.list_for_workspace(
            workspace_id=request.workspace_id,
            status=status_filter,
            user_id=request.user_id,
        )
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = ProjectCreateSerializer(
            data=request.data,
            context={
                "workspace_id": request.workspace_id,
                "request": request,
            },
        )
        serializer.is_valid(raise_exception=True)
        project = ProjectService.create(
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request, project_id: str) -> Response:
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
        )
        return Response(ProjectSerializer(project).data, status=status.HTTP_200_OK)

    def patch(self, request: Request, project_id: str) -> Response:
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
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

    def delete(self, request: Request, project_id: str) -> Response:
        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
        )
        self.check_object_permissions(request, project)
        ProjectService.delete(project=project, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAuthenticated(), IsWorkspaceMember(), IsProjectOwnerOrWorkspaceAdmin()]
        return [IsAuthenticated(), IsWorkspaceMember()]


class ProjectTaskListView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request, project_id: str) -> Response:
        ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
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


class ProjectAIRecommendationsView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request, project_id: str) -> Response:
        ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
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


class TaskListCreateView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request) -> Response:
        tasks = TaskService.list_for_workspace(
            workspace_id=request.workspace_id,
            project_id=request.query_params.get("project_id"),
            status=request.query_params.get("status"),
            assignee_id=request.query_params.get("assignee_id"),
            priority=request.query_params.get("priority"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(tasks, request)
        serializer = TaskSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"project_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = ProjectService.get(
            project_id=str(project_id),
            workspace_id=request.workspace_id,
        )

        serializer = TaskCreateSerializer(
            data=request.data,
            context={
                "workspace_id": request.workspace_id,
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


class TaskDetailView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    def patch(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update(
            task=task,
            user_id=request.user_id,
            **serializer.validated_data,
        )
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    def delete(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        TaskService.delete(task=task, user_id=request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskStatusUpdateView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def patch(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
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


class TaskDependencyView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        serializer = TaskDependencySerializer(
            data=request.data,
            context={"workspace_id": request.workspace_id},
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


class TaskDependencyDestroyView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def delete(self, request: Request, task_id: str, dependency_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        TaskService.remove_dependency(
            task=task,
            dependency_id=str(dependency_id),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskRepositoryLinkView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        serializer = TaskRepositoryLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_repository(
            task=task,
            repository_id=str(serializer.validated_data["repository_id"]),
            workspace_id=request.workspace_id,
        )
        return Response(
            {"id": str(link.id), "repository_id": str(link.repository_id)},
            status=status.HTTP_201_CREATED,
        )


class TaskKnowledgeLinkView(APIView):

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request: Request, task_id: str) -> Response:
        task = TaskService.get(
            task_id=str(task_id),
            workspace_id=request.workspace_id,
        )
        serializer = TaskKnowledgeLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = TaskService.add_knowledge(
            task=task,
            knowledge_space_id=str(serializer.validated_data["knowledge_space_id"]),
            workspace_id=request.workspace_id,
        )
        return Response(
            {"id": str(link.id), "knowledge_space_id": str(link.knowledge_space_id)},
            status=status.HTTP_201_CREATED,
        )
