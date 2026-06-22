"""
Workspace event publisher — KRV-019 + KRV-020.

Publishes domain events to Kafka topic: workspace.events
Event schema follows platform standard (system design §14).

Events added in KRV-020:
  workspace.member.invited      — invitation created
  workspace.member.joined       — invitation accepted → member created
  workspace.member.role_changed — role updated
  workspace.member.removed      — member removed

Publishing contract:
  - Fire-and-forget: failed publish NEVER rolls back the DB transaction
  - Events are durable (Kafka) — consumers can replay on restart
  - In dev (no Kafka), events are logged to stdout for visibility
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Workspace, WorkspaceInvitation, WorkspaceMember

logger = logging.getLogger(__name__)

TOPIC_WORKSPACE = "workspace.events"
KAFKA_FLUSH_TIMEOUT_SECONDS = 2.0


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _envelope(
    event_type: str, workspace_id: uuid.UUID, actor_id: uuid.UUID, data: dict
) -> dict:
    """
    Standard platform event envelope (system design §14).
    All events have the same outer shape — consumers can route on event_type
    without parsing the inner data payload.
    """
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source_service": "core",
        "workspace_id": str(workspace_id),
        "user_id": str(actor_id),
        "timestamp": _now_iso(),
        "version": "1.0",
        "data": data,
    }


class WorkspaceEventPublisher:
    """
    Stateless event publisher. Instantiate per-request.

    Kafka producer is fetched from the shared connection pool.
    In environments without Kafka (local dev without full docker-compose),
    falls back to structured logging so events are still visible.
    """

    def __init__(self):
        self._producer = self._get_producer()

    # ── Infrastructure ────────────────────────────────────────────────────────

    def _get_producer(self):
        try:
            from core.infrastructure.kafka import get_producer

            return get_producer()
        except (ImportError, Exception) as exc:
            logger.warning("kafka.producer.unavailable", extra={"reason": str(exc)})
            return None

    def _publish(self, topic: str, event: dict) -> None:
        event_type = event.get("event_type", "unknown")
        workspace_id = event.get("workspace_id", "unknown")

        if self._producer is None:
            # Dev fallback — log the full event so developers can see it
            logger.info(
                "event.published.dev_fallback",
                extra={"topic": topic, "event_type": event_type, "payload": event},
            )
            return

        try:
            self._producer.produce(
                topic=topic,
                key=workspace_id.encode("utf-8"),
                value=json.dumps(event, default=str).encode("utf-8"),
            )
            # Short flush timeout — don't block request on Kafka latency.
            # Unflushed messages sit in the local producer buffer; Kafka
            # guarantees they'll be delivered on the next flush or process exit.
            self._producer.flush(timeout=KAFKA_FLUSH_TIMEOUT_SECONDS)

            logger.debug(
                "event.published",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                },
            )
        except Exception as exc:
            # IMPORTANT: log and continue — never let event failure crash a request
            logger.error(
                "event.publish.failed",
                extra={
                    "topic": topic,
                    "event_type": event_type,
                    "workspace_id": workspace_id,
                    "error": str(exc),
                },
            )

    # ── Workspace lifecycle events (KRV-019) ──────────────────────────────────

    def workspace_created(self, *, workspace: "Workspace", actor_id: uuid.UUID) -> None:
        """Consumed by: Notifications (welcome email), Analytics."""
        event = _envelope(
            event_type="workspace.created",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
                "plan": workspace.plan,
                "owner_id": str(workspace.owner_id),
            },
        )
        self._publish(TOPIC_WORKSPACE, event)

    def workspace_deleted(self, *, workspace: "Workspace", actor_id: uuid.UUID) -> None:
        """Consumed by: Analysis (cancel jobs), AI (remove embeddings)."""
        event = _envelope(
            event_type="workspace.deleted",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={"workspace_id": str(workspace.id), "slug": workspace.slug},
        )
        self._publish(TOPIC_WORKSPACE, event)

    # ── Member events (KRV-020) ───────────────────────────────────────────────

    def member_invited(
        self,
        *,
        workspace: "Workspace",
        invitation: "WorkspaceInvitation",
        actor_id: uuid.UUID,
    ) -> None:
        """
        Published when an invitation is created.
        Consumed by: Notifications (invitation email via Celery task),
                     Realtime (admin dashboard update).
        """
        event = _envelope(
            event_type="workspace.member.invited",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "invitation_id": str(invitation.id),
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "email": invitation.email,
                "role": invitation.role,
                "invited_by_id": str(invitation.invited_by_id),
                "invited_by_name": invitation.invited_by_name,
                "expires_at": invitation.expires_at.isoformat(),
                "accept_url": invitation.accept_url,
            },
        )
        self._publish(TOPIC_WORKSPACE, event)

    def member_joined(
        self, *, workspace: "Workspace", member: "WorkspaceMember", actor_id: uuid.UUID
    ) -> None:
        """
        Published when an invitation is accepted and the member is created.
        Consumed by: Notifications (welcome to workspace),
                     Realtime (member list update for current workspace members),
                     Analytics.
        """
        event = _envelope(
            event_type="workspace.member.joined",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "user_id": str(member.user_id),
                "role": member.role,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            },
        )
        self._publish(TOPIC_WORKSPACE, event)

    def member_role_changed(
        self,
        *,
        workspace: "Workspace",
        member: "WorkspaceMember",
        old_role: str,
        new_role: str,
        actor_id: uuid.UUID,
    ) -> None:
        """
        Published when a member's role is changed.
        Consumed by: Notifications (role change email),
                     Realtime (member list update),
                     Audit log.
        """
        event = _envelope(
            event_type="workspace.member.role_changed",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "user_id": str(member.user_id),
                "old_role": old_role,
                "new_role": new_role,
                "changed_by": str(actor_id),
            },
        )
        self._publish(TOPIC_WORKSPACE, event)

    def member_removed(
        self,
        *,
        workspace: "Workspace",
        user_id: uuid.UUID,
        actor_id: uuid.UUID,
        reason: str = "removed_by_admin",
    ) -> None:
        """
        Published when a member is removed or leaves.
        reason: 'removed_by_admin' | 'left' | 'workspace_deleted'
        Consumed by: Notifications, Audit log, Realtime.
        """
        event = _envelope(
            event_type="workspace.member.removed",
            workspace_id=workspace.id,
            actor_id=actor_id,
            data={
                "workspace_id": str(workspace.id),
                "user_id": str(user_id),
                "removed_by": str(actor_id),
                "reason": reason,
            },
        )
        self._publish(TOPIC_WORKSPACE, event)

    # ── Backward compat alias (used in KRV-019 service) ──────────────────────

    def member_added(
        self, *, workspace: "Workspace", member: "WorkspaceMember", actor_id: uuid.UUID
    ) -> None:
        """Alias used by WorkspaceService.add_member() from KRV-019."""
        self.member_joined(workspace=workspace, member=member, actor_id=actor_id)
