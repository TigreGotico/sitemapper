"""Passive site discovery (no crawl): robots.txt + sitemaps."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

from sitemapper.robots import Robots, parse_robots
from sitemapper.sitemap import Sitemap, SitemapUrl, fetch_sitemaps

if TYPE_CHECKING:
    from unblock_requests import CloudflareSession

_DEFAULT_MAX_SITEMAPS = 50
_DEFAULT_MAX_URLS = 10_000


@dataclass
class SiteDiscovery:
    """Result of a passive :func:`discover` call.

    Attributes:
        base_url:  The URL that was passed to :func:`discover`.
        robots:    Parsed robots.txt (may have empty fields if unreachable).
        sitemaps:  Each sitemap document fetched.
        urls:      Deduplicated list of all :class:`~sitemapper.sitemap.SitemapUrl`
                   entries found across all sitemaps.
    """

    base_url: str
    robots: Robots = field(default_factory=Robots)
    sitemaps: List[Sitemap] = field(default_factory=list)
    urls: List[SitemapUrl] = field(default_factory=list)

    @property
    def url_count(self) -> int:
        """Number of deduplicated URLs found in the sitemaps."""
        return len(self.urls)

    def to_dict(self) -> dict:
        return {
            "base_url": self.base_url,
            "robots": self.robots.to_dict(),
            "sitemaps": [s.to_dict() for s in self.sitemaps],
            "url_count": self.url_count,
            "urls_sample": [u.to_dict() for u in self.urls[:20]],
        }

    def summary(self) -> str:
        sitemap_count = len([s for s in self.sitemaps if not s.is_index])
        lines = [
            f"Base URL:       {self.base_url}",
            f"Sitemaps found: {sitemap_count}",
            f"URLs in sitemaps: {self.url_count}",
            f"Crawl-delay:    {self.robots.crawl_delay}",
            f"Sitemap directives in robots.txt: {len(self.robots.sitemaps)}",
        ]
        if self.urls:
            lines.append("Sample URLs:")
            for u in self.urls[:5]:
                lines.append(f"  {u.loc}")
        return "\n".join(lines)


def discover(
    base_url: str,
    session: "CloudflareSession",
    *,
    timeout: float = 30.0,
    max_sitemaps: int = _DEFAULT_MAX_SITEMAPS,
    max_urls: int = _DEFAULT_MAX_URLS,
) -> SiteDiscovery:
    """Passively discover a site's structure from robots.txt and sitemaps.

    No HTML pages are fetched.  Fetches:

    1. ``/robots.txt`` — extracts ``Sitemap:`` directives and ``Crawl-delay``.
    2. All sitemaps referenced in robots.txt plus the conventional
       ``/sitemap.xml`` (deduplicated).

    Args:
        base_url:     The site's base URL (scheme + host, e.g.
                      ``https://example.com``).
        session:      Transport session.
        timeout:      Per-request timeout in seconds.
        max_sitemaps: Cap on total sitemap documents fetched (recursion bound).
        max_urls:     Cap on total sitemap URLs collected.

    Returns:
        A populated :class:`SiteDiscovery`.
    """
    # Normalise base — strip trailing slash.
    base = base_url.rstrip("/")

    # 1. Fetch robots.txt (soft-fail — recon must not break on missing robots).
    robots_url = urljoin(base + "/", "robots.txt")
    robots_text = ""
    try:
        r = session.get(robots_url, timeout=timeout)
        if r.status_code == 200:
            robots_text = r.text
    except Exception:
        pass
    robots = parse_robots(robots_text, base_url=robots_url)

    # 2. Collect sitemap URLs to fetch.
    sitemap_urls = list(dict.fromkeys(
        robots.sitemaps + [urljoin(base + "/", "sitemap.xml")]
    ))

    # 3. Fetch and parse all sitemaps.
    sitemaps = fetch_sitemaps(
        sitemap_urls,
        session,
        timeout=timeout,
        max_sitemaps=max_sitemaps,
        max_urls=max_urls,
    )

    # 4. Collect deduplicated URLs.
    seen: set = set()
    all_urls: List[SitemapUrl] = []
    for sm in sitemaps:
        for su in sm.urls:
            if su.loc not in seen:
                seen.add(su.loc)
                all_urls.append(su)

    return SiteDiscovery(
        base_url=base_url,
        robots=robots,
        sitemaps=sitemaps,
        urls=all_urls,
    )
