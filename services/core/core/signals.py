from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core.cache import CacheService


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
