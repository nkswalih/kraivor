AVATAR_SIZES = [64, 128, 256]
AVATAR_MAX_BYTES = 5 * 1024 * 1024
BANNER_MAX_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = frozenset(["image/png", "image/jpeg", "image/webp"])
AVATAR_KEY_PATTERN = "avatars/{user_id}/{size}.webp"
BANNER_KEY_PATTERN = "banners/{user_id}/banner.webp"
CDN_BASE_URL = "https://cdn.kraivor.com"
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50
USERNAME_REGEX = r"^[a-z0-9_]+$"
PROFILE_PAGE_SIZE = 20
LEADERBOARD_SIZE = 50
REPUTATION_EVENTS = {
    "discussion.created": +5,
    "discussion.deleted": -5,
    "discussion.upvoted": +2,
    "discussion.downvoted": -1,
    "comment.created": +1,
    "comment.deleted": -1,
    "comment.upvoted": +1,
}
