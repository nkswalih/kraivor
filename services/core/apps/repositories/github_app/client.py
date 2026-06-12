"""
GitHub App API client — JWT auth, installation tokens, repo access.

Architecture:
  - JWT is generated locally from the app's private key (never sent to GitHub)
  - Installation access tokens are obtained via GitHub's REST API using the JWT
  - Tokens are cached in-memory (never stored in the DB) — they last 1 hour
  - The cache key includes the installation_id for multi-installation support

Usage:
    client = GitHubAppClient()
    token = client.get_installation_token(installation_id=12345)
    repos = client.list_installation_repos(installation_id=12345)
"""

import logging
import time
from typing import Any

import jwt as pyjwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── Exceptions ────────────────────────────────────────────────────────────────


class GitHubAppError(Exception):
    """Base exception for GitHub App operations."""

    pass


class GitHubAppAuthError(GitHubAppError):
    """JWT generation or installation token fetch failed."""

    pass


class GitHubAppAPIError(GitHubAppError):
    """GitHub API returned a non-2xx response."""

    pass


# ─── In-Memory Token Cache ────────────────────────────────────────────────────


class _TokenCache:
    """
    Thread-safe in-memory cache for installation access tokens.

    Tokens expire after 1 hour (GitHub's max). We cache for 55 minutes
    to add a safety margin and avoid edge-of-expiry failures.

    Singleton: all GitHubAppClient instances share the same cache.
    """

    _cache: dict[int, tuple[str, float]] = {}  # installation_id -> (token, expiry_ts)

    TTL_SECONDS = 55 * 60  # 55 minutes

    def get(self, installation_id: int) -> str | None:
        token, expiry = self._cache.get(installation_id, (None, 0.0))
        if token and time.time() < expiry:
            return token
        self._cache.pop(installation_id, None)
        return None

    def set(self, installation_id: int, token: str) -> None:
        self._cache[installation_id] = (token, time.time() + self.TTL_SECONDS)

    def invalidate(self, installation_id: int) -> None:
        self._cache.pop(installation_id, None)


_token_cache = _TokenCache()

# ─── GitHub App Client ────────────────────────────────────────────────────────


class GitHubAppClient:
    """
    GitHub App authentication and API client.

    Requires the following Django settings:
      GITHUB_APP_ID           — numeric GitHub App ID
      GITHUB_APP_PRIVATE_KEY  — RSA private key string (loaded from env/secret)
      GITHUB_APP_SLUG         — GitHub App slug for constructing installation URLs
      GITHUB_APP_CLIENT_ID    — GitHub App client ID (for callback validation)

    All API calls use installation access tokens for repo-scoped requests.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self):
        self._app_id = getattr(settings, "GITHUB_APP_ID", "")
        self._private_key = getattr(settings, "GITHUB_APP_PRIVATE_KEY", "")
        self._slug = getattr(settings, "GITHUB_APP_SLUG", "")
        self._client_id = getattr(settings, "GITHUB_APP_CLIENT_ID", "")

    # ── JWT Generation ────────────────────────────────────────────────────────

    def _generate_jwt(self) -> str:
        """
        Generate a short-lived JWT signed with the app's private key.

        The JWT is used to authenticate as the GitHub App (not as a user)
        and is only valid for requesting installation tokens or other
        app-level endpoints. Maximum GitHub-allowed expiry is 10 minutes.
        """
        if not self._app_id or not self._private_key:
            raise GitHubAppAuthError(
                "GitHub App is not configured. Missing GITHUB_APP_ID or "
                "GITHUB_APP_PRIVATE_KEY in settings."
            )

        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued 60s ago to allow clock drift
            "exp": now + 600,  # 10 minutes (GitHub max)
            "iss": str(self._app_id),
        }
        try:
            token = pyjwt.encode(payload, self._private_key, algorithm="RS256")
            return token if isinstance(token, str) else token.decode("utf-8")
        except Exception as exc:
            raise GitHubAppAuthError(
                f"Failed to generate GitHub App JWT: {exc}"
            ) from exc

    # ── Installation Token ────────────────────────────────────────────────────

    def get_installation_token(self, installation_id: int) -> str:
        """
        Return a valid installation access token for the given installation.

        Uses in-memory cache to avoid unnecessary API calls. Tokens are
        valid for 1 hour; we cache for 55 minutes and fetch a new one
        when the cached token expires.

        Raises:
            GitHubAppAuthError — JWT generation failed
            GitHubAppAPIError  — token request failed
        """
        cached = _token_cache.get(installation_id)
        if cached:
            return cached

        jwt_token = self._generate_jwt()
        url = (
            f"{self.GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
        )
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            response = requests.post(url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise GitHubAppAPIError(
                f"Failed to request installation token: {exc}"
            ) from exc

        if response.status_code == 401:
            raise GitHubAppAuthError(
                "GitHub App JWT rejected. Check your private key and app ID."
            )
        if response.status_code == 404:
            raise GitHubAppAPIError(
                f"Installation {installation_id} not found. It may have been "
                "uninstalled or revoked."
            )
        if response.status_code != 201:
            raise GitHubAppAPIError(
                f"GitHub returned HTTP {response.status_code} when requesting "
                f"installation token: {response.text[:200]}"
            )

        data = response.json()
        token = data.get("token")
        if not token:
            raise GitHubAppAPIError(
                "GitHub returned a 201 response but no token was present."
            )

        _token_cache.set(installation_id, token)
        return token

    # ── List Installation Repositories ────────────────────────────────────────

    def list_installation_repos(
        self, installation_id: int, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """
        List all repositories accessible to this installation.

        Returns a flat list of repo dicts with the fields needed by
        the repo picker and sync logic.

        Handles pagination automatically (up to 1000 repos).
        """
        token = self.get_installation_token(installation_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        repos: list[dict[str, Any]] = []
        url = f"{self.GITHUB_API_BASE}/installation/repositories"
        params = {"per_page": min(per_page, 100)}
        page_count = 0

        while url and page_count < 10:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=10)
            except requests.exceptions.RequestException as exc:
                raise GitHubAppAPIError(
                    f"Failed to list installation repos: {exc}"
                ) from exc

            if response.status_code == 401:
                _token_cache.invalidate(installation_id)
                raise GitHubAppAuthError(
                    "Installation token expired or invalid. Retry to refresh."
                )
            if response.status_code != 200:
                raise GitHubAppAPIError(
                    f"GitHub returned HTTP {response.status_code} for "
                    f"installation repos: {response.text[:200]}"
                )

            data = response.json()
            repos.extend(data.get("repositories", []))

            # Check for pagination (Link header)
            url = None
            link_header = response.headers.get("Link", "")
            if 'rel="next"' in link_header:
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        url = part.split(";")[0].strip().strip("<>")
                        break

            params = {}
            page_count += 1

        return repos

    # ── Resolve Installation (for the callback) ───────────────────────────────

    def get_installation_info(self, installation_id: int) -> dict[str, Any]:
        """
        Fetch installation metadata from GitHub.

        Returns the raw GitHub API response for /app/installations/{id}.

        Requires JWT auth (not installation token).
        """
        jwt_token = self._generate_jwt()
        url = f"{self.GITHUB_API_BASE}/app/installations/{installation_id}"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise GitHubAppAPIError(
                f"Failed to fetch installation info: {exc}"
            ) from exc

        if response.status_code == 404:
            raise GitHubAppAPIError(f"Installation {installation_id} not found.")
        if response.status_code != 200:
            raise GitHubAppAPIError(
                f"GitHub returned HTTP {response.status_code} for "
                f"installation info: {response.text[:200]}"
            )

        return response.json()

    # ── Get Repository Metadata ───────────────────────────────────────────────

    def get_repository(self, installation_id: int, github_repo: str) -> dict[str, Any]:
        """
        Fetch metadata for a specific repo via the installation's token.

        Used by connect_repository() to verify the repo is accessible
        and fetch its metadata before creating the Repository record.
        """
        token = self.get_installation_token(installation_id)
        url = f"{self.GITHUB_API_BASE}/repos/{github_repo}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            raise GitHubAppAPIError(
                "Unable to reach GitHub. Please try again later."
            ) from exc

        if response.status_code == 404:
            raise GitHubAppAPIError(
                f"Repository '{github_repo}' was not found on GitHub or "
                "is not accessible through the current installation."
            )
        if response.status_code == 403:
            raise GitHubAppAPIError(
                "Access denied. The installation may not have access to "
                "this repository."
            )
        if response.status_code == 401:
            _token_cache.invalidate(installation_id)
            raise GitHubAppAuthError("Installation token expired. Please try again.")
        if response.status_code != 200:
            raise GitHubAppAPIError(
                f"GitHub returned HTTP {response.status_code} for repo "
                f"'{github_repo}': {response.text[:200]}"
            )

        return response.json()

    # ── Installation URL ──────────────────────────────────────────────────────

    def get_installation_url(self, state: str) -> str:
        """
        Return the GitHub App installation URL with the given state parameter.

        The state is a unique token stored in Redis that encodes the
        workspace context (workspace_id, user_id) so the callback can
        reconstruct it without exposing it in the URL.
        """
        if not self._slug:
            raise GitHubAppError(
                "GitHub App slug is not configured. Set GITHUB_APP_SLUG."
            )
        return (
            f"https://github.com/apps/{self._slug}/installations/new?state={state}"
        )
