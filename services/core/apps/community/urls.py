from django.urls import path

from .views import (
    CommentListView,
    CommentRepliesView,
    CommentVoteView,
    DiscussionDetailView,
    DiscussionListView,
    DiscussionVoteView,
    PopularTagsView,
    SyncAuthorDenormalizationView,
    TagSearchView,
    TrendingDiscussionsView,
    UserCommentsView,
    UserDiscussionsView,
)

discussion_patterns = [
    path("", DiscussionListView.as_view(), name="discussion-list"),
    path(
        "<uuid:discussion_id>/",
        DiscussionDetailView.as_view(),
        name="discussion-detail",
    ),
    path(
        "<uuid:discussion_id>/vote/",
        DiscussionVoteView.as_view(),
        name="discussion-vote",
    ),
    path(
        "<uuid:discussion_id>/comments/",
        CommentListView.as_view(),
        name="discussion-comments",
    ),
    path(
        "<uuid:discussion_id>/comments/<uuid:comment_id>/",
        CommentRepliesView.as_view(),
        name="comment-replies",
    ),
    path(
        "<uuid:discussion_id>/comments/<uuid:comment_id>/vote/",
        CommentVoteView.as_view(),
        name="comment-vote",
    ),
]

tag_patterns = [
    path("trending/", TrendingDiscussionsView.as_view(), name="discussion-trending"),
    path("tags/popular/", PopularTagsView.as_view(), name="tags-popular"),
    path("tags/search/", TagSearchView.as_view(), name="tags-search"),
]

user_content_patterns = [
    path("user/<uuid:user_id>/discussions/", UserDiscussionsView.as_view(), name="user-discussions"),
    path("user/<uuid:user_id>/comments/", UserCommentsView.as_view(), name="user-comments"),
]

internal_patterns = [
    path("internal/sync-author/", SyncAuthorDenormalizationView.as_view(), name="sync-author"),
]

urlpatterns = discussion_patterns + tag_patterns + user_content_patterns + internal_patterns
