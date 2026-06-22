import uuid
from django.db.models import Count, Prefetch, QuerySet

from apps.community.models import Comment, Discussion


class DiscussionSelector:
    MAX_POPULAR_TAGS = 50

    @staticmethod
    def list_for_workspace(workspace_id: uuid.UUID, tag: str | None = None) -> QuerySet[Discussion]:
        qs = Discussion.objects.filter(
            workspace_id=workspace_id, deleted_at__isnull=True
        ).prefetch_related("tags")
        if tag:
            qs = qs.filter(tags__name__iexact=tag)
        return qs.order_by("-created_at")

    @staticmethod
    def get_detail(discussion_id: uuid.UUID, workspace_id: uuid.UUID) -> Discussion | None:
        return (
            Discussion.objects.prefetch_related(
                "tags",
                Prefetch(
                    "comments",
                    queryset=Comment.objects.filter(
                        deleted_at__isnull=True, parent__isnull=True
                    ).select_related("parent"),
                ),
            )
            .filter(
                id=discussion_id, workspace_id=workspace_id, deleted_at__isnull=True
            )
            .first()
        )

    @staticmethod
    def trending(workspace_id: uuid.UUID, limit: int = 10) -> QuerySet[Discussion]:
        return (
            Discussion.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            )
            .annotate(
                vote_score=Count("votes"),
                comment_count=Count("comments"),
            )
            .order_by("-vote_score", "-created_at")[:limit]
        )

    @staticmethod
    def popular_tags(workspace_id: uuid.UUID) -> QuerySet[str]:
        return (
            Discussion.objects.filter(
                workspace_id=workspace_id, deleted_at__isnull=True
            )
            .values_list("tags__name", flat=True)
            .annotate(count=Count("tags"))
            .order_by("-count")[: DiscussionSelector.MAX_POPULAR_TAGS]
        )


class CommentSelector:
    @staticmethod
    def list_for_discussion(discussion_id: uuid.UUID) -> QuerySet[Comment]:
        return (
            Comment.objects.filter(
                discussion_id=discussion_id,
                deleted_at__isnull=True,
                parent__isnull=True,
            )
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(deleted_at__isnull=True).order_by(
                        "created_at"
                    ),
                )
            )
            .order_by("created_at")
        )

    @staticmethod
    def get_replies(comment_id: uuid.UUID) -> QuerySet[Comment]:
        return (
            Comment.objects.filter(parent_id=comment_id, deleted_at__isnull=True)
            .order_by("created_at")
        )
