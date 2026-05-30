# Quickstart

## Install

```bash
pip install sitemapper
pip install sitemapper[stealth]   # recommended: adds curl_cffi for TLS impersonation
pip install sitemapper[anon]      # adds anon_requests for IP rotation
```

## Passive discovery (no crawl)

```python
from sitemapper import discover

info = discover("https://www.python.org")
print(info.summary())
# Sitemaps found: 1
# URLs in sitemaps: 342
# Crawl-delay: None
# ...
```

`discover()` fetches only robots.txt and the sitemaps listed there (plus
`/sitemap.xml`).  No HTML pages are touched.

## Active crawl

```python
from sitemapper import crawl

graph = crawl("https://www.python.org", max_pages=50, max_depth=2)
print(graph.summary())
```

## CLI

```bash
# Passive discovery:
python -m sitemapper https://www.python.org

# Crawl and export:
python -m sitemapper https://www.python.org --crawl --max-pages 50 --json out.json --dot out.dot
```
