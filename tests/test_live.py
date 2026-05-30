"""Live integration tests — require network access.

Skip with: pytest -m "not live"
"""
import pytest

from sitemapper import discover


@pytest.mark.live
def test_discover_site_with_sitemap():
    """A site that declares a sitemap in robots.txt is fully discovered.

    cloudflare.com is also Cloudflare-fronted, so this exercises the transport
    end to end.
    """
    info = discover("https://www.cloudflare.com", timeout=30.0)
    assert info.base_url.startswith("https://www.cloudflare.com")
    assert info.robots.sitemaps, "expected a Sitemap: directive in robots.txt"
    assert info.url_count > 0, "expected sitemap URLs to be collected"
    assert "cloudflare.com" in info.summary()


@pytest.mark.live
def test_discover_site_without_sitemap_is_graceful():
    """A site with no Sitemap directive and no /sitemap.xml must return an
    empty (but valid) discovery rather than erroring — python.org is such a
    site."""
    info = discover("https://www.python.org", timeout=30.0)
    assert info.base_url.startswith("https://www.python.org")
    assert info.url_count == 0
    assert not info.robots.sitemaps
