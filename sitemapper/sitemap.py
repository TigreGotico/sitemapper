"""Sitemap parser.

Handles:
- ``<sitemapindex>`` — recurses into child ``<sitemap><loc>`` entries (bounded).
- ``<urlset>`` — parses ``<url>`` entries with ``<loc>``, ``<lastmod>``,
  ``<changefreq>``, ``<priority>``.
- Gzip-compressed sitemaps (``.gz``).

URL caps and sitemap-fetch caps prevent runaway behaviour on large sites.
"""
from __future__ import annotations

import gzip
import io
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from unblock_requests import CloudflareSession

# XML namespaces used in standard sitemaps.
_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "": "http://www.sitemaps.org/schemas/sitemap/0.9",
}

_DEFAULT_MAX_SITEMAPS = 50
_DEFAULT_MAX_URLS = 10_000


@dataclass
class SitemapUrl:
    """One ``<url>`` entry from a ``<urlset>`` sitemap."""

    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    source_sitemap: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "loc": self.loc,
            "lastmod": self.lastmod,
            "changefreq": self.changefreq,
            "priority": self.priority,
        }


@dataclass
class Sitemap:
    """A parsed sitemap (either a urlset or a sitemapindex)."""

    url: str
    urls: List[SitemapUrl] = field(default_factory=list)
    child_sitemaps: List[str] = field(default_factory=list)
    is_index: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "is_index": self.is_index,
            "url_count": len(self.urls),
            "child_sitemaps": self.child_sitemaps,
            "error": self.error,
        }


def _fetch_bytes(url: str, session: "CloudflareSession", timeout: float) -> bytes:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def _decompress(data: bytes, url: str) -> bytes:
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try:
            return gzip.decompress(data)
        except Exception:
            pass
    return data


def _tag_local(tag: str) -> str:
    """Strip namespace prefix from an ElementTree tag."""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_xml(data: bytes) -> Optional[ET.Element]:
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        return None


def _parse_urlset(root: ET.Element, sitemap_url: str) -> List[SitemapUrl]:
    urls: List[SitemapUrl] = []
    for url_el in root:
        if _tag_local(url_el.tag) != "url":
            continue
        loc = None
        lastmod = changefreq = None
        priority = None
        for child in url_el:
            t = _tag_local(child.tag)
            if t == "loc":
                loc = (child.text or "").strip()
            elif t == "lastmod":
                lastmod = (child.text or "").strip() or None
            elif t == "changefreq":
                changefreq = (child.text or "").strip() or None
            elif t == "priority":
                try:
                    priority = float((child.text or "").strip())
                except ValueError:
                    pass
        if loc:
            urls.append(
                SitemapUrl(
                    loc=loc,
                    lastmod=lastmod,
                    changefreq=changefreq,
                    priority=priority,
                    source_sitemap=sitemap_url,
                )
            )
    return urls


def _parse_sitemapindex(root: ET.Element) -> List[str]:
    locs: List[str] = []
    for sm_el in root:
        if _tag_local(sm_el.tag) != "sitemap":
            continue
        for child in sm_el:
            if _tag_local(child.tag) == "loc":
                loc = (child.text or "").strip()
                if loc:
                    locs.append(loc)
    return locs


def fetch_sitemaps(
    urls: Sequence[str],
    session: "CloudflareSession",
    *,
    timeout: float = 30.0,
    max_sitemaps: int = _DEFAULT_MAX_SITEMAPS,
    max_urls: int = _DEFAULT_MAX_URLS,
) -> List[Sitemap]:
    """Fetch and parse a list of sitemap URLs (BFS, bounded).

    Args:
        urls:         Initial sitemap URLs to fetch.
        session:      The transport session to use.
        timeout:      Per-request timeout in seconds.
        max_sitemaps: Maximum number of sitemap documents to fetch in total.
        max_urls:     Stop collecting ``SitemapUrl`` entries after this many.

    Returns:
        List of :class:`Sitemap` objects (one per fetched document).
    """
    queue = list(urls)
    visited: set = set()
    results: List[Sitemap] = []
    total_urls = 0

    while queue and len(visited) < max_sitemaps and total_urls < max_urls:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        sm = Sitemap(url=url)
        try:
            raw = _fetch_bytes(url, session, timeout)
            data = _decompress(raw, url)
            root = _parse_xml(data)
            if root is None:
                sm.error = "XML parse error"
                results.append(sm)
                continue
            root_tag = _tag_local(root.tag)
            if root_tag == "sitemapindex":
                sm.is_index = True
                child_locs = _parse_sitemapindex(root)
                sm.child_sitemaps = child_locs
                # Enqueue children (respecting the cap).
                for loc in child_locs:
                    if loc not in visited and len(visited) + len(queue) < max_sitemaps:
                        queue.append(loc)
            elif root_tag == "urlset":
                parsed = _parse_urlset(root, url)
                remaining = max_urls - total_urls
                sm.urls = parsed[:remaining]
                total_urls += len(sm.urls)
            else:
                sm.error = f"unknown root element: {root_tag!r}"
        except Exception as exc:
            sm.error = str(exc)

        results.append(sm)

    return results
