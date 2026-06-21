import uuid

from django.db.models import QuerySet

from apps.repositories.models import Repository
from core.cache import CacheService


class RepositorySelector:
    @staticmethod
    def list_for_workspace(workspace_id: uuid.UUID) -> QuerySet[Repository]:
        return (
            Repository.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            )
            .select_related("workspace")
            .order_by("name")
        )

    @staticmethod
    def get_detail(repo_id: uuid.UUID, workspace_id: uuid.UUID) -> Repository | None:
        return (
            Repository.objects.filter(
                id=repo_id, workspace_id=workspace_id, deleted_at__isnull=True
            )
            .select_related("workspace")
            .first()
        )

    @staticmethod
    def count_for_workspace(workspace_id: uuid.UUID) -> int:
        key = f"repo:count:{workspace_id}"
        return CacheService.get_or_set(
            key=key,
            timeout=60,
            fallback=lambda: Repository.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            ).count(),
        )
