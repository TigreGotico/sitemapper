# sitemapper

Site-recon tooling for scraper development.  Given a base URL, discovers
site structure (robots.txt + sitemaps) and optionally crawls internal pages,
mapping internal and outgoing links into a graph.

## Quickstart

```bash
pip install sitemapper
pip install sitemapper[stealth]   # recommended: adds curl_cffi TLS impersonation
```

```python
from sitemapper import discover, crawl

# Passive — no HTML crawled.  Fetches robots.txt and all sitemaps.
info = discover("https://www.python.org")
print(info.summary())
# Base URL:         https://www.python.org
# Sitemaps found:   1
# URLs in sitemaps: 342
# Crawl-delay:      None

# Active — bounded BFS, builds a link graph.
graph = crawl("https://www.python.org", max_pages=50, max_depth=2)
print(graph.summary())
# Pages crawled (internal): 50
# External URLs seen: 87
# Top external domains: docs.python.org (23), ...
```

## Entry points

| Function / class    | Description |
|---------------------|-------------|
| `discover(url)`     | Passive discovery: robots.txt + sitemaps → `SiteDiscovery`. |
| `crawl(url)`        | Bounded BFS crawl → `LinkGraph`. |
| `Sitemapper`        | Stateful class; holds config, transport, and caches discovery results. |

## Transport

All HTTP goes through
[`unblock_requests.CloudflareSession`](https://github.com/TigreGotico/unblock_requests)
(env prefix `SITEMAPPER`), so recon works on Cloudflare-fronted sites.

```bash
export SITEMAPPER_FLARESOLVERR_URL=http://localhost:8191   # point at a running FlareSolverr
export SITEMAPPER_FLARESOLVERR_FALLBACK=1                  # escalate blocked GETs to solver
export SITEMAPPER_WAYBACK_FALLBACK=1                       # fall back to Wayback Machine
```

Or configure programmatically:

```python
from sitemapper import Sitemapper
sm = Sitemapper(flaresolverr_url="http://localhost:8191", wayback_fallback=True)
info = sm.discover("https://www.progarchives.com")
```

## CLI

```bash
# Passive discovery (default)
python -m sitemapper https://www.python.org

# Active crawl with export
python -m sitemapper https://www.python.org \
    --crawl --max-pages 50 --json graph.json --dot graph.dot

# Cloudflare-fronted site
python -m sitemapper https://example.com --flaresolverr http://localhost:8191
```

Full flag list: `python -m sitemapper --help`

## LinkGraph

`crawl()` returns a `LinkGraph` with no third-party dependencies (plain dict
adjacency):

```python
graph.nodes           # dict[str, Node]   — url, status, title, depth, ...
graph.internal        # set[str]
graph.external        # set[str]
graph.domains()       # {host: count}  outgoing external links
graph.to_json()
graph.to_dot()        # Graphviz digraph  (dot -Tsvg out.dot)
graph.summary()
```

## Docs

- [docs/quickstart.md](docs/quickstart.md)
- [docs/discovery.md](docs/discovery.md)
- [docs/crawl_graph.md](docs/crawl_graph.md)
- [docs/transport.md](docs/transport.md)
- [docs/cli.md](docs/cli.md)
