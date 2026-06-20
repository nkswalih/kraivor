from django.urls import path

from .views import (
    CommentListView,
    CommentRepliesView,
    CommentVoteView,
    DiscussionDetailView,
    DiscussionListView,
    DiscussionVoteView,
    PopularTagsView,
    TagSearchView,
    TrendingDiscussionsView,
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

urlpatterns = discussion_patterns + tag_patterns
