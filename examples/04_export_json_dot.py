"""Example 04 — export the link graph to JSON and Graphviz DOT.

Crawls a small site and writes:
- ``graph.json``  — full node + edge data
- ``graph.dot``   — Graphviz digraph (render with ``dot -Tsvg graph.dot``)

Run::

    python examples/04_export_json_dot.py
"""
from sitemapper import crawl


def main() -> None:
    graph = crawl(
        "https://www.python.org",
        max_pages=20,
        max_depth=1,
        delay=1.0,
    )

    with open("graph.json", "w") as fh:
        fh.write(graph.to_json(indent=2))
    print("Wrote graph.json")

    with open("graph.dot", "w") as fh:
        fh.write(graph.to_dot())
    print("Wrote graph.dot  (render: dot -Tsvg graph.dot -o graph.svg)")


if __name__ == "__main__":
    main()
