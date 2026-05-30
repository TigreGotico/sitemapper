"""Live integration test — requires network access.

Skip with: pytest -m "not live"
"""
import pytest

from sitemapper import discover


@pytest.mark.live
def test_discover_python_org():
    """Passive discovery of https://www.python.org — checks that robots.txt
    and at least one sitemap URL are returned without error."""
    info = discover("https://www.python.org", timeout=30.0)
    assert info.base_url.startswith("https://www.python.org")
    # python.org serves a sitemap
    assert info.url_count > 0 or len(info.sitemaps) > 0
    # robots.txt should be reachable
    assert info.robots.raw_text != "" or info.robots.sitemaps is not None
    summary = info.summary()
    assert "python.org" in summary
