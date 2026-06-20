"""Factory boy factories for projects test data.

Provides ``ProjectFactory``, ``TaskFactory``, and ``TaskLinkFactory`` for use
in test fixtures. Factories auto-generate UUIDs for owner/creator fields and
use ``factory.Sequence`` for unique names/titles.
"""
import uuid

import factory
import factory.django

from ..constants import ProjectStatus, TaskLinkType, TaskPriority, TaskStatus, TaskType
from ..models import Project, Task, TaskLink


class ProjectFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Project instances with sensible defaults."""
    class Meta:
        model = Project

    workspace = factory.SubFactory("apps.workspaces.tests.factories.WorkspaceFactory")
    name = factory.Sequence(lambda n: f"Project {n}")
    description = "Test project description"
    status = ProjectStatus.ACTIVE
    visibility = "workspace"
    owner_id = factory.LazyFunction(lambda: uuid.uuid4())
    created_by = factory.LazyFunction(lambda: uuid.uuid4())


class TaskFactory(factory.django.DjangoModelFactory):
    """Factory for creating test Task instances with sensible defaults and sequential positions."""
    class Meta:
        model = Task

    project = factory.SubFactory(ProjectFactory)
    title = factory.Sequence(lambda n: f"Task {n}")
    description = "Test task description"
    status = TaskStatus.BACKLOG
    priority = TaskPriority.MEDIUM
    task_type = TaskType.FEATURE
    reporter_id = factory.LazyFunction(lambda: uuid.uuid4())
    created_by = factory.LazyFunction(lambda: uuid.uuid4())
    position = factory.Sequence(lambda n: float(n * 1000))


class TaskLinkFactory(factory.django.DjangoModelFactory):
    """Factory for creating test TaskLink (dependency) instances with default BLOCKS relationship."""
    class Meta:
        model = TaskLink

    source_task = factory.SubFactory(TaskFactory)
    target_task = factory.SubFactory(TaskFactory)
    relationship_type = TaskLinkType.BLOCKS
    created_by = factory.LazyFunction(lambda: uuid.uuid4())
