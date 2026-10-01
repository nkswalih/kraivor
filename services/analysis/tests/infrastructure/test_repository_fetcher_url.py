"""Regression test for GitHub token exfiltration via clone URL.

``clone()`` splices a GitHub App token into the clone URL so private
repositories can be fetched. The original check was a substring test::

    if github_token and "github.com" in clone_url:
        clone_url = clone_url.replace("https://github.com", f"...{token}@github.com")

Because the replace target is a prefix, a URL of
``https://github.com.evil.com/attacker/repo.git`` satisfied the substring
test *and* matched the replace target, producing
``https://x-access-token:<token>@github.com.evil.com/...``. Git then
connects to the attacker's host with the token in the userinfo field.

The fix compares the parsed hostname against an exact allowlist.
"""

from urllib.parse import urlsplit

import pytest

from app.infrastructure.git.repository_fetcher import _is_github_host


class TestIsGithubHost:
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/nkswalih/kraivor.git",
            "https://www.github.com/nkswalih/kraivor.git",
            "https://GitHub.com/nkswalih/kraivor.git",
        ],
    )
    def test_accepts_github(self, url):
        assert _is_github_host(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            # The exfiltration vector: prefix matches the replace target.
            "https://github.com.evil.com/attacker/repo.git",
            # Substring in path or query.
            "https://evil.com/github.com",
            "https://evil.com/?ref=github.com",
            # Near-miss hostnames.
            "https://notgithub.com/x",
            "https://githubXcom/x",
            "https://github.com.co/x",
            # A GitHub Pages or gist host is not the git host.
            "https://raw.githubusercontent.com/x",
        ],
    )
    def test_rejects_lookalikes(self, url):
        assert _is_github_host(url) is False

    def test_rejects_ssh_form(self):
        """The token injection only rewrites https URLs."""
        assert _is_github_host("git@github.com:nkswalih/kraivor.git") is False

    def test_rejects_malformed(self):
        assert _is_github_host("not a url") is False
        assert _is_github_host("") is False

    def test_token_is_not_injected_for_attacker_host(self):
        """End-to-end shape of the original bug, asserted directly."""
        token = "ghp_SECRETTOKEN123"
        clone_url = "https://github.com.evil.com/attacker/repo.git"

        # The replace is unchanged — only the guard is new.
        if _is_github_host(clone_url):
            clone_url = clone_url.replace(
                "https://github.com", f"https://x-access-token:{token}@github.com"
            )

        assert token not in clone_url
        assert urlsplit(clone_url).hostname == "github.com.evil.com"
