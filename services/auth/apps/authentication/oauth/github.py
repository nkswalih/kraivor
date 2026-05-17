"""
GitHub OAuth Service
====================

Handles GitHub OAuth 2.0 authentication flow.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GitHubOAuthError(Exception):
    pass


class GitHubAPIError(GitHubOAuthError):
    pass


@dataclass
class GitHubUser:
    id: int
    login: str
    name: str | None
    email: str | None
    avatar_url: str | None


class GitHubOAuthService:
    AUTHORIZATION_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"
    EMAILS_API_URL = "https://api.github.com/user/emails"

    def __init__(self):
        self.client_id = getattr(settings, "GITHUB_CLIENT_ID", "")
        self.client_secret = getattr(settings, "GITHUB_CLIENT_SECRET", "")
        self.redirect_uri = getattr(settings, "GITHUB_REDIRECT_URI", "")

    def get_authorization_url(self, state: str) -> str:
        if not self.client_id:
            raise GitHubOAuthError("GitHub client ID not configured")

        from urllib.parse import urlencode

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email read:user",
            "state": state,
        }
        return f"{self.AUTHORIZATION_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> str:
        if not self.client_id or not self.client_secret:
            raise GitHubOAuthError("GitHub OAuth credentials not configured")

        try:
            response = requests.post(
                self.TOKEN_URL,
                data={"client_id": self.client_id, "client_secret": self.client_secret, "code": code},
                headers={"Accept": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                raise GitHubAPIError("No access token in response")
            return access_token
        except requests.RequestException as e:
            raise GitHubAPIError(f"Failed to exchange code for token: {e}") from e

    def get_user(self, access_token: str) -> GitHubUser:
        try:
            response = requests.get(
                self.USER_API_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return GitHubUser(id=data.get("id"), login=data.get("login"), name=data.get("name"), email=data.get("email"), avatar_url=data.get("avatar_url"))
        except requests.RequestException as e:
            raise GitHubAPIError(f"Failed to fetch user profile: {e}") from e

    def get_emails(self, access_token: str) -> list:
        try:
            response = requests.get(
                self.EMAILS_API_URL,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            response.raise_for_status()
            emails_data = response.json()
            emails = [{"email": e.get("email"), "primary": e.get("primary", False), "verified": e.get("verified", False)} for e in emails_data if e.get("email")]
            emails.sort(key=lambda e: (not e["primary"], not e["verified"]))
            return emails
        except requests.RequestException as e:
            raise GitHubAPIError(f"Failed to fetch emails: {e}") from e

    def get_primary_verified_email(self, access_token: str) -> str | None:
        emails = self.get_emails(access_token)
        for email in emails:
            if email["primary"] and email["verified"]:
                return email["email"]
        for email in emails:
            if email["verified"]:
                return email["email"]
        return None


_oauth_service: GitHubOAuthService | None = None


def get_github_oauth_service() -> GitHubOAuthService:
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = GitHubOAuthService()
    return _oauth_service