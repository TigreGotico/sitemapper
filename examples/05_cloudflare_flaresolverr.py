"""Example 05 — recon a Cloudflare-fronted site via FlareSolverr.

``sitemapper`` routes all HTTP through :class:`unblock_requests.CloudflareSession`.
For sites protected by Cloudflare's JS challenge you can point it at a running
FlareSolverr instance so the challenge is solved in a real browser.

Requirements:
    docker run -d --name flaresolverr -p 8191:8191 ghcr.io/flaresolverr/flaresolverr

Run::

    python examples/05_cloudflare_flaresolverr.py

The ``SITEMAPPER_FLARESOLVERR_URL`` env var is equivalent to the
``flaresolverr_url`` kwarg.
"""
import os
from sitemapper import Sitemapper


def main() -> None:
    # Configure FlareSolverr via env or the kwarg below.
    fs_url = os.environ.get("SITEMAPPER_FLARESOLVERR_URL", "http://localhost:8191")

    sm = Sitemapper(
        flaresolverr_url=fs_url,
        flaresolverr_fallback=True,   # fast curl_cffi path first; solver on block
        wayback_fallback=True,         # fall back to the Wayback Machine if everything fails
        timeout=60.0,
    )

    # Passive discovery — no HTML crawled.
    info = sm.discover("https://www.progarchives.com")
    print(info.summary())

    # Active crawl.
    # graph = sm.crawl("https://www.progarchives.com", max_pages=10, max_depth=1)
    # print(graph.summary())


if __name__ == "__main__":
    main()
