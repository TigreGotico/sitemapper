"""Link graph built by the crawler.

No third-party graph library is used — the adjacency structure is a plain
``dict[str, set[str]]`` and node metadata lives in ``dict[str, Node]``.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class Node:
    """Metadata for one URL seen during a crawl."""

    url: str
    internal: bool = True
    depth: int = 0
    status: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "internal": self.internal,
            "depth": self.depth,
            "status": self.status,
            "content_type": self.content_type,
            "title": self.title,
            "out_degree": 0,  # filled by LinkGraph.to_dict()
            "in_degree": 0,
        }


class LinkGraph:
    """Directed link graph produced by :func:`sitemapper.crawl`.

    Attributes:
        nodes:     Mapping from URL to :class:`Node`.
        adjacency: ``{src_url: {dst_url, ...}}`` for all observed edges.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.adjacency: Dict[str, Set[str]] = {}

    # -- construction helpers ------------------------------------------------

    def add_node(self, node: Node) -> None:
        if node.url not in self.nodes:
            self.nodes[node.url] = node
        if node.url not in self.adjacency:
            self.adjacency[node.url] = set()

    def add_edge(self, src: str, dst: str) -> None:
        self.adjacency.setdefault(src, set()).add(dst)

    # -- read interface ------------------------------------------------------

    @property
    def internal(self) -> Set[str]:
        """Set of internal URLs."""
        return {u for u, n in self.nodes.items() if n.internal}

    @property
    def external(self) -> Set[str]:
        """Set of external URLs seen as link targets."""
        return {u for u, n in self.nodes.items() if not n.internal}

    def edges(self) -> Iterator[Tuple[str, str]]:
        """Yield ``(src, dst)`` for every edge."""
        for src, dsts in self.adjacency.items():
            for dst in dsts:
                yield src, dst

    def domains(self) -> Dict[str, int]:
        """Return a ``{host: link_count}`` mapping for outgoing external links."""
        counts: Counter = Counter()
        for src, dsts in self.adjacency.items():
            for dst in dsts:
                node = self.nodes.get(dst)
                if node and not node.internal:
                    host = urlparse(dst).netloc
                    if host:
                        counts[host] += 1
        return dict(counts.most_common())

    def _in_degree(self, url: str) -> int:
        count = 0
        for dsts in self.adjacency.values():
            if url in dsts:
                count += 1
        return count

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        out_deg = {u: len(dsts) for u, dsts in self.adjacency.items()}
        # build in-degree
        in_deg: Dict[str, int] = {u: 0 for u in self.nodes}
        for dsts in self.adjacency.values():
            for dst in dsts:
                in_deg[dst] = in_deg.get(dst, 0) + 1

        nodes_out = {}
        for url, node in self.nodes.items():
            d = node.to_dict()
            d["out_degree"] = out_deg.get(url, 0)
            d["in_degree"] = in_deg.get(url, 0)
            nodes_out[url] = d

        return {
            "nodes": nodes_out,
            "edges": [{"src": s, "dst": d} for s, d in self.edges()],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_dot(self) -> str:
        """Return a Graphviz ``digraph`` string."""
        lines = ["digraph sitemapper {", '    rankdir="LR";']
        for url, node in self.nodes.items():
            label = (node.title or url)[:60].replace('"', "'")
            color = "lightblue" if node.internal else "lightyellow"
            lines.append(f'    "{url}" [label="{label}" style=filled fillcolor={color}];')
        for src, dst in self.edges():
            lines.append(f'    "{src}" -> "{dst}";')
        lines.append("}")
        return "\n".join(lines)

    def summary(self) -> str:
        """Return a human-readable summary string."""
        internal_fetched = [n for n in self.nodes.values() if n.internal and n.status is not None]
        depths = [n.depth for n in internal_fetched] or [0]
        max_depth = max(depths)

        # orphans: internal nodes with in-degree 0 (excluding the seed)
        in_deg: Dict[str, int] = {u: 0 for u in self.nodes}
        for dsts in self.adjacency.values():
            for dst in dsts:
                in_deg[dst] = in_deg.get(dst, 0) + 1

        orphans = [u for u in self.internal if in_deg.get(u, 0) == 0]
        top_ext = list(self.domains().items())[:5]
        ext_str = ", ".join(f"{h} ({c})" for h, c in top_ext) if top_ext else "none"

        lines = [
            f"Pages crawled (internal): {len(internal_fetched)}",
            f"Total internal URLs seen: {len(self.internal)}",
            f"External URLs seen: {len(self.external)}",
            f"Max depth reached: {max_depth}",
            f"Orphan pages (no inbound links): {len(orphans)}",
            f"Top external domains: {ext_str}",
        ]
        return "\n".join(lines)
