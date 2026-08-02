"""Offline tests for site discovery."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sitemapper.discovery import discover

_FIXTURES = Path(__file__).parent / "fixtures"


def _make_mock_session(responses: dict):
    """Build a mock CloudflareSession from a {url: bytes_or_exception} map.

    URLs not present in *responses* are answered with a 404 (matching real
    server behaviour for a missing robots.txt/sitemap.xml) rather than a
    fabricated 200 with empty body.
    """
    session = MagicMock()
    def _get(url, **kwargs):
        val = responses.get(url)
        if isinstance(val, Exception):
            raise val
        r = MagicMock()
        if val is None:
            r.status_code = 404
            r.content = b""
            r.text = ""
            r.raise_for_status = MagicMock(side_effect=Exception("404 Not Found"))
            return r
        r.status_code = 200
        content = val if isinstance(val, bytes) else val.encode()
        r.content = content
        r.text = content.decode()
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


# -- fixture-replay tests, recorded from real live responses ----------------
#
# tests/fixtures/live_sitemaps_org_robots.txt   <- https://www.sitemaps.org/robots.txt
# tests/fixtures/live_sitemaps_org_sitemap.xml  <- https://www.sitemaps.org/sitemap.xml
# tests/fixtures/live_python_org_robots.txt     <- https://www.python.org/robots.txt
# Recorded 2026-08-02 via sitemapper.transport.make_session (one bounded
# live GET per file, saved verbatim).


def test_discover_happy_path_real_sitemap():
    """Replay a real recorded robots.txt + sitemap.xml pair (sitemaps.org).

    Covers the full happy path: a ``Sitemap:`` directive in robots.txt is
    followed and every ``<url>`` entry in the referenced sitemap is
    collected.
    """
    robots_bytes = (_FIXTURES / "live_sitemaps_org_robots.txt").read_bytes()
    sitemap_bytes = (_FIXTURES / "live_sitemaps_org_sitemap.xml").read_bytes()
    session = _make_mock_session({
        "https://www.sitemaps.org/robots.txt": robots_bytes,
        "https://www.sitemaps.org/sitemap.xml": sitemap_bytes,
    })
    result = discover("https://www.sitemaps.org", session)
    assert result.blocked is False
    assert result.robots.sitemaps == ["https://www.sitemaps.org/sitemap.xml"]
    assert result.url_count == 84
    assert any(u.loc == "https://www.sitemaps.org/" for u in result.urls)
    assert any(u.loc == "https://www.sitemaps.org/protocol.html" for u in result.urls)


def test_discover_real_site_without_sitemap_directive():
    """Replay a real recorded robots.txt (python.org) with no ``Sitemap:``
    directive — discovery must still succeed, with an empty sitemap set
    and no network call for a sitemap that doesn't exist beyond the
    conventional ``/sitemap.xml`` fallback (which 404s here)."""
    robots_bytes = (_FIXTURES / "live_python_org_robots.txt").read_bytes()
    session = _make_mock_session({
        "https://www.python.org/robots.txt": robots_bytes,
    })
    result = discover("https://www.python.org", session)
    assert result.blocked is False
    assert result.robots.sitemaps == []
    assert result.url_count == 0
    # The conventional /sitemap.xml fallback was attempted and recorded
    # as a fetch error (no fixture registered for it => mock returns None).
    assert len(result.sitemaps) == 1
    assert result.sitemaps[0].url == "https://www.python.org/sitemap.xml"


def test_discover_blocked_page_yields_no_sitemap_directives():
    """Regression test for the soft-block detection bug: a generic
    block/interstitial page served in place of robots.txt must not be
    parsed as if it were real robots.txt content (it previously always
    fell through as ``blocked=False`` because ``unblock_requests`` has no
    ``is_blocked`` attribute — see discovery.py's ``_is_soft_block``)."""
    block_page = b"""<!DOCTYPE html>
<html><head><title>403 Forbidden - Access Denied</title></head>
<body><h1>Access Denied</h1></body></html>
"""
    session = _make_mock_session({
        "https://example.com/robots.txt": block_page,
    })
    result = discover("https://example.com", session)
    assert result.blocked is True
    assert result.robots.sitemaps == []
    assert result.robots.raw_text == ""
