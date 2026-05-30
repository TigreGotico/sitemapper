"""Offline tests for sitemap parsing."""
import gzip
import pathlib
from unittest.mock import MagicMock, patch

import pytest

from sitemapper.sitemap import (
    Sitemap,
    SitemapUrl,
    _decompress,
    _parse_urlset,
    _parse_sitemapindex,
    _parse_xml,
    fetch_sitemaps,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_parse_urlset():
    data = (FIXTURES / "sitemap.xml").read_bytes()
    root = _parse_xml(data)
    assert root is not None
    urls = _parse_urlset(root, "https://example.com/sitemap.xml")
    assert len(urls) == 3
    locs = [u.loc for u in urls]
    assert "https://example.com/" in locs
    assert "https://example.com/about" in locs


def test_sitemap_url_fields():
    data = (FIXTURES / "sitemap.xml").read_bytes()
    root = _parse_xml(data)
    urls = _parse_urlset(root, "")
    home = next(u for u in urls if u.loc == "https://example.com/")
    assert home.lastmod == "2024-01-01"
    assert home.changefreq == "daily"
    assert home.priority == 1.0


def test_parse_sitemapindex():
    data = (FIXTURES / "sitemapindex.xml").read_bytes()
    root = _parse_xml(data)
    assert root is not None
    locs = _parse_sitemapindex(root)
    assert "https://example.com/sitemap-pages.xml" in locs
    assert "https://example.com/sitemap-blog.xml" in locs


def test_decompress_gz():
    gz_data = (FIXTURES / "sitemap.xml.gz").read_bytes()
    raw = _decompress(gz_data, "sitemap.xml.gz")
    assert b"<urlset" in raw
    assert b"gzipped-page" in raw


def test_decompress_plain():
    data = b"<hello/>"
    assert _decompress(data, "sitemap.xml") == data


def _make_mock_session(responses: dict):
    """Build a mock CloudflareSession from a {url: bytes_or_exception} map."""
    session = MagicMock()
    def _get(url, **kwargs):
        val = responses.get(url)
        if isinstance(val, Exception):
            raise val
        r = MagicMock()
        r.status_code = 200
        r.content = val or b""
        r.raise_for_status = lambda: None
        return r
    session.get = _get
    return session


def test_fetch_urlset():
    data = (FIXTURES / "sitemap.xml").read_bytes()
    session = _make_mock_session({"https://example.com/sitemap.xml": data})
    sms = fetch_sitemaps(["https://example.com/sitemap.xml"], session)
    assert len(sms) == 1
    assert len(sms[0].urls) == 3


def test_fetch_sitemapindex_recurses():
    index_data = (FIXTURES / "sitemapindex.xml").read_bytes()
    pages_data = (FIXTURES / "sitemap.xml").read_bytes()
    blog_data = b"""<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/blog/post-1</loc></url></urlset>"""
    session = _make_mock_session({
        "https://example.com/sitemapindex.xml": index_data,
        "https://example.com/sitemap-pages.xml": pages_data,
        "https://example.com/sitemap-blog.xml": blog_data,
    })
    sms = fetch_sitemaps(["https://example.com/sitemapindex.xml"], session)
    # Should have index + 2 children
    assert any(s.is_index for s in sms)
    all_locs = {u.loc for s in sms for u in s.urls}
    assert "https://example.com/blog/post-1" in all_locs


def test_fetch_gzipped():
    gz_data = (FIXTURES / "sitemap.xml.gz").read_bytes()
    session = _make_mock_session({"https://example.com/sitemap.xml.gz": gz_data})
    sms = fetch_sitemaps(["https://example.com/sitemap.xml.gz"], session)
    assert sms[0].urls[0].loc == "https://example.com/gzipped-page"


def test_fetch_error_is_recorded():
    session = _make_mock_session({"https://example.com/broken.xml": Exception("connection refused")})
    sms = fetch_sitemaps(["https://example.com/broken.xml"], session)
    assert sms[0].error is not None


def test_max_urls_cap():
    many = "".join(f"<url><loc>https://example.com/p{i}</loc></url>" for i in range(100))
    data = f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{many}</urlset>'.encode()
    session = _make_mock_session({"https://example.com/big.xml": data})
    sms = fetch_sitemaps(["https://example.com/big.xml"], session, max_urls=10)
    assert len(sms[0].urls) == 10


def test_sitemap_to_dict():
    data = (FIXTURES / "sitemap.xml").read_bytes()
    session = _make_mock_session({"https://example.com/sitemap.xml": data})
    sm = fetch_sitemaps(["https://example.com/sitemap.xml"], session)[0]
    d = sm.to_dict()
    assert d["url_count"] == 3
    assert d["is_index"] is False
