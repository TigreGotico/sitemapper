"""sitemapper — site-recon tooling for scraper development.

Given a base URL, discovers site structure (robots.txt + sitemaps) and
optionally crawls internal pages, mapping internal and outgoing links into
a graph.

Quick-start::

    from sitemapper import discover, crawl

    # Passive: no HTML crawl — just robots.txt + sitemaps.
    info = discover("https://www.python.org")
    print(info.summary())

    # Active: bounded BFS crawl.
    graph = crawl("https://www.python.org", max_pages=50)
    print(graph.summary())

All HTTP requests go through :class:`unblock_requests.CloudflareSession`
(env prefix ``SITEMAPPER``), so recon works on Cloudflare-fronted sites.
Set ``SITEMAPPER_FLARESOLVERR_URL=http://localhost:8191`` to enable the
headless-browser solver.
"""
from sitemapper.discovery import SiteDiscovery, discover as _discover
from sitemapper.graph import LinkGraph, Node
from sitemapper.robots import Robots, RobotsGroup, parse_robots
from sitemapper.sitemap import Sitemap, SitemapUrl, fetch_sitemaps
from sitemapper.sitemapper import Sitemapper, crawl, discover
from sitemapper.transport import make_session
from sitemapper.version import __version__

__all__ = [
    # high-level entry points
    "discover",
    "crawl",
    "Sitemapper",
    # data types
    "SiteDiscovery",
    "LinkGraph",
    "Node",
    "Robots",
    "RobotsGroup",
    "Sitemap",
    "SitemapUrl",
    # helpers
    "parse_robots",
    "fetch_sitemaps",
    "make_session",
    "__version__",
]
