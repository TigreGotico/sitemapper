"""robots.txt parser.

Parses ``robots.txt`` including ``Sitemap:`` directives and ``Crawl-delay``,
which :mod:`urllib.robotparser` does not expose.  ``is_allowed()`` delegates to
:class:`urllib.robotparser.RobotFileParser` for correctness.
"""
from __future__ import annotations

import re
import urllib.robotparser
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse


@dataclass
class RobotsGroup:
    """One ``User-agent`` block from robots.txt."""

    user_agents: List[str]
    allows: List[str] = field(default_factory=list)
    disallows: List[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None


@dataclass
class Robots:
    """Parsed representation of a robots.txt file.

    Attributes:
        sitemaps:    Sitemap URLs found in ``Sitemap:`` directives.
        crawl_delay: The first ``Crawl-delay`` value found (for ``*`` or the
                     only agent group), or ``None``.
        groups:      All ``User-agent`` blocks in document order.
        raw_text:    The raw robots.txt content (empty string if unreachable).
    """

    sitemaps: List[str] = field(default_factory=list)
    crawl_delay: Optional[float] = None
    groups: List[RobotsGroup] = field(default_factory=list)
    raw_text: str = ""

    # The stdlib parser handles is_allowed correctly.
    _rp: urllib.robotparser.RobotFileParser = field(
        default_factory=urllib.robotparser.RobotFileParser, repr=False, compare=False
    )

    def is_allowed(self, url_or_path: str, user_agent: str = "*") -> bool:
        """Return whether *user_agent* may fetch *url_or_path*.

        Delegates to :class:`urllib.robotparser.RobotFileParser`.  Always
        returns ``True`` when robots.txt was unreachable (empty *raw_text*).
        """
        return self._rp.can_fetch(user_agent, url_or_path)

    def to_dict(self) -> dict:
        return {
            "sitemaps": self.sitemaps,
            "crawl_delay": self.crawl_delay,
            "groups": [
                {
                    "user_agents": g.user_agents,
                    "allows": g.allows,
                    "disallows": g.disallows,
                    "crawl_delay": g.crawl_delay,
                }
                for g in self.groups
            ],
        }


def parse_robots(text: str, base_url: str = "") -> Robots:
    """Parse a robots.txt *text* string.

    Args:
        text:     The raw content of robots.txt.
        base_url: The URL the file was fetched from (used by the stdlib parser
                  to resolve absolute ``Sitemap:`` URLs — not strictly needed
                  but good practice).

    Returns:
        A populated :class:`Robots` instance.
    """
    sitemaps: List[str] = []
    crawl_delay: Optional[float] = None
    groups: List[RobotsGroup] = []

    current_agents: List[str] = []
    current_allows: List[str] = []
    current_disallows: List[str] = []
    current_delay: Optional[float] = None
    in_group = False

    def _flush():
        nonlocal in_group
        if current_agents:
            groups.append(
                RobotsGroup(
                    user_agents=list(current_agents),
                    allows=list(current_allows),
                    disallows=list(current_disallows),
                    crawl_delay=current_delay,
                )
            )
        current_agents.clear()
        current_allows.clear()
        current_disallows.clear()
        in_group = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            if in_group:
                _flush()
            continue
        if ":" not in line:
            continue
        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            if in_group and current_agents and not (current_allows or current_disallows or current_delay):
                # consecutive user-agent lines → add to current group
                current_agents.append(value)
            else:
                if in_group:
                    _flush()
                current_agents.append(value)
                in_group = True
        elif directive == "allow":
            current_allows.append(value)
        elif directive == "disallow":
            current_disallows.append(value)
        elif directive == "crawl-delay":
            try:
                delay = float(value)
                current_delay = delay
                if crawl_delay is None:
                    crawl_delay = delay
            except ValueError:
                pass
        elif directive == "sitemap":
            if value:
                sitemaps.append(value)

    if in_group:
        _flush()

    # Use stdlib for is_allowed (handles edge cases, anchoring, wildcards).
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(base_url or "")
    rp.parse(text.splitlines())

    return Robots(
        sitemaps=sitemaps,
        crawl_delay=crawl_delay,
        groups=groups,
        raw_text=text,
        _rp=rp,
    )
