"""High-level :class:`Sitemapper` class and module-level convenience wrappers."""
from __future__ import annotations

from typing import List, Optional

from sitemapper.discovery import SiteDiscovery
from sitemapper.discovery import discover as _discover
from sitemapper.graph import LinkGraph
from sitemapper.crawler import crawl as _crawl
from sitemapper.transport import make_session

from unblock_requests import CloudflareSession


class Sitemapper:
    """Stateful entry point that holds configuration and caches results.

    Args:
        flaresolverr_url:      FlareSolverr base URL.
        flaresolverr_fallback: Escalate blocked GETs to the solver.
        wayback_fallback:      Fall back to the Wayback Machine on errors.
        timeout:               Default per-request timeout in seconds.
        max_sitemaps:          Cap on sitemap documents fetched per discovery.
        max_urls:              Cap on sitemap URLs collected per discovery.
    """

    def __init__(
        self,
        *,
        flaresolverr_url: Optional[str] = None,
        flaresolverr_fallback: bool = True,
        wayback_fallback: bool = True,
        timeout: float = 30.0,
        max_sitemaps: int = 50,
        max_urls: int = 50_000,
    ) -> None:
        self._session: CloudflareSession = make_session(
            flaresolverr_url=flaresolverr_url,
            flaresolverr_fallback=flaresolverr_fallback,
            wayback_fallback=wayback_fallback,
            timeout=timeout,
        )
        self.timeout = timeout
        self.max_sitemaps = max_sitemaps
        self.max_urls = max_urls
        self._discovery_cache: dict = {}

    @property
    def session(self) -> CloudflareSession:
        """The underlying :class:`~unblock_requests.CloudflareSession`."""
        return self._session

    def discover(self, base_url: str, *, force: bool = False) -> SiteDiscovery:
        """Passively discover site structure (robots.txt + sitemaps).

        Results are cached per *base_url* within this instance.

        Args:
            base_url: The site root (e.g. ``https://example.com``).
            force:    Bypass the cache and re-fetch.

        Returns:
            A :class:`~sitemapper.discovery.SiteDiscovery` instance.
        """
        key = base_url.rstrip("/")
        if not force and key in self._discovery_cache:
            return self._discovery_cache[key]
        result = _discover(
            base_url,
            self._session,
            timeout=self.timeout,
            max_sitemaps=self.max_sitemaps,
            max_urls=self.max_urls,
        )
        self._discovery_cache[key] = result
        return result

    def crawl(
        self,
        base_url: str,
        *,
        max_pages: int = 200,
        max_depth: int = 3,
        same_domain: bool = True,
        use_sitemap: bool = True,
        respect_robots: bool = True,
        delay: Optional[float] = None,
    ) -> LinkGraph:
        """Bounded BFS crawl of *base_url*.

        Args:
            base_url:       The seed URL.
            max_pages:      Maximum internal pages to fetch.
            max_depth:      Maximum BFS depth.
            same_domain:    Restrict enqueuing to the same host.
            use_sitemap:    Seed additional URLs from the site's sitemaps.
            respect_robots: Honour ``Disallow`` rules from robots.txt.
            delay:          Fixed inter-fetch delay (overrides ``Crawl-delay``).

        Returns:
            A :class:`~sitemapper.graph.LinkGraph`.
        """
        discovery = self.discover(base_url)
        seed_urls: List[str] = []
        if use_sitemap:
            seed_urls = [u.loc for u in discovery.urls]

        return _crawl(
            base_url,
            self._session,
            max_pages=max_pages,
            max_depth=max_depth,
            same_domain=same_domain,
            seed_urls=seed_urls,
            robots=discovery.robots if respect_robots else None,
            respect_robots=respect_robots,
            delay=delay,
            timeout=self.timeout,
        )


# ---------------------------------------------------------------------------
# Module-level convenience wrappers (thin — use a shared default instance)
# ---------------------------------------------------------------------------

_default: Optional[Sitemapper] = None


def _get_default() -> Sitemapper:
    global _default
    if _default is None:
        _default = Sitemapper()
    return _default


def discover(base_url: str, *, timeout: float = 30.0) -> SiteDiscovery:
    """Passively discover site structure — robots.txt and sitemaps.

    Uses a module-level default :class:`Sitemapper` instance.

    Args:
        base_url: The site root (e.g. ``https://example.com``).
        timeout:  Per-request timeout in seconds.

    Returns:
        A :class:`~sitemapper.discovery.SiteDiscovery`.
    """
    inst = _get_default()
    inst.timeout = timeout
    return inst.discover(base_url)


def crawl(
    base_url: str,
    *,
    max_pages: int = 200,
    max_depth: int = 3,
    same_domain: bool = True,
    use_sitemap: bool = True,
    respect_robots: bool = True,
    delay: Optional[float] = None,
    timeout: float = 30.0,
) -> LinkGraph:
    """Bounded BFS crawl of *base_url*.

    Uses a module-level default :class:`Sitemapper` instance.

    Args:
        base_url:       The seed URL.
        max_pages:      Maximum internal pages to fetch.
        max_depth:      Maximum BFS depth.
        same_domain:    Restrict enqueuing to the same host.
        use_sitemap:    Seed additional URLs from the site's sitemaps.
        respect_robots: Honour ``Disallow`` rules from robots.txt.
        delay:          Fixed inter-fetch delay.
        timeout:        Per-request timeout in seconds.

    Returns:
        A :class:`~sitemapper.graph.LinkGraph`.
    """
    inst = _get_default()
    inst.timeout = timeout
    return inst.crawl(
        base_url,
        max_pages=max_pages,
        max_depth=max_depth,
        same_domain=same_domain,
        use_sitemap=use_sitemap,
        respect_robots=respect_robots,
        delay=delay,
    )
