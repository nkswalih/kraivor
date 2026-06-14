from django.db import models


class ProjectStatus(models.TextChoices):
    PLANNING = "planning", "Planning"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class ProjectVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    WORKSPACE = "workspace", "Workspace"


class TaskStatus(models.TextChoices):
    BACKLOG = "backlog", "Backlog"
    TODO = "todo", "Todo"
    IN_PROGRESS = "in_progress", "In Progress"
    IN_REVIEW = "in_review", "In Review"
    BLOCKED = "blocked", "Blocked"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


TERMINAL_TASK_STATUSES = frozenset({TaskStatus.DONE, TaskStatus.CANCELLED})

ACTIVE_TASK_STATUSES = frozenset({
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW,
    TaskStatus.BLOCKED,
})


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class TaskType(models.TextChoices):
    FEATURE = "feature", "Feature"
    BUG = "bug", "Bug"
    IMPROVEMENT = "improvement", "Improvement"
    RESEARCH = "research", "Research"
    SPIKE = "spike", "Spike"
    DOCUMENTATION = "documentation", "Documentation"
    TECHNICAL_DEBT = "technical_debt", "Technical Debt"
    INCIDENT = "incident", "Incident"


class TaskLinkType(models.TextChoices):
    BLOCKS = "blocks", "Blocks"
    BLOCKED_BY = "blocked_by", "Blocked By"
    DUPLICATES = "duplicates", "Duplicates"
    RELATES_TO = "relates_to", "Relates To"
    CAUSED_BY = "caused_by", "Caused By"


POSITION_REBALANCE_THRESHOLD = 0.001
POSITION_MULTIPLIER = 1000.0
MAX_DEPENDENCY_DEPTH = 10
