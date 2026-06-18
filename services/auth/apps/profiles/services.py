import logging

from django.db.models import F, Q

from profiles.models import Profile, UserFollow

logger = logging.getLogger(__name__)


class ProfileService:
    @staticmethod
    def get_by_username(username: str) -> Profile | None:
        return Profile.objects.filter(username=username).first()

    @staticmethod
    def get_by_user_id(user_id: str) -> Profile | None:
        return Profile.objects.filter(user_id=user_id).first()

    @staticmethod
    def search(query: str, page: int = 1, page_size: int = 20):
        qs = Profile.public.filter(
            Q(username__icontains=query)
            | Q(display_name__icontains=query)
            | Q(bio__icontains=query)
        ).order_by("-reputation_score", "username")
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def get_leaderboard(page: int = 1, page_size: int = 50):
        qs = Profile.objects.filter(is_public=True).order_by(
            "-reputation_score", "username"
        )
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def get_followers(
        profile: Profile, page: int = 1, page_size: int = 20, request_user_id: str | None = None
    ):
        qs = (
            UserFollow.objects.filter(following=profile.user)
            .select_related("follower__profile")
            .order_by("-created_at")
        )
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def get_following(
        profile: Profile, page: int = 1, page_size: int = 20, request_user_id: str | None = None
    ):
        qs = (
            UserFollow.objects.filter(follower=profile.user)
            .select_related("following__profile")
            .order_by("-created_at")
        )
        offset = (page - 1) * page_size
        total = qs.count()
        items = qs[offset : offset + page_size]
        return items, total

    @staticmethod
    def is_following(follower_user_id: str, target_user_id: str) -> bool:
        return UserFollow.objects.filter(
            follower_id=follower_user_id, following_id=target_user_id
        ).exists()

    @staticmethod
    def follow(follower_user_id: str, target_user_id: str) -> UserFollow | None:
        if follower_user_id == target_user_id:
            logger.warning("follow.self", extra={"user_id": follower_user_id})
            return None
        follow, created = UserFollow.objects.get_or_create(
            follower_id=follower_user_id, following_id=target_user_id
        )
        return follow if created else None

    @staticmethod
    def unfollow(follower_user_id: str, target_user_id: str) -> bool:
        deleted, _ = UserFollow.objects.filter(
            follower_id=follower_user_id, following_id=target_user_id
        ).delete()
        return deleted > 0


class ReputationService:
    @staticmethod
    def get_top_contributors(limit: int = 10):
        profiles = (
            Profile.objects.filter(is_public=True)
            .select_related("user")
            .order_by("-reputation_score")[:limit]
        )
        return [
            {
                "user_id": str(p.user_id),
                "username": p.username,
                "display_name": p.display_name,
                "avatar_url": p.avatar_url or (p.user.avatar_url or ""),
                "user_avatar_url": p.user.avatar_url or "",
                "reputation_score": p.reputation_score,
                "discussion_count": p.discussion_count,
                "comment_count": p.comment_count,
            }
            for p in profiles
        ]
