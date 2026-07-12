from typing import TYPE_CHECKING

import uuid
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from core.pagination import StandardPagination

if TYPE_CHECKING:
    from apps.notifications.models import Notification

from ..selectors.notifications import NotificationSelector
from ..serializers import NotificationSerializer


@extend_schema(tags=["Notifications"])
class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        responses={200: OpenApiResponse(description="Unread count")},
    )
    def get(self, request: Request) -> Response:
        count = NotificationSelector.get_unread_count(request.user_id)
        return Response({"unread_count": count})


@extend_schema(tags=["Notifications"])
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List notifications", responses={200: NotificationSerializer(many=True)}
    )
    def get(self, request: Request) -> Response:
        user_id = request.user_id
        notifications = NotificationSelector.list_user_notifications(user_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Mark all notifications as read",
        responses={200: OpenApiResponse(description="All notifications marked read")},
    )
    def post(self, request: Request) -> Response:
        count = NotificationSelector.mark_all_read(request.user_id)
        return Response({"marked_read": count}, status=status.HTTP_200_OK)


@extend_schema(tags=["Notifications"])
class NotificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_notification_or_404(self, pk: str, user_id: str) -> "Notification":
        try:
            notif_id = uuid.UUID(str(pk))
        except (ValueError, AttributeError):
            raise NotFound("Notification not found.") from None
        notification = NotificationSelector.get_notification(notif_id, user_id)
        if not notification:
            raise NotFound("Notification not found.")
        return notification

    @extend_schema(summary="Get notification", responses={200: NotificationSerializer})
    def get(self, request: Request, pk: str | None = None) -> Response:
        notification = self._get_notification_or_404(pk, request.user_id)
        return Response(NotificationSerializer(notification).data)

    @extend_schema(
        summary="Mark notification as read", responses={200: NotificationSerializer}
    )
    def patch(self, request: Request, pk: str | None = None) -> Response:
        notification = self._get_notification_or_404(pk, request.user_id)
        NotificationSelector.mark_read(notification)
        return Response(NotificationSerializer(notification).data)

    @extend_schema(
        summary="Dismiss notification",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, pk: str | None = None) -> Response:
        notification = self._get_notification_or_404(pk, request.user_id)
        NotificationSelector.dismiss(notification)
        return Response(status=status.HTTP_204_NO_CONTENT)
