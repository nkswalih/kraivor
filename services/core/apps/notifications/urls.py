"""
URL configuration for the notifications API endpoints.

Registers DRF routers:
- notifications/ — NotificationViewSet (list, retrieve, mark_read, dismiss)
- fcm-tokens/  — FCMTokenViewSet (register, unregister device tokens)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import FCMTokenViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"fcm-tokens", FCMTokenViewSet, basename="fcm-token")

urlpatterns = [path("", include(router.urls))]
