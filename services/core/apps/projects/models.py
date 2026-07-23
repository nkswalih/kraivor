"""Data models for projects and tasks.

All entities use UUID primary keys and soft-delete via ``deleted_at`` (inherited
from ``TimestampedModel``). The ``Project`` and ``Task`` models are workspace-scoped
— every query in the service layer enforces ``workspace_id`` filtering.

Design decisions:
  - ``Project.owner_id`` is a plain UUID (not a FK to the auth service) to avoid
    cross-service coupling — the auth service is a separate Django app.
  - ``Task.position`` uses ``FloatField`` for O(1) insert-between operations
    (see ``POSITION_MULTIPLIER`` / ``_rebalance_positions``).
  - ``Task.parent_task`` is a self-referential FK supporting subtask hierarchies.
  - Link models (``TaskLink``, ``TaskRepositoryLink``, ``TaskKnowledgeLink``) use
    ``UniqueConstraint`` to prevent duplicate relationships.
"""

import uuid
from django.db import models
from django.utils import timezone

from apps.workspaces.models import TimestampedModel

from .constants import (
    ProjectStatus,
    ProjectVisibility,
    TaskLinkType,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class Project(TimestampedModel):
    """A workspace-scoped project that groups related tasks together."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="projects",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    color = models.CharField(max_length=7, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNING,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=20,
        choices=ProjectVisibility.choices,
        default=ProjectVisibility.WORKSPACE,
    )
    repository = models.ForeignKey(
        "repositories.Repository",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    knowledge_space = models.ForeignKey(
        "knowledge.KnowledgeSpace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    owner_id = models.UUIDField()
    created_by = models.UUIDField()

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["workspace_id"], name="projects_workspace_idx"),
            models.Index(
                fields=["workspace_id", "status"], name="projects_workspace_status_idx"
            ),
            models.Index(
                fields=["workspace_id", "-updated_at"],
                name="projects_workspace_updated_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Project({self.name!r}, workspace={self.workspace_id})"

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class Task(TimestampedModel):
    """A unit of work scoped to a project; supports subtasks, position ordering, and soft-delete."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subtasks",
    )
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.BACKLOG
    )
    priority = models.CharField(
        max_length=20, choices=TaskPriority.choices, default=TaskPriority.MEDIUM
    )
    task_type = models.CharField(
        max_length=30, choices=TaskType.choices, default=TaskType.FEATURE
    )
    assignee_id = models.UUIDField(null=True, blank=True)
    reporter_id = models.UUIDField()
    due_date = models.DateField(null=True, blank=True)
    estimate_points = models.PositiveSmallIntegerField(null=True, blank=True)
    position = models.FloatField(default=0.0)
    created_by = models.UUIDField()

    class Meta:
        ordering = ["position", "-created_at"]
        indexes = [
            models.Index(fields=["project_id"], name="tasks_project_idx"),
            models.Index(fields=["assignee_id"], name="tasks_assignee_idx"),
            models.Index(
                fields=["project_id", "status"], name="tasks_project_status_idx"
            ),
            models.Index(fields=["due_date"], name="tasks_due_date_idx"),
        ]

    def __str__(self) -> str:
        return f"Task({self.title!r}, status={self.status}, project={self.project_id})"

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r}>"

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class TaskLink(models.Model):
    """Directed dependency relationship between two tasks (source → target)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="outgoing_links"
    )
    target_task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="incoming_links"
    )
    relationship_type = models.CharField(max_length=20, choices=TaskLinkType.choices)
    created_by = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_task", "target_task", "relationship_type"],
                name="unique_task_link",
            )
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return (
            f"TaskLink({self.source_task_id} "
            f"\u2192[{self.relationship_type}]\u2192 {self.target_task_id})"
        )


class TaskRepositoryLink(models.Model):
    """Links a task to a repository for cross-app traceability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="repository_links"
    )
    repository = models.ForeignKey(
        "repositories.Repository", on_delete=models.CASCADE, related_name="task_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "repository"], name="unique_task_repository_link"
            )
        ]

    def __str__(self) -> str:
        return f"TaskRepositoryLink(task={self.task_id}, repo={self.repository_id})"


class TaskKnowledgeLink(models.Model):
    """Links a task to a knowledge space for cross-app traceability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="knowledge_links"
    )
    knowledge_space = models.ForeignKey(
        "knowledge.KnowledgeSpace", on_delete=models.CASCADE, related_name="task_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "knowledge_space"], name="unique_task_knowledge_link"
            )
        ]

    def __str__(self) -> str:
        return (
            f"TaskKnowledgeLink(task={self.task_id}, space={self.knowledge_space_id})"
        )
