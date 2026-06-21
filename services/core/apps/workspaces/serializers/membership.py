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
from ..models import WorkspaceMember


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """
    Full member representation.
    user_id is a UUID ref to identity.users — frontend resolves display names
    via a separate identity service call (or the JWT payload for the current user).
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceMember
        fields = [
            "id",
            "user_id",
            "role",
            "status",
            "joined_at",
            "invited_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status(self, obj: WorkspaceMember) -> str:
        return "active" if not obj.is_deleted else "removed"


class MemberRoleUpdateSerializer(serializers.Serializer):
    """
    Used for PATCH /workspaces/{id}/members/{user_id}/ to change a member's role.
    Cannot set role to 'owner' — ownership transfer is a separate flow.
    """

    role = serializers.ChoiceField(
        choices=[
            (WorkspaceRole.OWNER, "Owner"),
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
            (WorkspaceRole.VIEWER, "Viewer"),
        ]
    )

    def validate_role(self, value: str) -> str:
        if value == WorkspaceRole.OWNER:
            raise serializers.ValidationError("Ownership transfer is a separate flow.")
        return value
