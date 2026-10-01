"""Tests for knowledge-engine domain matching.

The freshness half-life and the authority score both key off the URL's host.
Those checks used to be substring tests (``"news" in domain``), which match
any position in the string, so an attacker-registered lookalike host was
scored as if it were a trusted source. These tests pin the exact-match
behaviour and the lookalikes it has to reject.
"""

import pytest

from app.knowledge_engine.ranking.authority import _domain_is, get_domain_half_life


class TestDomainIs:
    @pytest.mark.parametrize(
        "domain",
        [
            "github.com",
            "GitHub.com",
            "GITHUB.COM",
            "www.github.com",
            "gist.github.com",
            "api.github.com",
            "github.com:8443",
        ],
    )
    def test_accepts_apex_and_subdomains(self, domain):
        assert _domain_is(domain, "github.com") is True

    @pytest.mark.parametrize(
        "domain",
        [
            # Substring check would match these; exact match must not.
            "github.com.evil.example",
            "evil.example/github.com",
            "notgithub.com",
            "github.com.cn",
            "mygithub.com",
            "xgithub.com.evil.example",
        ],
    )
    def test_rejects_lookalikes(self, domain):
        assert _domain_is(domain, "github.com") is False

    def test_trailing_dot_is_normalised(self):
        assert _domain_is("github.com.", "github.com") is True

    def test_matches_any_of_several_suffixes(self):
        assert _domain_is("reddit.com", "reddit.com", "redd.it") is True
        assert _domain_is("old.reddit.com", "reddit.com", "redd.it") is True
        assert _domain_is("example.com", "reddit.com", "redd.it") is False

    def test_empty_domain_never_matches(self):
        assert _domain_is("", "github.com") is False


class TestDomainHalfLife:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://techcrunch.com/2026/01/story", 7),
            ("https://www.theverge.com/story", 7),
            ("https://arstechnica.com/information-technology/", 7),
            ("https://news.ycombinator.com/item?id=1", 7),
            ("https://github.com/psf/requests/pull/1", 30),
            ("https://github.com:443/psf/requests", 30),
            ("https://arxiv.org/abs/2601.00001", 365),
            ("https://www.semanticscholar.org/paper/1", 365),
            ("https://stackoverflow.com/questions/1", 90),
            ("https://dev.to/someone/post", 90),
            ("https://reddit.com/r/python", 30),
            ("https://old.reddit.com/r/python", 30),
            ("https://example.com/post", 60),
        ],
    )
    def test_known_domains(self, url, expected):
        assert get_domain_half_life(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            # Each of these contains a trusted token but is not the trusted
            # host. A substring check would have given them a curated
            # half-life and inflated authority accordingly.
            "https://techcrunch.com.evil.example/story",
            "https://github.com.evil.example/psf/requests",
            "https://notgithub.com/x",
            "https://arxiv.org.evil.example/abs/1",
            "https://stackoverflow.com.evil.example/q/1",
            "https://reddit.com.evil.example/r/python",
            "https://evil.example/?ref=github.com",
        ],
    )
    def test_lookalike_hosts_fall_back_to_default(self, url):
        assert get_domain_half_life(url) == 60

    def test_url_without_netloc_uses_default(self):
        assert get_domain_half_life("not-a-url") == 60
