"""Offline tests for the BFS crawler."""
import pathlib
from unittest.mock import MagicMock
import pytest

from sitemapper.crawler import (
    _normalise,
    _same_domain,
    _is_asset,
    _extract_links,
    crawl,
)
from bs4 import BeautifulSoup

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_normalise_drops_fragment():
    assert _normalise("https://example.com/page#section") == "https://example.com/page"


def test_same_domain_www():
    assert _same_domain("https://www.example.com/a", "https://example.com/b")
    assert _same_domain("https://example.com/a", "https://www.example.com/b")


def test_same_domain_different():
    assert not _same_domain("https://example.com/", "https://other.org/")


def test_is_asset():
    assert _is_asset("https://example.com/logo.png")
    assert _is_asset("https://cdn.example.com/main.css")
    assert not _is_asset("https://example.com/about")


def test_extract_links():
    html = (FIXTURES / "page.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    links = _extract_links(soup, "https://example.com/")
    # javascript: and mailto: are excluded
    assert not any("javascript:" in l for l in links)
    assert not any("mailto:" in l for l in links)
    # relative links are resolved
    assert "https://example.com/about" in links
    # external links are included
    assert "https://external.org/partner" in links


def _make_session(pages: dict):
    """Build a mock session from {url: html_str | Exception}."""
    session = MagicMock()
    def _get(url, **kwargs):
        val = pages.get(url)
        if isinstance(val, Exception):
            raise val
        r = MagicMock()
        r.status_code = 200
        r.text = val or ""
        r.headers = {"Content-Type": "text/html; charset=utf-8"}
        return r
    session.get = _get
    return session


def test_crawl_basic():
    home_html = (FIXTURES / "page.html").read_text()
    about_html = "<html><head><title>About</title></head><body><a href='/'>Home</a></body></html>"
    contact_html = "<html><head><title>Contact</title></head><body></body></html>"
    pages = {
        "https://example.com/": home_html,
        "https://example.com/about": about_html,
        "https://example.com/contact": contact_html,
        "https://example.com/blog": "<html><body></body></html>",
        "https://example.com/admin/private": "<html><body></body></html>",
    }
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, max_pages=10, max_depth=2)
    assert "https://example.com/" in graph.nodes
    assert "https://external.org/partner" in graph.nodes


def test_crawl_respects_max_pages():
    html = "".join(f'<a href="/p{i}">link</a>' for i in range(50))
    html = f"<html><body>{html}</body></html>"
    pages = {f"https://example.com/p{i}": "<html><body></body></html>" for i in range(50)}
    pages["https://example.com/"] = html
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, max_pages=5, max_depth=1)
    fetched = [n for n in graph.nodes.values() if n.internal and n.status is not None]
    assert len(fetched) <= 5


def test_crawl_same_domain_true():
    home_html = '<html><body><a href="https://other.org/x">ext</a><a href="/local">local</a></body></html>'
    pages = {
        "https://example.com/": home_html,
        "https://example.com/local": "<html><body></body></html>",
    }
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, same_domain=True, max_pages=10, max_depth=2)
    # external node is recorded but not crawled (no status)
    ext = graph.nodes.get("https://other.org/x")
    if ext:
        assert not ext.internal


def test_crawl_external_nodes_recorded():
    home_html = '<html><body><a href="https://external.org/partner">ext</a></body></html>'
    pages = {"https://example.com/": home_html}
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, max_pages=5, max_depth=1)
    assert "https://external.org/partner" in graph.nodes
    assert not graph.nodes["https://external.org/partner"].internal


def test_crawl_asset_links_not_enqueued():
    home_html = '<html><body><a href="/logo.png">img</a><a href="/about">about</a></body></html>'
    pages = {
        "https://example.com/": home_html,
        "https://example.com/about": "<html><body></body></html>",
    }
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, max_pages=10, max_depth=2)
    # PNG should NOT appear as a fetched node
    png = graph.nodes.get("https://example.com/logo.png")
    if png:
        assert png.status is None


def test_graph_title_captured():
    home_html = '<html><head><title>My Site</title></head><body></body></html>'
    pages = {"https://example.com/": home_html}
    session = _make_session(pages)
    graph = crawl("https://example.com/", session, max_pages=1, max_depth=0)
    assert graph.nodes["https://example.com/"].title == "My Site"
