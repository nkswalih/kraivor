from django.urls import path

from .views import (
    FollowerListView,
    FollowingListView,
    FollowStatusView,
    FollowView,
    LeaderboardView,
    MyProfileView,
    ProfileDetailView,
    ProfilesByIdsView,
    ProfileSearchView,
    ProfileUploadView,
    ResolveProfilesByIdView,
    TopContributorsView,
    UsernameCheckView,
)

urlpatterns = [
    path("me/", MyProfileView.as_view(), name="my-profile"),
    path("search/", ProfileSearchView.as_view(), name="profile-search"),
    path("upload/", ProfileUploadView.as_view(), name="profile-upload"),
    path("check-username/", UsernameCheckView.as_view(), name="username-check"),
    path("leaderboard/", LeaderboardView.as_view(), name="profile-leaderboard"),
    path("top-contributors/", TopContributorsView.as_view(), name="top-contributors"),
    path("by-ids/", ProfilesByIdsView.as_view(), name="profiles-by-ids"),
    path("internal/resolve-by-id/", ResolveProfilesByIdView.as_view(), name="resolve-profiles-by-id"),
    path("<str:username>/", ProfileDetailView.as_view(), name="profile-detail"),
    path("<str:username>/follow/", FollowView.as_view(), name="profile-follow"),
    path("<str:username>/follow/status/", FollowStatusView.as_view(), name="follow-status"),
    path("<str:username>/followers/", FollowerListView.as_view(), name="profile-followers"),
    path("<str:username>/following/", FollowingListView.as_view(), name="profile-following"),
]
