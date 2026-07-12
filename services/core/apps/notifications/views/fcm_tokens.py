from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated

from ..selectors.notifications import NotificationSelector
from ..serializers import FCMTokenSerializer


@extend_schema(tags=["FCM Tokens"])
class FCMTokenCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Register FCM token",
        request=FCMTokenSerializer,
        responses={201: FCMTokenSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, created = NotificationSelector.register_fcm_token(
            user_id=request.user_id,
            token=serializer.validated_data["token"],
            platform=serializer.validated_data.get("platform", "web"),
        )
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(FCMTokenSerializer(token).data, status=status_code)


@extend_schema(tags=["FCM Tokens"])
class FCMTokenDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Remove FCM token", responses={204: None})
    def delete(self, request: Request, pk: str | None = None) -> Response:
        deleted = NotificationSelector.delete_fcm_token(request.user_id, pk)
        if not deleted:
            return Response(
                {"detail": "Token not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
