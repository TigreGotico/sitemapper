"""Bounded BFS crawler.

Fetches internal HTML pages starting from *base_url*, extracts ``<a href>``
links, classifies them as internal or external, and builds a :class:`LinkGraph`.
"""
from __future__ import annotations

import re
import time
from collections import deque
from typing import List, Optional, Set, TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from sitemapper.graph import LinkGraph, Node
from sitemapper.robots import Robots

if TYPE_CHECKING:
    from unblock_requests import CloudflareSession

# File extensions that are clearly non-HTML assets — never enqueue these.
_ASSET_EXTS = frozenset(
    ".jpg .jpeg .png .gif .webp .svg .ico .bmp "
    ".css .js .mjs .ts .woff .woff2 .ttf .eot "
    ".pdf .zip .gz .tar .rar .7z .mp3 .mp4 .ogg "
    ".wav .avi .mov .webm .xml .json .csv .xls .xlsx".split()
)

_HTML_TYPES = ("text/html", "application/xhtml+xml")


def _normalise(url: str) -> str:
    """Strip fragment and normalise trailing slash consistently."""
    p = urlparse(url)
    # drop fragment
    p = p._replace(fragment="")
    return urlunparse(p)


def _same_domain(url1: str, url2: str) -> bool:
    """Return True when both URLs share the same registered domain.

    Treats ``www.`` as equivalent to the bare host.
    """
    h1 = urlparse(url1).netloc.lower().removeprefix("www.")
    h2 = urlparse(url2).netloc.lower().removeprefix("www.")
    return h1 == h2


def _is_asset(url: str) -> bool:
    path = urlparse(url).path.lower()
    _, _, ext_part = path.rpartition(".")
    return f".{ext_part}" in _ASSET_EXTS if ext_part else False


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else None


def _extract_links(soup: BeautifulSoup, page_url: str) -> List[str]:
    links: List[str] = []
    for tag in soup.find_all("a", href=True):
        raw = (tag["href"] or "").strip()
        if not raw or raw.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full = urljoin(page_url, raw)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        links.append(_normalise(full))
    return links


def crawl(
    base_url: str,
    session: "CloudflareSession",
    *,
    max_pages: int = 200,
    max_depth: int = 3,
    same_domain: bool = True,
    seed_urls: Optional[List[str]] = None,
    robots: Optional[Robots] = None,
    respect_robots: bool = True,
    delay: Optional[float] = None,
    timeout: float = 30.0,
) -> LinkGraph:
    """Run a bounded BFS crawl from *base_url*.

    Args:
        base_url:       The starting URL; determines what counts as "internal".
        session:        Transport session.
        max_pages:      Maximum number of internal pages to fetch.
        max_depth:      Maximum BFS depth from the seed.
        same_domain:    When True (default) only enqueue pages on the same
                        host as *base_url*.
        seed_urls:      Additional seed URLs (e.g. from a sitemap).
        robots:         Parsed :class:`~sitemapper.robots.Robots` — used for
                        Disallow checks when *respect_robots* is True.
        respect_robots: Honour ``Disallow`` rules from robots.txt.
        delay:          Fixed inter-fetch delay in seconds.  When ``None``
                        the ``Crawl-delay`` from robots.txt is used if present.
        timeout:        Per-request timeout in seconds.

    Returns:
        A populated :class:`~sitemapper.graph.LinkGraph`.
    """
    graph = LinkGraph()
    effective_delay = delay
    if effective_delay is None and robots is not None and robots.crawl_delay is not None:
        effective_delay = robots.crawl_delay

    # BFS queue of (url, depth)
    visited: Set[str] = set()
    queue: deque = deque()

    seeds = [_normalise(base_url)] + [_normalise(u) for u in (seed_urls or [])]
    for s in seeds:
        if s not in visited:
            queue.append((s, 0))
            visited.add(s)
            # Pre-register the node so external references to it are linked.
            graph.add_node(Node(url=s, internal=True, depth=0))

    pages_fetched = 0

    while queue and pages_fetched < max_pages:
        url, depth = queue.popleft()

        # robots.txt check
        if respect_robots and robots is not None:
            if not robots.is_allowed(url):
                continue

        if effective_delay and pages_fetched > 0:
            time.sleep(effective_delay)

        try:
            resp = session.get(url, timeout=timeout)
        except Exception as exc:
            node = graph.nodes.get(url) or Node(url=url, internal=True, depth=depth)
            node.status = 0
            graph.add_node(node)
            pages_fetched += 1
            continue

        ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
        title: Optional[str] = None
        links: List[str] = []

        if any(ct.startswith(h) for h in _HTML_TYPES) or not ct:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = _extract_title(soup)
                links = _extract_links(soup, url)
            except Exception:
                pass

        node = graph.nodes.get(url) or Node(url=url, internal=True, depth=depth)
        node.status = resp.status_code
        node.content_type = ct or None
        node.title = title
        graph.add_node(node)
        pages_fetched += 1

        for link in links:
            if _is_asset(link):
                continue
            parsed = urlparse(link)
            is_internal = (not same_domain) or _same_domain(base_url, link)

            if link not in graph.nodes:
                graph.add_node(
                    Node(
                        url=link,
                        internal=is_internal,
                        depth=depth + 1,
                    )
                )
            graph.add_edge(url, link)

            if (
                is_internal
                and link not in visited
                and depth + 1 <= max_depth
                and pages_fetched + len(queue) < max_pages
            ):
                if not _is_asset(link):
                    visited.add(link)
                    queue.append((link, depth + 1))

    return graph
