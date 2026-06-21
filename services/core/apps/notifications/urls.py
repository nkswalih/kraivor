from django.urls import path

from .views import (
    FCMTokenCreateView,
    FCMTokenDeleteView,
    NotificationDetailView,
    NotificationListView,
    UnreadCountView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread_count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path(
        "notifications/<uuid:pk>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "notifications/<uuid:pk>/read/",
        NotificationDetailView.as_view(),
        name="notification-mark-read",
    ),
    path("fcm-tokens/", FCMTokenCreateView.as_view(), name="fcm-token-create"),
    path("fcm-tokens/<str:pk>/", FCMTokenDeleteView.as_view(), name="fcm-token-delete"),
]
