"""Offline tests for robots.txt parsing."""
import pathlib
import pytest

from sitemapper.robots import parse_robots

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _robots_text():
    return (FIXTURES / "robots.txt").read_text()


def test_sitemap_directives():
    r = parse_robots(_robots_text())
    assert "https://example.com/sitemap.xml" in r.sitemaps
    assert "https://example.com/sitemap-news.xml" in r.sitemaps


def test_crawl_delay():
    r = parse_robots(_robots_text())
    assert r.crawl_delay == 2.0


def test_groups():
    r = parse_robots(_robots_text())
    agents = [a for g in r.groups for a in g.user_agents]
    assert "*" in agents
    assert "Googlebot" in agents


def test_disallow():
    r = parse_robots(_robots_text())
    assert not r.is_allowed("https://example.com/admin/secret", "*")
    assert r.is_allowed("https://example.com/about", "*")


def test_allow_overrides_disallow():
    r = parse_robots(_robots_text())
    # /admin/public/ is explicitly allowed
    assert r.is_allowed("https://example.com/admin/public/page", "*")


def test_empty_robots():
    r = parse_robots("")
    assert r.sitemaps == []
    assert r.crawl_delay is None
    assert r.is_allowed("https://example.com/anything")


def test_to_dict():
    r = parse_robots(_robots_text())
    d = r.to_dict()
    assert "sitemaps" in d
    assert "crawl_delay" in d
    assert isinstance(d["groups"], list)
