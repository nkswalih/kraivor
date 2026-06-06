from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import FCMTokenViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"fcm-tokens", FCMTokenViewSet, basename="fcm-token")

urlpatterns = [
    path("", include(router.urls)),
]
