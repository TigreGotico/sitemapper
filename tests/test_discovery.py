"""Offline tests for site discovery."""
from unittest.mock import MagicMock

import pytest

from sitemapper.discovery import discover


def _make_mock_session(responses: dict):
    """Build a mock CloudflareSession from a {url: bytes_or_exception} map."""
    session = MagicMock()
    def _get(url, **kwargs):
        val = responses.get(url)
        if isinstance(val, Exception):
            raise val
        r = MagicMock()
        r.status_code = 200
        r.text = val.decode() if isinstance(val, bytes) else val
        r.raise_for_status = lambda: None
        return r
    session.get = _get
    return session


def test_discover_basic():
    """Test basic discovery without blocks."""
    robots_text = b"""User-agent: *
Disallow: /admin
Sitemap: https://example.com/sitemap.xml
"""
    session = _make_mock_session({
        "https://example.com/robots.txt": robots_text,
    })
    result = discover("https://example.com", session)
    assert result.base_url == "https://example.com"
    assert result.blocked is False
    assert result.robots.crawl_delay is None


def test_discover_robots_missing():
    """Test discovery when robots.txt returns 404 or doesn't exist."""
    session = MagicMock()
    session.get.return_value.status_code = 404
    result = discover("https://example.com", session)
    assert result.base_url == "https://example.com"
    assert result.blocked is False


def test_discover_robots_exception():
    """Test discovery when robots.txt fetch raises an exception."""
    session = MagicMock()
    session.get.side_effect = Exception("connection refused")
    result = discover("https://example.com", session)
    assert result.base_url == "https://example.com"
    assert result.blocked is False


def test_discover_robots_blocked_403_title():
    """Test discovery when robots.txt is a block page with 403-style title."""
    block_page = b"""<!DOCTYPE html>
<html>
<head>
<title>403 Forbidden - Access Denied</title>
</head>
<body>
<h1>Access Denied</h1>
<p>You have been blocked from accessing this resource.</p>
</body>
</html>
"""
    session = _make_mock_session({
        "https://example.com/robots.txt": block_page,
    })
    result = discover("https://example.com", session)
    assert result.base_url == "https://example.com"
    assert result.blocked is True
    # When blocked, robots should be empty/unparsed
    assert len(result.robots.sitemaps) == 0


def test_discover_robots_blocked_permission_denied():
    """Test discovery when robots.txt is a block page with permission denied."""
    block_page = b"""<!DOCTYPE html>
<html>
<head>
<title>Permission Denied</title>
</head>
<body>
<h1>You have been blocked</h1>
</body>
</html>
"""
    session = _make_mock_session({
        "https://example.com/robots.txt": block_page,
    })
    result = discover("https://example.com", session)
    assert result.blocked is True


def test_discover_max_urls_parameter():
    """Test that max_urls parameter is passed through."""
    robots_text = b"User-agent: *\nDisallow: /admin\n"
    session = _make_mock_session({
        "https://example.com/robots.txt": robots_text,
    })
    # Just verify the parameter is accepted without error
    result = discover(
        "https://example.com",
        session,
        max_urls=100_000
    )
    assert result.base_url == "https://example.com"


def test_discover_max_sitemaps_parameter():
    """Test that max_sitemaps parameter is passed through."""
    robots_text = b"User-agent: *\nDisallow: /admin\n"
    session = _make_mock_session({
        "https://example.com/robots.txt": robots_text,
    })
    # Just verify the parameter is accepted without error
    result = discover(
        "https://example.com",
        session,
        max_sitemaps=100
    )
    assert result.base_url == "https://example.com"


def test_site_discovery_to_dict_includes_blocked():
    """Test that SiteDiscovery.to_dict() includes blocked flag."""
    robots_text = b"User-agent: *\nDisallow: /admin\n"
    session = _make_mock_session({
        "https://example.com/robots.txt": robots_text,
    })
    result = discover("https://example.com", session)
    d = result.to_dict()
    assert "blocked" in d
    assert d["blocked"] is False


def test_site_discovery_summary_includes_blocked():
    """Test that SiteDiscovery.summary() includes blocked flag."""
    robots_text = b"User-agent: *\nDisallow: /admin\n"
    session = _make_mock_session({
        "https://example.com/robots.txt": robots_text,
    })
    result = discover("https://example.com", session)
    summary = result.summary()
    assert "Blocked:" in summary
    assert "False" in summary
