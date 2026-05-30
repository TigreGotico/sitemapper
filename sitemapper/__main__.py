"""CLI entry point: ``python -m sitemapper <url> [options]``."""
from __future__ import annotations

import argparse
import json
import os
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m sitemapper",
        description=(
            "Site-recon tooling: discover robots.txt + sitemaps (passive), "
            "or crawl internal pages into a link graph (active)."
        ),
    )
    p.add_argument("url", help="Base URL to recon (e.g. https://example.com)")
    p.add_argument(
        "--crawl", action="store_true",
        help="Enable BFS crawl; default is passive discovery only.",
    )
    p.add_argument("--max-pages", type=int, default=200, metavar="N",
                   help="Max internal pages to fetch during crawl (default 200).")
    p.add_argument("--max-depth", type=int, default=3, metavar="N",
                   help="Max BFS depth during crawl (default 3).")
    p.add_argument("--same-domain", default=True, action="store_true",
                   help="Restrict crawl to same host (default on).")
    p.add_argument("--no-same-domain", dest="same_domain", action="store_false",
                   help="Allow crawling across sub-domains.")
    p.add_argument("--json", metavar="FILE",
                   help="Write JSON output to FILE.")
    p.add_argument("--dot", metavar="FILE",
                   help="Write Graphviz DOT output to FILE (requires --crawl).")
    p.add_argument("--flaresolverr", metavar="URL",
                   help="FlareSolverr base URL (e.g. http://localhost:8191).")
    p.add_argument("--timeout", type=float, default=30.0,
                   help="Per-request timeout in seconds (default 30).")
    return p


def main(argv=None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Respect --flaresolverr on the command line (takes priority over env).
    if args.flaresolverr:
        os.environ["SITEMAPPER_FLARESOLVERR_URL"] = args.flaresolverr

    from sitemapper.sitemapper import Sitemapper

    sm = Sitemapper(timeout=args.timeout)

    if not args.crawl:
        info = sm.discover(args.url)
        print(info.summary())
        if args.json:
            with open(args.json, "w") as fh:
                json.dump(info.to_dict(), fh, indent=2)
            print(f"\nJSON written to {args.json}")
    else:
        graph = sm.crawl(
            args.url,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            same_domain=args.same_domain,
        )
        print(graph.summary())
        if args.json:
            with open(args.json, "w") as fh:
                fh.write(graph.to_json())
            print(f"\nJSON written to {args.json}")
        if args.dot:
            with open(args.dot, "w") as fh:
                fh.write(graph.to_dot())
            print(f"DOT written to {args.dot}")


if __name__ == "__main__":
    main()
