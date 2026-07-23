"""
Workspace serializers — KRV-019 (workspace CRUD) + KRV-020 (invitations).

Serializer contract:
  - Validate and coerce input
  - Never enforce authorization (that's permissions + service layer)
  - Never call external services (that's the service layer)
  - Output shape is the API contract — change carefully

Invitation serializers added in KRV-020:
  WorkspaceInvitationCreateSerializer  — POST /members/invite/
  WorkspaceInvitationSerializer        — response shape for invitations
  InvitationAcceptSerializer           — POST /invitations/{token}/accept/
"""

from rest_framework import serializers

from ..constants import WorkspaceRole
from ..models import WorkspaceInvitation


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    """
    Read serializer for invitation responses.
    Token is included in admin list views and the creation response.
    The frontend uses it to build the accept URL for copy-paste sharing.
    """

    status = serializers.ReadOnlyField()
    accept_url = serializers.ReadOnlyField()

    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    workspace_slug = serializers.CharField(source="workspace.slug", read_only=True)

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id",
            "workspace_id",
            "workspace_name",
            "workspace_slug",
            "email",
            "role",
            "token",
            "invited_by_id",
            "invited_by_name",
            "status",
            "accept_url",
            "expires_at",
            "accepted_at",
            "email_sent_at",
            "created_at",
        ]
        read_only_fields = fields


class WorkspaceInvitationCreateSerializer(serializers.Serializer):
    """
    POST /workspaces/{id}/members/invite/

    Validates the invite request payload.
    email: target recipient
    role:  role they'll receive (cannot be 'owner')

    We accept invited_by_name from the request context (set by the view from
    the JWT sub claim display name) — not from user input.
    """

    email = serializers.EmailField(
        help_text="Email address of the person being invited."
    )
    role = serializers.ChoiceField(
        choices=[
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
            (WorkspaceRole.VIEWER, "Viewer"),
        ],
        default=WorkspaceRole.MEMBER,
    )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class InvitationAcceptSerializer(serializers.Serializer):
    """
    POST /workspace/invitations/{token}/accept/

    The token comes from the URL path, not the body.
    The user_id comes from the gateway header (request.user_id).
    No body fields required — the token IS the credential.
    """

    # No input fields — token is path param, user is from gateway header
    pass


class InvitationAcceptResponseSerializer(serializers.Serializer):
    """Response shape after successfully accepting an invitation."""

    workspace_id = serializers.UUIDField()
    workspace_name = serializers.CharField()
    workspace_slug = serializers.CharField()
    role = serializers.CharField()
    joined_at = serializers.DateTimeField()
    message = serializers.CharField()
