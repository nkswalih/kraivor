import uuid

from django.db.models import Count, Prefetch, Q, QuerySet

from apps.workspaces.models import Workspace, WorkspaceInvitation, WorkspaceMember
from core.cache import CacheService


class WorkspaceSelector:
    @staticmethod
    def get_workspace_for_user(
        workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> Workspace | None:
        return (
            Workspace.objects.filter(
                id=workspace_id,
                members__user_id=user_id,
                members__deleted_at__isnull=True,
            )
            .annotate(
                active_member_count=Count(
                    "members", filter=Q(members__deleted_at__isnull=True)
                )
            )
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(
                        deleted_at__isnull=True
                    ).order_by("joined_at"),
                ),
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(
                        user_id=user_id, deleted_at__isnull=True
                    ),
                    to_attr="_user_membership",
                ),
            )
            .first()
        )

    @staticmethod
    def list_user_workspace_ids(user_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            WorkspaceMember.objects.filter(
                user_id=user_id, deleted_at__isnull=True
            ).values_list("workspace_id", flat=True)
        )

    @staticmethod
    def list_user_workspaces(user_id: uuid.UUID) -> QuerySet[Workspace]:
        return (
            Workspace.objects.filter(
                members__user_id=user_id,
                members__deleted_at__isnull=True,
            )
            .annotate(
                active_member_count=Count(
                    "members", filter=Q(members__deleted_at__isnull=True)
                )
            )
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(
                        user_id=user_id, deleted_at__isnull=True
                    ),
                    to_attr="_user_membership",
                )
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_annotated_detail(workspace_id: uuid.UUID) -> Workspace | None:
        return (
            Workspace.objects.filter(id=workspace_id)
            .annotate(
                active_member_count=Count(
                    "members", filter=Q(members__deleted_at__isnull=True)
                )
            )
            .prefetch_related(
                Prefetch(
                    "members",
                    queryset=WorkspaceMember.objects.filter(deleted_at__isnull=True),
                )
            )
            .first()
        )

    @staticmethod
    def get_members(workspace_id: uuid.UUID) -> QuerySet[WorkspaceMember]:
        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id, deleted_at__isnull=True
        ).order_by("joined_at", "created_at")

    @staticmethod
    def get_invitation(
        invitation_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WorkspaceInvitation | None:
        try:
            return WorkspaceInvitation.objects.select_related("workspace").get(
                id=invitation_id, workspace_id=workspace_id
            )
        except WorkspaceInvitation.DoesNotExist:
            return None

    @staticmethod
    def get_member_count(workspace_id: uuid.UUID) -> int:
        key = f"ws:member_count:{workspace_id}"
        return CacheService.get_or_set(
            key=key,
            timeout=60,
            fallback=lambda: WorkspaceMember.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            ).count(),
        )

    @staticmethod
    def is_workspace_member(workspace_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id, user_id=user_id, deleted_at__isnull=True
        ).exists()
