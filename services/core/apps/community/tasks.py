import logging

from celery import shared_task
from django.utils import timezone

from .constants import TRENDING_WINDOW_HOURS
from .models import Discussion

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue="core")
def update_author_denormalization(self, author_id, username, display_name, avatar_url):
    try:
        updated_discussions = Discussion.objects.filter(author_id=author_id).update(
            author_username=username,
            author_display_name=display_name,
            author_avatar_url=avatar_url,
        )
        logger.info(
            "denormalization.discussions.updated",
            extra={"author_id": author_id, "count": updated_discussions},
        )
        from .models import Comment

        updated_comments = Comment.objects.filter(author_id=author_id).update(
            author_username=username,
            author_display_name=display_name,
            author_avatar_url=avatar_url,
        )
        logger.info(
            "denormalization.comments.updated",
            extra={"author_id": author_id, "count": updated_comments},
        )
    except Exception as exc:
        logger.exception("denormalization.failed", extra={"author_id": author_id})
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=300, queue="core")
def recalculate_discussion_counters(self, discussion_id):
    try:
        discussion = Discussion.all_objects.filter(id=discussion_id).first()
        if not discussion:
            logger.warning(
                "counters.discussion_not_found", extra={"discussion_id": discussion_id}
            )
            return
        from .models import Comment, Vote

        upvotes = Vote.objects.filter(discussion=discussion, value=1).count()
        downvotes = Vote.objects.filter(discussion=discussion, value=-1).count()
        comments = Comment.objects.filter(discussion=discussion).count()

        discussion.upvote_count = upvotes
        discussion.downvote_count = downvotes
        discussion.comment_count = comments
        discussion.save(
            update_fields=[
                "upvote_count",
                "downvote_count",
                "comment_count",
                "updated_at",
            ]
        )

        logger.info(
            "counters.recalculated",
            extra={
                "discussion_id": discussion_id,
                "upvotes": upvotes,
                "downvotes": downvotes,
                "comments": comments,
            },
        )
    except Exception as exc:
        logger.exception(
            "counters.recalculate_failed", extra={"discussion_id": discussion_id}
        )
        raise self.retry(exc=exc) from exc


@shared_task(queue="core")
def update_trending_scores():
    cutoff = timezone.now() - timezone.timedelta(hours=TRENDING_WINDOW_HOURS)
    discussions = Discussion.objects.filter(created_at__gte=cutoff).order_by(
        "-upvote_count"
    )[:20]
    logger.info(
        "trending.updated",
        extra={"count": len(discussions)},
    )
    return [str(d.id) for d in discussions]
