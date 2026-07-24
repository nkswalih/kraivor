import contextlib

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import CacheService

# ── Chat v2: Workspace Team Group Auto-Provisioning ──────────────────────────


@receiver(post_save, sender="workspaces.Workspace")
def provision_team_group(sender, instance, created, **kwargs):
    """Auto-provision a WORKSPACE_TEAM room when a workspace is created."""
    if not created:
        # Check if this is an archive (soft delete)
        if instance.deleted_at:
            from apps.chat.services.provisioning import get_provisioner

            get_provisioner().archive_team_group(workspace_id=str(instance.id))
        return

    from apps.chat.services.provisioning import get_provisioner

    get_provisioner().provision_team_group(
        workspace_id=str(instance.id),
        workspace_name=instance.name,
        owner_id=str(instance.owner_id),
    )


@receiver(post_save, sender="workspaces.WorkspaceMember")
def add_to_team_group(sender, instance, created, **kwargs):
    """Add a user to the workspace team group when they join the workspace."""
    if not created:
        return
    if instance.deleted_at:
        return

    from apps.chat.services.provisioning import get_provisioner

    get_provisioner().add_to_team_group(
        workspace_id=str(instance.workspace_id), user_id=str(instance.user_id)
    )


@receiver(post_delete, sender="workspaces.WorkspaceMember")
def remove_from_team_group(sender, instance, **kwargs):
    """Remove a user from the workspace team group when they leave."""
    from apps.chat.services.provisioning import get_provisioner

    get_provisioner().remove_from_team_group(
        workspace_id=str(instance.workspace_id), user_id=str(instance.user_id)
    )


# ── Cache Invalidation ───────────────────────────────────────────────────────


@receiver(post_save, sender="workspaces.WorkspaceMember")
@receiver(post_delete, sender="workspaces.WorkspaceMember")
def invalidate_workspace_member_count(sender, instance, **kwargs):
    CacheService.delete(f"ws:member_count:{instance.workspace_id}")


@receiver(post_save, sender="projects.Task")
@receiver(post_delete, sender="projects.Task")
def invalidate_project_task_count(sender, instance, **kwargs):
    if instance.project_id:
        CacheService.delete(f"proj:task_count:{instance.project_id}")


@receiver(post_save, sender="knowledge.KnowledgeAsset")
@receiver(post_delete, sender="knowledge.KnowledgeAsset")
def invalidate_knowledge_asset_count(sender, instance, **kwargs):
    if instance.knowledge_space_id:
        CacheService.delete(f"ks:asset_count:{instance.knowledge_space_id}")


@receiver(post_save, sender="repositories.Repository")
@receiver(post_delete, sender="repositories.Repository")
def invalidate_repository_count(sender, instance, **kwargs):
    if instance.workspace_id:
        CacheService.delete(f"repo:count:{instance.workspace_id}")


# ── Knowledge Auto-Indexing ──────────────────────────────────────────────────


@receiver(post_save, sender="knowledge.KnowledgeSpace")
def index_knowledge_space_on_save(sender, instance, created, **kwargs):
    """Auto-index KnowledgeSpace canvas content into the AI knowledge base.

    Fires asynchronously via a background thread to avoid blocking the save.
    Only indexes when canvas_data has elements.
    """
    canvas_data = instance.canvas_data
    if not canvas_data or not canvas_data.get("elements"):
        return

    import threading

    def _send_to_ai():
        import httpx
        import os

        ai_url = os.environ.get("AI_SERVICE_URL", "http://ai:8004")
        with contextlib.suppress(Exception):
            httpx.post(
                f"{ai_url}/v1/knowledge/index-canvas",
                json={
                    "workspace_id": str(instance.workspace_id),
                    "knowledge_space_id": str(instance.id),
                    "canvas_data": canvas_data,
                    "knowledge_space_name": instance.name,
                },
                headers={
                    "X-Internal-Request": settings.INTERNAL_REQUEST_SECRET,
                    "X-User-ID": str(instance.created_by_id or ""),
                    "X-Workspace-IDs": str(instance.workspace_id),
                },
                timeout=30.0,
            )

    thread = threading.Thread(target=_send_to_ai, daemon=True)
    thread.start()
