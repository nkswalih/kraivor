from rest_framework.authentication import BaseAuthentication


class TestAuthentication(BaseAuthentication):
    """Read test-only X-User-Id / X-Workspace-Id headers for authentication."""

    def authenticate(self, request):
        user_id = request.headers.get("X-User-Id")
        workspace_id = request.headers.get("X-Workspace-Id")

        if not user_id:
            return None

        request.user_id = user_id
        if workspace_id:
            request.workspace_id = workspace_id

        class TestUser:
            is_authenticated = True
            is_anonymous = False
            is_active = True
            pk = user_id

        return (TestUser(), None)
