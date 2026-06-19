import logging
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from profiles.constants import (
    ALLOWED_IMAGE_TYPES,
    AVATAR_MAX_BYTES,
    BANNER_MAX_BYTES,
)
from profiles.events import publish_profile_updated
from profiles.models import Profile
from profiles.permissions import IsAuthenticatedOrReadOnly
from profiles.serializers import (
    FollowerSerializer,
    FollowingSerializer,
    ProfileSerializer,
    UpdateProfileSerializer,
)
from profiles.services import ProfileService, ReputationService
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse

logger = logging.getLogger(__name__)

PAGE_SIZE = 20

_HEX_CHARS = set("0123456789abcdef")


def _is_temp_username(username: str) -> bool:
    """Check if the username is an auto-generated UUID prefix (12 hex chars)."""
    return len(username) == 12 and all(c in _HEX_CHARS for c in username)


def _user_id(request) -> str | None:
    if request.user.is_authenticated:
        return str(request.user.id)
    return None


class ProfileDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get profile",
        description="Returns profile details by username.",
        tags=["Profiles"],
        parameters=[OpenApiParameter("username", str, description="Profile username", location=OpenApiParameter.PATH)],
        responses={200: ProfileSerializer},
    )
    def get(self, request, username):
        uid = _user_id(request)
        profile = ProfileService.get_by_username(username)
        if not profile or (not profile.is_public and uid != str(profile.user_id)):
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProfileSerializer(profile)
        data = serializer.data
        data["is_following"] = bool(uid) and ProfileService.is_following(uid, str(profile.user_id))
        data["is_owner"] = uid is not None and uid == str(profile.user_id)
        return Response(data)

    @extend_schema(
        summary="Update profile",
        description="Update profile details. Only the profile owner can update.",
        tags=["Profiles"],
        request=UpdateProfileSerializer,
        responses={200: ProfileSerializer},
    )
    def patch(self, request, username):
        uid = _user_id(request)
        if not uid:  # pragma: no cover
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        profile = ProfileService.get_by_username(username)
        if not profile:  # pragma: no cover
            profile = ProfileService.get_by_user_id(uid)
        if not profile:  # pragma: no cover
            display_name = request.data.get("display_name", username)
            profile = Profile(user_id=uid, username=username, display_name=display_name)
        if uid != str(profile.user_id):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        old_values = {}
        for field in ("display_name", "bio", "avatar_url", "website_url"):
            old_values[field] = getattr(profile, field)
        serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():  # pragma: no cover
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        publish_profile_updated(profile, old_values=old_values)
        return Response(ProfileSerializer(profile).data)


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get my profile",
        description="Returns the authenticated users own profile.",
        tags=["Profiles"],
        responses={200: ProfileSerializer},
    )
    def get(self, request):
        uid = str(request.user.id)
        profile = ProfileService.get_by_user_id(uid)
        if not profile or _is_temp_username(profile.username):  # pragma: no cover
            return Response(
                {"detail": "Profile not found.", "code": "profile_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ProfileSerializer(profile).data
        data["is_owner"] = True
        return Response(data)


class ProfileSearchView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Search profiles",
        description="Search profiles by query string. Supports pagination.",
        tags=["Profiles"],
        parameters=[
            OpenApiParameter("q", str, description="Search query"),
            OpenApiParameter("page", int, description="Page number (1-indexed)"),
        ],
        responses={200: OpenApiResponse(description="Paginated search results")},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)
        page = int(request.query_params.get("page", 1))
        items, total = ProfileService.search(query, page=page, page_size=PAGE_SIZE)
        return Response(
            {
                "results": ProfileSerializer(items, many=True).data,
                "total": total,
                "page": page,
                "page_size": PAGE_SIZE,
            }
        )


class FollowerListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List followers",
        description="Returns followers for a given profile.",
        tags=["Profiles"],
        responses={200: FollowerSerializer(many=True)},
    )
    def get(self, request, username):
        profile = ProfileService.get_by_username(username)
        if not profile:  # pragma: no cover
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        page = int(request.query_params.get("page", 1))
        items, total = ProfileService.get_followers(profile, page=page, page_size=PAGE_SIZE)
        return Response(
            {
                "results": FollowerSerializer(items, many=True).data,
                "total": total,
                "page": page,
                "page_size": PAGE_SIZE,
            }
        )


class FollowingListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List following",
        description="Returns profiles that a given user follows.",
        tags=["Profiles"],
        responses={200: FollowingSerializer(many=True)},
    )
    def get(self, request, username):
        profile = ProfileService.get_by_username(username)
        if not profile:  # pragma: no cover
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        page = int(request.query_params.get("page", 1))
        items, total = ProfileService.get_following(profile, page=page, page_size=PAGE_SIZE)
        return Response(
            {
                "results": FollowingSerializer(items, many=True).data,
                "total": total,
                "page": page,
                "page_size": PAGE_SIZE,
            }
        )


class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Follow user",
        description="Follow a profile. Returns 409 if already following or self-follow.",
        tags=["Profiles"],
        responses={204: OpenApiResponse(description="Followed successfully")},
    )
    def post(self, request, username):
        target = ProfileService.get_by_username(username)
        if not target:  # pragma: no cover
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        result = ProfileService.follow(str(request.user.id), str(target.user_id))
        if result is None:
            return Response({"detail": "Already following or self-follow."}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Unfollow user",
        description="Unfollow a profile.",
        tags=["Profiles"],
        responses={204: OpenApiResponse(description="Unfollowed successfully")},
    )
    def delete(self, request, username):
        target = ProfileService.get_by_username(username)
        if not target:  # pragma: no cover
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        ProfileService.unfollow(str(request.user.id), str(target.user_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class FollowStatusView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Follow status",
        description="Check if the current user is following a given profile.",
        tags=["Profiles"],
        responses={200: OpenApiResponse(description="Follow status")},
    )
    def get(self, request, username):
        uid = _user_id(request)
        target = ProfileService.get_by_username(username)
        if not target:  # pragma: no cover
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        is_following = ProfileService.is_following(uid, str(target.user_id)) if uid else False
        return Response({"is_following": is_following})


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Leaderboard",
        description="Returns leaderboard of profiles ranked by reputation score.",
        tags=["Profiles"],
        parameters=[OpenApiParameter("page", int, description="Page number (1-indexed)")],
        responses={200: OpenApiResponse(description="Paginated leaderboard")},
    )
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        items, total = ProfileService.get_leaderboard(page=page, page_size=50)
        return Response(
            {
                "results": ProfileSerializer(items, many=True).data,
                "total": total,
                "page": page,
                "page_size": 50,
            }
        )


class TopContributorsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Top contributors",
        description="Returns top contributors ranked by reputation.",
        tags=["Profiles"],
        parameters=[OpenApiParameter("limit", int, description="Number of contributors to return (default 10)")],
        responses={200: OpenApiResponse(description="Top contributors")},
    )
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        contributors = ReputationService.get_top_contributors(limit=limit)
        return Response({"results": contributors})


class UsernameCheckView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Check username availability",
        description="Check if a username is available for registration.",
        tags=["Profiles"],
        parameters=[OpenApiParameter("username", str, description="Username to check availability")],
        responses={200: OpenApiResponse(description="Username availability status")},
    )
    def get(self, request):
        username = request.query_params.get("username", "").strip()
        if not username:  # pragma: no cover
            return Response({"detail": "username parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        exists = Profile.objects.filter(username=username).exists()
        return Response({"username": username, "available": not exists})


class ResolveProfilesByIdView(APIView):
    """
    POST /api/profiles/internal/resolve-by-id/

    Internal endpoint. Resolves user IDs to profile data (username, display_name, avatar_url).
    Used by core service to sync denormalized author fields in community discussions/comments.

    Request:
      {"user_ids": ["uuid1", "uuid2"]}

    Response:
      {"profiles": {"uuid1": {"username": "...", "display_name": "...", "avatar_url": "..."}}}

    Security:
      - Requires X-Internal-Request header
    """

    permission_classes = []

    @extend_schema(
        summary="Resolve profiles by ID (internal)",
        description="Internal endpoint. Resolves user IDs to profile data. Requires X-Internal-Request header.",
        tags=["Profiles"],
        responses={200: OpenApiResponse(description="Profile resolution result")},
    )
    def post(self, request):  # pragma: no cover
        internal_header = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")
        if request.headers.get(internal_header) != "1":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list) or not user_ids:
            return Response({"profiles": {}}, status=status.HTTP_200_OK)

        profiles = Profile.objects.filter(
            user_id__in=[uuid.UUID(uid) for uid in user_ids if uid],
        )

        result = {
            str(p.user_id): {
                "username": p.username,
                "display_name": p.display_name,
                "avatar_url": p.avatar_url or p.user.avatar_url or "",
                "user_avatar_url": p.user.avatar_url or "",
            }
            for p in profiles
        }

        return Response({"profiles": result})


class ProfileUploadView(APIView):  # pragma: no cover
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload profile image",
        description="Upload an avatar or banner image for the current user's profile.",
        tags=["Profiles"],
        responses={200: OpenApiResponse(description="Upload successful - returns URL")},
    )
    def post(self, request):
        uid = str(request.user.id)
        field = request.data.get("field")
        file = request.FILES.get("file")

        if not field or field not in ("avatar", "banner"):
            return Response(
                {"detail": "field must be 'avatar' or 'banner'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not file:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.content_type not in ALLOWED_IMAGE_TYPES:
            return Response(
                {"detail": f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_bytes = AVATAR_MAX_BYTES if field == "avatar" else BANNER_MAX_BYTES
        if file.size > max_bytes:
            limit_mb = max_bytes / (1024 * 1024)
            return Response(
                {"detail": f"File too large. Maximum {limit_mb:.0f} MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext_map = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }
        ext = ext_map.get(file.content_type, "jpg")
        stamp = timezone.now().strftime("%Y%m%d%H%M%S")
        unique_id = uuid.uuid4().hex[:8]

        if field == "avatar":
            s3_key = f"avatars/{uid}/{stamp}_{unique_id}.{ext}"
        else:
            s3_key = f"banners/{uid}/{stamp}_{unique_id}.{ext}"

        try:
            saved_path = default_storage.save(s3_key, file)
            url = default_storage.url(saved_path)
            if not url.startswith(("http://", "https://")):
                url = request.build_absolute_uri(url)
            return Response({"url": url, "key": saved_path})
        except Exception as e:
            logger.exception("Failed to upload %s for user %s", field, uid)
            return Response(
                {"detail": f"Upload failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfilesByIdsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get profiles by IDs",
        description="""
        Accepts a list of user UUIDs and returns profile data for all matching users.
        Used by other services (e.g. chat) to resolve user IDs to display names and avatars.
        """,
        tags=["Profiles"],
        request=ProfileSerializer,
        responses={200: ProfileSerializer(many=True)},
    )
    def post(self, request):
        user_ids = request.data.get("user_ids", [])
        if not user_ids:
            return Response({"profiles": []}, status=status.HTTP_200_OK)

        profiles = Profile.objects.filter(user_id__in=user_ids)
        serializer = ProfileSerializer(profiles, many=True)
        return Response({"profiles": serializer.data}, status=status.HTTP_200_OK)
