"""Django admin configuration for project and task models."""
from django.contrib import admin

from .models import Project, Task, TaskKnowledgeLink, TaskLink, TaskRepositoryLink


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin for Project — supports name/description search, status/visibility filtering."""

    list_display = ["name", "workspace_id", "status", "visibility", "owner_id", "created_at"]
    list_filter = ["status", "visibility", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin for Task — supports title/description search, status/priority/type filtering."""

    list_display = ["title", "project", "status", "priority", "assignee_id", "due_date", "created_at"]
    list_filter = ["status", "priority", "task_type", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(TaskLink)
class TaskLinkAdmin(admin.ModelAdmin):
    """Admin for TaskLink — displays source → target dependency relationships."""

    list_display = ["source_task", "relationship_type", "target_task", "created_at"]
    list_filter = ["relationship_type"]
    readonly_fields = ["id", "created_at"]


admin.site.register(TaskRepositoryLink)
admin.site.register(TaskKnowledgeLink)
