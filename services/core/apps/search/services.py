import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.db.models import Q, Model
from django.db.models import Value as V
from django.db.models.functions import Length

from apps.knowledge.models import KnowledgeAsset, KnowledgeSpace
from apps.notifications.models import Notification
from apps.projects.models import Project, Task
from apps.repositories.models import Repository
from apps.workspaces.models import Workspace

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _workspace_slug(workspace_id: str) -> str:
    try:
        return Workspace.objects.values_list("slug", flat=True).get(id=workspace_id)
    except Workspace.DoesNotExist:
        return workspace_id


def _slug_for(workspace_id: str) -> str:
    return _workspace_slug(str(workspace_id))


@dataclass
class SearchResult:
    id: str
    type: str
    title: str
    description: str
    url: str
    workspace_id: str | None
    relevance: float
    highlights: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    created_at: str | None = None


def highlight_text(text: str, query: str) -> str:
    if not text or not query:
        return text or ""
    lower_text = text.lower()
    lower_query = query.lower()
    idx = lower_text.find(lower_query)
    if idx == -1:
        return text[:200]
    start = max(0, idx - 40)
    end = min(len(text), idx + len(query) + 40)
    fragment = text[start:end]
    if start > 0:
        fragment = "..." + fragment
    if end < len(text):
        fragment = fragment + "..."
    return fragment


def compute_relevance(text: str, query: str, type_score: float = 1.0) -> float:
    if not text or not query:
        return 0.0
    lower_text = text.lower()
    lower_query = query.lower()
    score = 0.0
    if lower_text.startswith(lower_query):
        score = 1.0
    elif lower_query in lower_text:
        score = 0.7
    else:
        isimilar = 0
        for ch in lower_query:
            if ch in lower_text:
                isimilar += 1
        score = (isimilar / max(len(lower_query), 1)) * 0.4
    return score * type_score


def _build_url(workspace_id: str, *segments: str) -> str:
    return "/" + "/".join((_slug_for(workspace_id), *segments))


def search_projects(query: str, workspace_id: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    qs = Project.objects.filter(
        workspace_id=workspace_id,
    ).filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).order_by("-created_at")[:limit]

    results = []
    for obj in qs:
        title_hl = highlight_text(obj.name, query)
        desc_hl = highlight_text(obj.description or "", query)
        score = max(
            compute_relevance(obj.name, query, 0.95),
            compute_relevance(obj.description or "", query, 0.85),
        )
        results.append(SearchResult(
            id=str(obj.id),
            type="project",
            title=obj.name,
            description=obj.description or "",
            url=_build_url(workspace_id, "projects", str(obj.id)),
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl], "description": [desc_hl] if obj.description else []},
            metadata={"status": obj.status},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))
    return results


def search_tasks(query: str, workspace_id: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    qs = Task.objects.filter(
        project__workspace_id=workspace_id,
    ).filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    ).select_related("project").order_by("-created_at")[:limit]

    results = []
    for obj in qs:
        title_hl = highlight_text(obj.title, query)
        desc_hl = highlight_text(obj.description or "", query)
        score = max(
            compute_relevance(obj.title, query, 0.95),
            compute_relevance(obj.description or "", query, 0.85),
        )
        results.append(SearchResult(
            id=str(obj.id),
            type="task",
            title=obj.title,
            description=obj.description or "",
            url=f"{_build_url(workspace_id, 'projects', str(obj.project_id))}?task={obj.id}",
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl], "description": [desc_hl] if obj.description else []},
            metadata={"status": obj.status, "priority": obj.priority},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))
    return results


def search_knowledge(query: str, workspace_id: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    qs = KnowledgeSpace.objects.filter(
        workspace_id=workspace_id,
    ).filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).order_by("-created_at")[:limit]

    results = []
    for obj in qs:
        title_hl = highlight_text(obj.name, query)
        desc_hl = highlight_text(obj.description or "", query)
        score = max(
            compute_relevance(obj.name, query, 0.95),
            compute_relevance(obj.description or "", query, 0.85),
        )
        results.append(SearchResult(
            id=str(obj.id),
            type="knowledge",
            title=obj.name,
            description=obj.description or "",
            url=_build_url(workspace_id, "knowledge", str(obj.id)),
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl], "description": [desc_hl] if obj.description else []},
            metadata={},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))

    asset_qs = KnowledgeAsset.objects.filter(
        knowledge_space__workspace_id=workspace_id,
    ).filter(
        Q(file_name__icontains=query)
    ).select_related("knowledge_space").order_by("-created_at")[:limit]

    for obj in asset_qs:
        title_hl = highlight_text(obj.file_name, query)
        score = compute_relevance(obj.file_name, query, 0.8)
        results.append(SearchResult(
            id=str(obj.id),
            type="knowledge_asset",
            title=obj.file_name,
            description=f"Asset in {obj.knowledge_space.name}",
            url=_build_url(workspace_id, "knowledge", str(obj.knowledge_space_id)),
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl]},
            metadata={"file_type": obj.file_type, "mime_type": obj.mime_type},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))

    return results


def search_repositories(query: str, workspace_id: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    qs = Repository.objects.filter(
        workspace_id=workspace_id,
    ).filter(
        Q(github_repo__icontains=query) | Q(description__icontains=query)
    ).order_by("-created_at")[:limit]

    results = []
    for obj in qs:
        title_hl = highlight_text(obj.github_repo, query)
        desc_hl = highlight_text(obj.description or "", query)
        score = max(
            compute_relevance(obj.github_repo, query, 0.95),
            compute_relevance(obj.description or "", query, 0.85),
        )
        results.append(SearchResult(
            id=str(obj.id),
            type="repository",
            title=obj.github_repo,
            description=obj.description or "",
            url=_build_url(workspace_id, "repositories", str(obj.id)),
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl], "description": [desc_hl] if obj.description else []},
            metadata={"language": obj.language, "is_private": obj.is_private},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))
    return results


def search_notifications(query: str, workspace_id: str, user_id: str | None, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2 or not user_id:
        return []
    qs = Notification.objects.filter(
        workspace_id=workspace_id,
        user_id=user_id,
    ).filter(
        Q(title__icontains=query) | Q(body__icontains=query)
    ).order_by("-created_at")[:limit]

    results = []
    for obj in qs:
        title_hl = highlight_text(obj.title, query)
        body_hl = highlight_text(obj.body or "", query)
        score = max(
            compute_relevance(obj.title, query, 0.95),
            compute_relevance(obj.body or "", query, 0.85),
        )
        results.append(SearchResult(
            id=str(obj.id),
            type="notification",
            title=obj.title,
            description=obj.body or "",
            url=obj.link or "",
            workspace_id=str(workspace_id),
            relevance=score,
            highlights={"title": [title_hl], "description": [body_hl] if obj.body else []},
            metadata={"notification_type": obj.notification_type, "read": obj.read_at is not None},
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        ))
    return results


def search_profiles(query: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    identity_base = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8002/api")
    try:
        resp = requests.get(
            f"{identity_base}/profiles/search/",
            params={"q": query, "page_size": limit},
            timeout=2.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = []
        for item in data.get("results", []):
            display = item.get("display_name") or item.get("username", "")
            score = compute_relevance(display, query, 0.9)
            results.append(SearchResult(
                id=item.get("id", ""),
                type="profile",
                title=display,
                description=item.get("bio", ""),
                url=f"/profiles/{item.get('username', '')}",
                workspace_id=None,
                relevance=score,
                highlights={
                    "title": [highlight_text(display, query) or display],
                },
                metadata={
                    "username": item.get("username", ""),
                    "avatar_url": item.get("avatar_url", ""),
                },
            ))
        return results
    except requests.RequestException as exc:
        logger.warning("profile_search_failed", extra={"error": str(exc)})
        return []


def search_chat(query: str, workspace_id: str, limit: int = 10) -> list[SearchResult]:
    if len(query) < 2:
        return []
    from apps.chat.dynamodb import ChatMessageRepository as DynamoDBRepository
    try:
        repo = DynamoDBRepository()
        rooms = repo.search_messages(query, limit=limit)
        results = []
        for room_id, messages in rooms.items():
            for msg in messages:
                content = msg.get("content", "")
                score = compute_relevance(content, query, 0.8)
                results.append(SearchResult(
                    id=msg.get("message_id", ""),
                    type="chat",
                    title=msg.get("sender_name", "Unknown"),
                    description=content,
                    url=_build_url(workspace_id, "chat", room_id),
                    workspace_id=str(workspace_id),
                    relevance=score,
                    highlights={
                        "description": [highlight_text(content, query) or content[:200]],
                    },
                    metadata={"sender_name": msg.get("sender_name", ""), "room_id": room_id},
                    created_at=msg.get("created_at"),
                ))
        return results
    except Exception as exc:
        logger.warning("chat_search_failed", extra={"error": str(exc)})
        return []


class SearchService:
    SOURCE_WEIGHTS = {
        "project": 1.0,
        "task": 0.95,
        "knowledge": 0.9,
        "knowledge_asset": 0.8,
        "repository": 0.85,
        "notification": 0.7,
        "chat": 0.75,
        "profile": 0.85,
    }

    def search(
        self,
        query: str,
        workspace_id: str,
        user_id: str | None = None,
        scope: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        query = query.strip()
        if len(query) < 2:
            return {"query": query, "total_results": 0, "page": page, "page_size": page_size, "results": [], "facets": {}}

        source_limit = page_size * 2
        tasks = {}

        with ThreadPoolExecutor(max_workers=6) as executor:
            if scope in ("all", "projects"):
                tasks["project"] = executor.submit(search_projects, query, workspace_id, source_limit)
            if scope in ("all", "tasks"):
                tasks["task"] = executor.submit(search_tasks, query, workspace_id, source_limit)
            if scope in ("all", "knowledge"):
                tasks["knowledge"] = executor.submit(search_knowledge, query, workspace_id, source_limit)
            if scope in ("all", "repos"):
                tasks["repository"] = executor.submit(search_repositories, query, workspace_id, source_limit)
            if scope in ("all", "notifications"):
                tasks["notification"] = executor.submit(search_notifications, query, workspace_id, user_id, source_limit)
            if scope in ("all", "chats"):
                tasks["chat"] = executor.submit(search_chat, query, workspace_id, source_limit)
            if scope in ("all", "profiles"):
                tasks["profile"] = executor.submit(search_profiles, query, source_limit)

            all_results: list[SearchResult] = []
            for future in as_completed(tasks.values()):
                try:
                    all_results.extend(future.result())
                except Exception as exc:
                    logger.error("search_source_failed", extra={"error": str(exc)})

        all_results.sort(key=lambda r: r.relevance, reverse=True)

        total = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = all_results[start:end]

        facets: dict[str, int] = {}
        for r in all_results:
            facets[r.type] = facets.get(r.type, 0) + 1

        serialized = []
        for r in page_results:
            serialized.append(self._serialize_result(r))

        return {
            "query": query,
            "total_results": total,
            "page": page,
            "page_size": page_size,
            "results": serialized,
            "facets": facets,
        }

    def _serialize_result(self, r: SearchResult) -> dict:
        return {
            "id": r.id,
            "type": r.type,
            "title": r.title,
            "description": r.description,
            "url": r.url,
            "workspace_id": r.workspace_id,
            "relevance": r.relevance,
            "highlights": r.highlights,
            "metadata": r.metadata,
            "created_at": r.created_at,
        }
