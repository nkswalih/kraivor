from .projects import (
    ProjectAIRecommendationsView,
    ProjectDetailView,
    ProjectListView,
    ProjectTaskListView,
)
from .tasks import (
    TaskDependencyDestroyView,
    TaskDependencyView,
    TaskDetailView,
    TaskKnowledgeLinkDestroyView,
    TaskKnowledgeLinkView,
    TaskListView,
    TaskRepositoryLinkDestroyView,
    TaskRepositoryLinkView,
    TaskStatusUpdateView,
)

__all__ = [
    "ProjectAIRecommendationsView",
    "ProjectDetailView",
    "ProjectListView",
    "ProjectTaskListView",
    "TaskDependencyDestroyView",
    "TaskDependencyView",
    "TaskDetailView",
    "TaskKnowledgeLinkDestroyView",
    "TaskKnowledgeLinkView",
    "TaskListView",
    "TaskRepositoryLinkDestroyView",
    "TaskRepositoryLinkView",
    "TaskStatusUpdateView",
]
