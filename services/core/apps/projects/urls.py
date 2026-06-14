from django.urls import path

from apps.projects import views

app_name = "projects"

urlpatterns = [
    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<uuid:project_id>/", views.ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<uuid:project_id>/tasks/", views.ProjectTaskListView.as_view(), name="project-task-list"),
    path("projects/<uuid:project_id>/ai/recommendations/", views.ProjectAIRecommendationsView.as_view(), name="project-ai-recommendations"),
    path("tasks/", views.TaskListCreateView.as_view(), name="task-list-create"),
    path("tasks/<uuid:task_id>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<uuid:task_id>/status/", views.TaskStatusUpdateView.as_view(), name="task-status-update"),
    path("tasks/<uuid:task_id>/dependencies/", views.TaskDependencyView.as_view(), name="task-dependency-create"),
    path("tasks/<uuid:task_id>/dependencies/<uuid:dependency_id>/", views.TaskDependencyDestroyView.as_view(), name="task-dependency-destroy"),
    path("tasks/<uuid:task_id>/repositories/", views.TaskRepositoryLinkView.as_view(), name="task-repository-link"),
    path("tasks/<uuid:task_id>/knowledge/", views.TaskKnowledgeLinkView.as_view(), name="task-knowledge-link"),
]
