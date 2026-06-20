"""
REST API views for notification management.
"""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from apps.notifications.models import FCMToken, Notification
from apps.notifications.serializers import FCMTokenSerializer, NotificationSerializer
from apps.workspaces.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List notifications",
        tags=["Notifications"],
        responses={200: NotificationSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get notification",
        tags=["Notifications"],
        responses={200: NotificationSerializer},
    ),
    mark_all_read=extend_schema(
        summary="Mark all notifications as read",
        tags=["Notifications"],
        responses={200: OpenApiResponse(description="Mark all as read status")},
    ),
    mark_read=extend_schema(
        summary="Mark notification as read",
        tags=["Notifications"],
        responses={200: OpenApiResponse(description="Mark as read status")},
    ),
    dismiss=extend_schema(
        summary="Dismiss notification",
        tags=["Notifications"],
        responses={200: OpenApiResponse(description="Dismiss status")},
    ),
    unread_count=extend_schema(
        summary="Get unread notification count",
        tags=["Notifications"],
        responses={200: OpenApiResponse(description="Unread count")},
    ),
)
class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user_id=self.request.user_id).order_by(
            "-created_at"
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            user_id=request.user_id, read_at__isnull=True
        ).update(read_at=timezone.now())
        logger.info(
            "notifications.mark_all_read",
            extra={"user_id": request.user_id, "count": updated},
        )
        return Response({"status": "ok", "marked_read": updated})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        try:
            notif = Notification.objects.get(id=pk, user_id=request.user_id)
            notif.read_at = timezone.now()
            notif.save(update_fields=["read_at"])
            return Response({"status": "ok"})
        except Notification.DoesNotExist:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        deleted, _ = Notification.objects.filter(
            id=pk, user_id=request.user_id
        ).delete()
        if deleted:
            return Response({"status": "deleted"})
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(
            user_id=request.user_id, read_at__isnull=True
        ).count()
        return Response({"unread_count": count})


@extend_schema_view(
    create=extend_schema(
        summary="Register FCM token",
        tags=["Notifications"],
        request=FCMTokenSerializer,
        responses={201: OpenApiResponse(description="Token registered")},
    ),
    destroy=extend_schema(
        summary="Remove FCM token",
        tags=["Notifications"],
        responses={200: OpenApiResponse(description="Token removed")},
    ),
)
class FCMTokenViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        FCMToken.objects.update_or_create(
            user_id=request.user_id,
            token=serializer.validated_data["token"],
            defaults={"platform": serializer.validated_data["platform"]},
        )
        logger.info("fcm_token.registered", extra={"user_id": request.user_id})
        return Response({"status": "registered"}, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        deleted, _ = FCMToken.objects.filter(user_id=request.user_id, token=pk).delete()
        if deleted:
            return Response({"status": "removed"})
        return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)

