import logging
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import slugify

from .constants import TRENDING_WINDOW_HOURS
from .models import Comment, Discussion, Tag, Vote

logger = logging.getLogger(__name__)

PAGE_SIZE = 20


class DiscussionService:
    @staticmethod
    def list_discussions(
        page=1,
        page_size=PAGE_SIZE,
        tag=None,
        sort="latest",
        workspace_id=None,
    ):
        qs = Discussion.objects.select_related(None).prefetch_related("tags")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        if tag:
            qs = qs.filter(tags__slug=tag)
        if sort == "trending":
            cutoff = timezone.now() - timedelta(hours=TRENDING_WINDOW_HOURS)
            qs = qs.filter(created_at__gte=cutoff).order_by("-upvote_count", "-created_at")
        elif sort == "top":
            qs = qs.order_by("-upvote_count", "-created_at")
        else:
            qs = qs.order_by("-is_pinned", "-created_at")
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def get_detail(discussion_id: str):
        return Discussion.objects.prefetch_related("tags").filter(id=discussion_id).first()

    @staticmethod
    def create_discussion(data, user_id, username, display_name, avatar_url):
        tag_objs = []
        tag_names = data.pop("tags", [])
        for name in tag_names[:5]:
            slug = slugify(name)[:60]
            tag, _ = Tag.objects.get_or_create(
                slug=slug,
                defaults={"name": name[:50]},
            )
            Tag.objects.filter(id=tag.id).update(usage_count=F("usage_count") + 1)
            tag.refresh_from_db()
            tag_objs.append(tag)
        discussion = Discussion.objects.create(
            workspace_id=data.get("workspace_id"),
            title=data["title"],
            body=data["body"],
            author_id=user_id,
            author_username=username,
            author_display_name=display_name,
            author_avatar_url=avatar_url,
        )
        if tag_objs:
            discussion.tags.set(tag_objs)
        return discussion

    @staticmethod
    def update_discussion(discussion, data, tag_names=None):
        for field in ("title", "body", "is_resolved"):
            if field in data:
                setattr(discussion, field, data[field])
        discussion.save(update_fields=["title", "body", "is_resolved", "updated_at"])
        if tag_names is not None:
            tag_objs = []
            for name in tag_names[:5]:
                slug = slugify(name)[:60]
                tag, _ = Tag.objects.get_or_create(
                    slug=slug,
                    defaults={"name": name[:50]},
                )
                tag_objs.append(tag)
            discussion.tags.set(tag_objs)
        return discussion

    @staticmethod
    def soft_delete(discussion, user_id):
        discussion.soft_delete()
        return discussion

    @staticmethod
    def get_trending(limit=10):
        cutoff = timezone.now() - timedelta(hours=TRENDING_WINDOW_HOURS)
        return list(
            Discussion.objects.filter(created_at__gte=cutoff)
            .order_by("-upvote_count")[:limit]
            .values(
                "id",
                "title",
                "author_username",
                "author_display_name",
                "author_avatar_url",
                "upvote_count",
                "comment_count",
                "created_at",
            )
        )


class CommentService:
    @staticmethod
    def get_by_id(comment_id: str, discussion_id: str):
        return Comment.objects.filter(id=comment_id, discussion_id=discussion_id).first()

    @staticmethod
    def get_comments(discussion_id: str, page=1, page_size=30, sort="newest"):
        qs = (
            Comment.objects.filter(discussion_id=discussion_id, parent__isnull=True)
            .select_related(None)
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
    def get_replies(parent_id: str):
        return list(
            Comment.objects.filter(parent_id=parent_id)
            .select_related(None)
            .order_by("created_at")
        )

    @staticmethod
    def create_comment(discussion, data, user_id, username, display_name, avatar_url):
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
    def soft_delete(comment, user_id):
        comment.soft_delete()
        Discussion.objects.filter(id=comment.discussion_id).update(
            comment_count=F("comment_count") - 1
        )
        return comment


class VoteService:
    @staticmethod
    def vote_discussion(discussion, user_id: str, value: int):
        existing = Vote.objects.filter(user_id=user_id, discussion=discussion).first()
        if existing:
            if existing.value == value:
                return existing, "no_change"
            old_value = existing.value
            existing.value = value
            existing.save(update_fields=["value"])
            delta = value - old_value
            if delta > 0:
                Discussion.objects.filter(id=discussion.id).update(
                    upvote_count=F("upvote_count") + 1,
                    downvote_count=F("downvote_count") - 1,
                )
            else:
                Discussion.objects.filter(id=discussion.id).update(
                    upvote_count=F("upvote_count") - 1,
                    downvote_count=F("downvote_count") + 1,
                )
            return existing, "changed"
        vote = Vote.objects.create(user_id=user_id, discussion=discussion, value=value)
        if value == 1:
            Discussion.objects.filter(id=discussion.id).update(
                upvote_count=F("upvote_count") + 1
            )
        else:
            Discussion.objects.filter(id=discussion.id).update(
                downvote_count=F("downvote_count") + 1
            )
        return vote, "created"

    @staticmethod
    def remove_discussion_vote(discussion, user_id: str):
        vote = Vote.objects.filter(user_id=user_id, discussion=discussion).first()
        if not vote:
            return False
        was_upvote = vote.value == 1
        vote.delete()
        if was_upvote:
            Discussion.objects.filter(id=discussion.id).update(
                upvote_count=F("upvote_count") - 1
            )
        else:
            Discussion.objects.filter(id=discussion.id).update(
                downvote_count=F("downvote_count") - 1
            )
        return True

    @staticmethod
    def vote_comment(comment, user_id: str, value: int):
        existing = Vote.objects.filter(user_id=user_id, comment=comment).first()
        if existing:
            if existing.value == value:
                return existing, "no_change"
            old_value = existing.value
            existing.value = value
            existing.save(update_fields=["value"])
            delta = value - old_value
            if delta > 0:
                Comment.objects.filter(id=comment.id).update(
                    upvote_count=F("upvote_count") + 1,
                    downvote_count=F("downvote_count") - 1,
                )
            else:
                Comment.objects.filter(id=comment.id).update(
                    upvote_count=F("upvote_count") - 1,
                    downvote_count=F("downvote_count") + 1,
                )
            return existing, "changed"
        vote = Vote.objects.create(user_id=user_id, comment=comment, value=value)
        if value == 1:
            Comment.objects.filter(id=comment.id).update(
                upvote_count=F("upvote_count") + 1
            )
        else:
            Comment.objects.filter(id=comment.id).update(
                downvote_count=F("downvote_count") + 1
            )
        return vote, "created"

    @staticmethod
    def remove_comment_vote(comment, user_id: str):
        vote = Vote.objects.filter(user_id=user_id, comment=comment).first()
        if not vote:
            return False
        was_upvote = vote.value == 1
        vote.delete()
        if was_upvote:
            Comment.objects.filter(id=comment.id).update(
                upvote_count=F("upvote_count") - 1
            )
        else:
            Comment.objects.filter(id=comment.id).update(
                downvote_count=F("downvote_count") - 1
            )
        return True

    @staticmethod
    def get_user_votes(user_id: str, discussion_ids: list = None, comment_ids: list = None):
        q = Q(user_id=user_id)
        if discussion_ids:
            q &= Q(discussion_id__in=discussion_ids)
        elif comment_ids:
            q &= Q(comment_id__in=comment_ids)
        return {str(v.discussion_id or v.comment_id): v.value for v in Vote.objects.filter(q)}


class TagService:
    @staticmethod
    def get_popular_tags(limit=20):
        return list(Tag.objects.order_by("-usage_count")[:limit])

    @staticmethod
    def search_tags(query: str, limit=10):
        return list(
            Tag.objects.filter(name__icontains=query).order_by("-usage_count")[:limit]
        )
