"""URL routing for the projects application.

All endpoints are scoped under ``workspaces/<uuid:workspace_pk>/`` — workspace
membership is validated in each view via ``WorkspaceContextMixin``.

API design:
  - ``/projects/`` — list and create projects
  - ``/projects/<project_id>/`` — retrieve, update, delete a project
  - ``/projects/<project_id>/tasks/`` — list tasks scoped to a project
  - ``/projects/<project_id>/ai/recommendations/`` — stubbed AI suggestions
  - ``/tasks/`` — list and create tasks at the workspace level
  - ``/tasks/<task_id>/`` — retrieve, update, delete a task
  - ``/tasks/<task_id>/status/`` — dedicated status-update endpoint
  - ``/tasks/<task_id>/dependencies/`` — manage dependency links
  - ``/tasks/<task_id>/repositories/`` — link repositories to tasks
  - ``/tasks/<task_id>/knowledge/`` — link knowledge spaces to tasks
"""

from django.urls import path

from apps.projects import views

app_name = "projects"

urlpatterns = [
    path(
        "workspaces/<uuid:workspace_pk>/projects/",
        views.ProjectListCreateView.as_view(),
        name="project-list-create",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/projects/<uuid:project_id>/",
        views.ProjectDetailView.as_view(),
        name="project-detail",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/projects/<uuid:project_id>/tasks/",
        views.ProjectTaskListView.as_view(),
        name="project-task-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/projects/<uuid:project_id>/ai/recommendations/",
        views.ProjectAIRecommendationsView.as_view(),
        name="project-ai-recommendations",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/",
        views.TaskListCreateView.as_view(),
        name="task-list-create",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/",
        views.TaskDetailView.as_view(),
        name="task-detail",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/status/",
        views.TaskStatusUpdateView.as_view(),
        name="task-status-update",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/dependencies/",
        views.TaskDependencyView.as_view(),
        name="task-dependency-create",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/dependencies/<uuid:dependency_id>/",
        views.TaskDependencyDestroyView.as_view(),
        name="task-dependency-destroy",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/repositories/",
        views.TaskRepositoryLinkView.as_view(),
        name="task-repository-link",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/repositories/<uuid:link_id>/",
        views.TaskRepositoryLinkDestroyView.as_view(),
        name="task-repository-link-destroy",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/knowledge/",
        views.TaskKnowledgeLinkView.as_view(),
        name="task-knowledge-link",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/tasks/<uuid:task_id>/knowledge/<uuid:link_id>/",
        views.TaskKnowledgeLinkDestroyView.as_view(),
        name="task-knowledge-link-destroy",
    ),
]
