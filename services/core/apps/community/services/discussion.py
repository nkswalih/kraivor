from datetime import timedelta

from django.db.models import Count, F, Prefetch, QuerySet
from django.utils import timezone
from django.utils.text import slugify

from ..constants import TRENDING_WINDOW_HOURS
from ..models import Comment, Discussion, Tag, Vote

logger = __import__("logging").getLogger(__name__)

PAGE_SIZE = 20


class DiscussionService:
    @staticmethod
    def list_discussions(
        page: int = 1,
        page_size: int = PAGE_SIZE,
        tag: str | None = None,
        sort: str = "latest",
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> tuple[QuerySet, int]:
        prefetches = ["tags"]
        if user_id:
            prefetches.append(
                Prefetch(
                    "votes",
                    queryset=Vote.objects.filter(user_id=user_id),
                    to_attr="_user_votes",
                )
            )
        qs = Discussion.objects.select_related(None).prefetch_related(*prefetches)
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        if tag:
            qs = qs.filter(tags__slug=tag)
        if sort == "trending":
            cutoff = timezone.now() - timedelta(hours=TRENDING_WINDOW_HOURS)
            qs = qs.filter(created_at__gte=cutoff).order_by(
                "-upvote_count", "-created_at"
            )
        elif sort == "top":
            qs = qs.order_by("-upvote_count", "-created_at")
        else:
            qs = qs.order_by("-is_pinned", "-created_at")
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size].annotate(
            _comment_count=Count("comments")
        )
        return items, total

    @staticmethod
    def get_detail(discussion_id: str) -> Discussion | None:
        return (
            Discussion.objects.prefetch_related("tags").filter(id=discussion_id).first()
        )

    @staticmethod
    def create_discussion(
        data: dict,
        user_id: str,
        username: str,
        display_name: str,
        avatar_url: str,
    ) -> Discussion:
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
    def update_discussion(
        discussion: Discussion, data: dict, tag_names: list[str] | None = None
    ) -> Discussion:
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
    def soft_delete(discussion: Discussion, user_id: str) -> Discussion:
        discussion.soft_delete()
        return discussion

    @staticmethod
    def get_trending(limit: int = 10) -> list[dict]:
        cutoff = timezone.now() - timedelta(hours=TRENDING_WINDOW_HOURS)
        discussions = list(
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
        ids = [d["id"] for d in discussions]
        if ids:
            counts = dict(
                Comment.objects.filter(discussion_id__in=ids)
                .values("discussion_id")
                .annotate(cnt=Count("id"))
                .values_list("discussion_id", "cnt")
            )
            for d in discussions:
                d["comment_count"] = counts.get(d["id"], 0)
        return discussions
