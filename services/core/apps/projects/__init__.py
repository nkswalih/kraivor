"""Projects application — workspace-scoped project and task management.

This app provides full CRUD for projects and tasks within a workspace context.
All endpoints are scoped under ``/api/workspaces/<workspace_pk>/`` and validate
workspace membership via ``WorkspaceContextMixin._get_workspace_or_404()``.

Key responsibilities:
  - Project lifecycle: planning active completed archived (soft-delete)
  - Task lifecycle with configurable status workflow, priority, and type taxonomy
  - Task dependency management with circular-dependency detection (BFS, max depth 10)
  - Position-based task ordering within each status column (float-based, auto-rebalance)
  - Linking tasks to repositories and knowledge spaces (cross-app integration)
  - Kafka event publishing for domain events via ``transaction.on_commit``
  - Celery background task for overdue detection

ADR notes:
  - Soft-delete pattern (``deleted_at`` timestamp) used instead of hard delete for
    auditability; all service-layer queries filter ``deleted_at__isnull=True``.
  - Position-based ordering uses ``float`` gaps (``POSITION_MULTIPLIER=1000.0``) with
    an auto-rebalance when the gap drops below ``POSITION_REBALANCE_THRESHOLD=0.001``.
  - Kafka events are published inside ``transaction.on_commit`` to avoid emitting
    events for rolled-back transactions (except ``task.overdue`` which comes from
    Celery outside any transaction).
  - Membership and ownership checks happen at two levels: workspace membership via
    ``_get_workspace_or_404`` (404 for non-members), object-level permissions via
    ``IsProjectOwnerOrWorkspaceAdmin`` (403 for non-owners/non-admins).
"""
