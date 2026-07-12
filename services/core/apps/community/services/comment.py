from django.db.models import F, Prefetch, QuerySet

from ..models import Comment, Discussion, Vote

logger = __import__("logging").getLogger(__name__)


class CommentService:
    @staticmethod
    def get_by_id(comment_id: str, discussion_id: str) -> Comment | None:
        return Comment.objects.filter(
            id=comment_id, discussion_id=discussion_id
        ).first()

    @staticmethod
    def get_comments(
        discussion_id: str,
        page: int = 1,
        page_size: int = 30,
        sort: str = "newest",
        user_id: str | None = None,
    ) -> tuple[QuerySet, int]:
        qs = Comment.objects.filter(
            discussion_id=discussion_id, parent__isnull=True
        ).select_related(None)
        if user_id:
            qs = qs.prefetch_related(
                Prefetch(
                    "votes",
                    queryset=Vote.objects.filter(user_id=user_id),
                    to_attr="_user_votes",
                ),
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(deleted_at__isnull=True),
                    to_attr="_all_replies",
                ),
            )
        else:
            qs = qs.prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(deleted_at__isnull=True),
                    to_attr="_all_replies",
                )
            )
        if sort == "top":
            qs = qs.order_by("-upvote_count", "-created_at")
        else:
            qs = qs.order_by("-created_at")
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def get_replies(parent_id: str, user_id: str | None = None) -> list[Comment]:
        qs = Comment.objects.filter(parent_id=parent_id).select_related(None)
        if user_id:
            qs = qs.prefetch_related(
                Prefetch(
                    "votes",
                    queryset=Vote.objects.filter(user_id=user_id),
                    to_attr="_user_votes",
                )
            )
        return list(qs.order_by("created_at"))

    @staticmethod
    def create_comment(
        discussion: Discussion,
        data: dict,
        user_id: str,
        username: str,
        display_name: str,
        avatar_url: str,
    ) -> Comment:
        comment = Comment.objects.create(
            discussion=discussion,
            parent_id=data.get("parent_id"),
            body=data["body"],
            author_id=user_id,
            author_username=username,
            author_display_name=display_name,
            author_avatar_url=avatar_url,
        )
        Discussion.objects.filter(id=discussion.id).update(
            comment_count=F("comment_count") + 1
        )
        return comment

    @staticmethod
    def soft_delete(comment: Comment, user_id: str) -> Comment:
        comment.soft_delete()
        Discussion.objects.filter(id=comment.discussion_id).update(
            comment_count=F("comment_count") - 1
        )
        return comment
