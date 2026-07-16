import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceClient:
    def __init__(self, core_url: str, analysis_url: str):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.core_url = core_url
        self.analysis_url = analysis_url

    async def _get(self, url: str, user_id: str, workspace_id: str) -> list | dict:
        try:
            resp = await self.client.get(
                url,
                headers={
                    "X-Internal-Request": settings.internal_request_secret,
                    "X-User-ID": user_id,
                    "X-Workspace-IDs": workspace_id,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "HTTP %s from %s: %s", e.response.status_code, url, e.response.text
            )
            return []
        except httpx.RequestError as e:
            logger.warning("Request failed for %s: %s", url, e)
            return []

    async def get_repos(self, user_id: str, workspace_id: str) -> list[dict]:
        data = await self._get(
            f"{self.core_url}/workspaces/{workspace_id}/repos/", user_id, workspace_id
        )
        if isinstance(data, dict):
            data = data.get("results", data.get("repos", []))
        return data if isinstance(data, list) else []

    async def get_projects(self, user_id: str, workspace_id: str) -> list[dict]:
        data = await self._get(
            f"{self.core_url}/workspaces/{workspace_id}/projects/",
            user_id,
            workspace_id,
        )
        if isinstance(data, dict):
            data = data.get("results", data.get("projects", []))
        return data if isinstance(data, list) else []

    async def get_tasks(
        self, user_id: str, workspace_id: str, project_id: str | None = None
    ) -> list[dict]:
        path = f"{self.core_url}/workspaces/{workspace_id}/tasks/"
        if project_id:
            path += f"?project_id={project_id}"
        data = await self._get(path, user_id, workspace_id)
        if isinstance(data, dict):
            data = data.get("results", data.get("tasks", []))
        return data if isinstance(data, list) else []

    async def get_knowledge_spaces(self, user_id: str, workspace_id: str) -> list[dict]:
        data = await self._get(
            f"{self.core_url}/workspaces/{workspace_id}/knowledge/",
            user_id,
            workspace_id,
        )
        if isinstance(data, dict):
            data = data.get("results", data.get("knowledge_spaces", []))
        return data if isinstance(data, list) else []

    async def get_notifications(self, user_id: str, workspace_id: str) -> list[dict]:
        data = await self._get(f"{self.core_url}/notifications/", user_id, workspace_id)
        if isinstance(data, dict):
            data = data.get("results", data.get("notifications", []))
        return data if isinstance(data, list) else []

    async def get_discussions(self, user_id: str, workspace_id: str) -> list[dict]:
        data = await self._get(f"{self.core_url}/community/", user_id, workspace_id)
        if isinstance(data, dict):
            data = data.get("results", data.get("discussions", []))
        return data if isinstance(data, list) else []

    async def get_discussion_comments(
        self, user_id: str, workspace_id: str, discussion_id: str
    ) -> list[dict]:
        data = await self._get(
            f"{self.core_url}/community/{discussion_id}/comments/",
            user_id,
            workspace_id,
        )
        if isinstance(data, dict):
            data = data.get("results", data.get("comments", []))
        return data if isinstance(data, list) else []

    async def get_analysis_report(
        self, user_id: str, workspace_id: str, repo_id: str
    ) -> dict | None:
        jobs = await self._get(
            f"{self.analysis_url}/jobs?workspace_id={workspace_id}&repo_id={repo_id}",
            user_id,
            workspace_id,
        )
        if isinstance(jobs, dict):
            jobs = jobs.get("results", jobs.get("jobs", []))
        if not jobs or not isinstance(jobs, list):
            return None
        latest = max(jobs, key=lambda j: j.get("created_at", ""))
        report = await self._get(
            f"{self.analysis_url}/reports/by-job/{latest['job_id']}",
            user_id,
            workspace_id,
        )
        return report if isinstance(report, dict) else None

    async def close(self):
        await self.client.aclose()
