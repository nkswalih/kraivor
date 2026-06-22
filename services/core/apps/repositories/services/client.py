import logging
import uuid

import requests
from django.conf import settings

from .exceptions import GitHubAPIError, GitHubAuthError

logger = logging.getLogger(__name__)


class GitHubTokenClient:
    def get_token(self, user_id: uuid.UUID) -> str:
        auth_service_url = getattr(
            settings, "GITHUB_TOKEN_SERVICE_URL", "http://identity:8001"
        )
        endpoint = f"{auth_service_url}/api/oauth/github/token/"
        try:
            response = requests.get(
                endpoint,
                headers={
                    settings.INTERNAL_REQUEST_HEADER: "1",
                    "X-User-ID": str(user_id),
                },
                timeout=5,
            )
        except requests.exceptions.RequestException as exc:
            raise GitHubAuthError(
                "Unable to reach the authentication service. Please try again later."
            ) from exc
        if response.status_code == 404:
            raise GitHubAuthError(
                "No GitHub account connected. "
                "Please connect your GitHub account in workspace settings."
            )
        if response.status_code != 200:
            raise GitHubAuthError(
                "Failed to retrieve GitHub credentials. Please reconnect your GitHub account."
            )
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            raise GitHubAuthError(
                "No GitHub access token found. Please reconnect your GitHub account."
            )
        return token


class GitHubAPIClient:
    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_repository(self, github_repo: str) -> dict:
        url = f"{self.GITHUB_API_BASE}/repos/{github_repo}"
        try:
            response = requests.get(url, headers=self._headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise GitHubAPIError(
                "Unable to reach GitHub. Please try again later."
            ) from exc
        if response.status_code == 404:
            raise GitHubAPIError(
                f"Repository '{github_repo}' was not found on GitHub or "
                "your account does not have access to it."
            )
        if response.status_code == 403:
            raise GitHubAPIError(
                "GitHub access denied. Your token may be missing the 'repo' scope. "
                "Please reconnect your GitHub account with the required permissions."
            )
        if response.status_code == 401:
            raise GitHubAuthError(
                "Your GitHub token is invalid or has expired. Please reconnect your GitHub account."
            )
        if response.status_code != 200:
            raise GitHubAPIError(
                f"GitHub returned an unexpected error (HTTP {response.status_code}). "
                "Please try again later."
            )
        return response.json()

    def list_user_repos(self, *, search: str = "", per_page: int = 30) -> list[dict]:
        if search.strip():
            url = f"{self.GITHUB_API_BASE}/search/repositories"
            params = {
                "q": f"{search.strip()} user:@me fork:true",
                "sort": "updated",
                "per_page": min(per_page, 20),
            }
        else:
            url = f"{self.GITHUB_API_BASE}/user/repos"
            params = {
                "affiliation": "owner,collaborator",
                "sort": "updated",
                "per_page": per_page,
                "visibility": "all",
            }
        try:
            response = requests.get(
                url, headers=self._headers, params=params, timeout=10
            )
        except requests.exceptions.RequestException as exc:
            raise GitHubAPIError(
                "Unable to reach GitHub. Please try again later."
            ) from exc
        if response.status_code == 401:
            raise GitHubAuthError(
                "Your GitHub token is invalid or has expired. Please reconnect your GitHub account."
            )
        if response.status_code != 200:
            raise GitHubAPIError(
                f"GitHub returned HTTP {response.status_code}. Please try again."
            )
        raw = response.json()
        items: list[dict] = raw.get("items", raw) if search.strip() else raw
        return [
            {
                "full_name": r["full_name"],
                "name": r["name"],
                "owner": r["owner"]["login"],
                "private": r.get("private", False),
                "description": (r.get("description") or "")[:120],
                "language": r.get("language"),
                "default_branch": r.get("default_branch") or "main",
                "updated_at": r.get("updated_at"),
            }
            for r in items
        ]

    @staticmethod
    def extract_metadata(github_data: dict) -> dict:
        raw_description = github_data.get("description") or ""
        return {
            "github_id": github_data["id"],
            "github_repo": github_data["full_name"],
            "default_branch": github_data.get("default_branch") or "main",
            "language": github_data.get("language") or None,
            "description": raw_description[:500] or None,
            "is_private": bool(github_data.get("private", False)),
        }
