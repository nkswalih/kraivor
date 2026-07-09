"""
Chat v2 provisioning — auto-creates and syncs Workspace Team Groups.

Triggered by Django signals from the workspaces app:
  - Workspace created       → provision team group room
  - WorkspaceMember created → add user to team group
  - WorkspaceMember deleted → remove user from team group
  - Workspace deleted       → archive team group
"""

import logging
from typing import Any

from django.db import transaction

from apps.chat.dynamodb.repository import ChatV2Repository
from apps.chat.models import Room, RoomMember

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Handles automatic team group lifecycle for workspaces."""

    def __init__(self) -> None:
        self.repo = ChatV2Repository()

    @transaction.atomic
    def provision_team_group(self, *, workspace_id: str, workspace_name: str, owner_id: str) -> Room | None:
        """Create the WORKSPACE_TEAM room for a new workspace. Idempotent."""
        existing = Room.objects.filter(
            workspace_id=workspace_id,
            room_type=Room.RoomType.WORKSPACE_TEAM,
            deleted_at__isnull=True,
        ).first()
        if existing:
            logger.debug("provision.exists", extra={"workspace_id": workspace_id, "room_id": str(existing.id)})
            return None

        room = Room.objects.create(
            name=f"{workspace_name} Team",
            room_type=Room.RoomType.WORKSPACE_TEAM,
            is_public=False,
            workspace_id=workspace_id,
            created_by=owner_id,
        )
        RoomMember.objects.create(room=room, user_id=owner_id)
        self.repo.init_counter(str(room.id))

        logger.info(
            "provision.team_group_created",
            extra={"workspace_id": workspace_id, "room_id": str(room.id)},
        )
        return room

    @transaction.atomic
    def add_to_team_group(self, *, workspace_id: str, user_id: str) -> RoomMember | None:
        """Add a user to the workspace's team group. Idempotent."""
        room = Room.objects.filter(
            workspace_id=workspace_id,
            room_type=Room.RoomType.WORKSPACE_TEAM,
            deleted_at__isnull=True,
        ).first()
        if not room:
            logger.warning("provision.no_team_group", extra={"workspace_id": workspace_id})
            return None

        member, created = RoomMember.objects.get_or_create(
            room=room, user_id=user_id,
            defaults={"last_read_seq": 0},
        )
        if created:
            room.member_count += 1
            room.save(update_fields=["member_count"])
            logger.info(
                "provision.member_added",
                extra={"workspace_id": workspace_id, "room_id": str(room.id), "user_id": user_id},
            )
        return member

    @transaction.atomic
    def remove_from_team_group(self, *, workspace_id: str, user_id: str) -> bool:
        """Remove a user from the workspace's team group (soft delete)."""
        room = Room.objects.filter(
            workspace_id=workspace_id,
            room_type=Room.RoomType.WORKSPACE_TEAM,
            deleted_at__isnull=True,
        ).first()
        if not room:
            return False

        deleted_count = RoomMember.objects.filter(
            room=room, user_id=user_id, deleted_at__isnull=True,
        ).delete()[0]

        if deleted_count:
            room.member_count = max(0, room.member_count - 1)
            room.save(update_fields=["member_count"])
            logger.info(
                "provision.member_removed",
                extra={"workspace_id": workspace_id, "room_id": str(room.id), "user_id": user_id},
            )
        return deleted_count > 0

    @transaction.atomic
    def archive_team_group(self, *, workspace_id: str) -> bool:
        """Soft-delete the team group and all its members when workspace is deleted."""
        room = Room.objects.filter(
            workspace_id=workspace_id,
            room_type=Room.RoomType.WORKSPACE_TEAM,
            deleted_at__isnull=True,
        ).first()
        if not room:
            return False

        room.delete()  # soft delete
        RoomMember.objects.filter(room=room, deleted_at__isnull=True).delete()

        logger.info(
            "provision.team_group_archived",
            extra={"workspace_id": workspace_id, "room_id": str(room.id)},
        )
        return True


_provisioner: ProvisioningService | None = None


def get_provisioner() -> ProvisioningService:
    global _provisioner
    if _provisioner is None:
        _provisioner = ProvisioningService()
    return _provisioner
