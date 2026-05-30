"""Example 03 — crawl a site and print the link-graph summary.

Performs a bounded BFS crawl (max 50 pages, depth 2) starting from the
given URL, extracts all internal and external links, and prints a
human-readable summary of the resulting graph.

Run::

    python examples/03_crawl_graph_summary.py
"""
from sitemapper import crawl


def main() -> None:
    graph = crawl(
        "https://www.python.org",
        max_pages=50,
        max_depth=2,
        delay=1.0,
    )
    print(graph.summary())
    print()
    print("Top 10 internal pages by out-degree:")
    out_deg = {url: len(dsts) for url, dsts in graph.adjacency.items()}
    for url, deg in sorted(out_deg.items(), key=lambda x: -x[1])[:10]:
        node = graph.nodes.get(url)
        title = (node.title or "")[:40] if node else ""
        print(f"  {deg:4d} links  {url[:60]}  ({title})")


if __name__ == "__main__":
    main()
