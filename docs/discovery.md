# Discovery

`discover(base_url, *, timeout=30.0) -> SiteDiscovery` is the passive
entry point.  It fetches:

1. `robots.txt` — extracts `Sitemap:` directives, `Crawl-delay`, and
   `Disallow`/`Allow` rules.
2. All sitemap documents referenced in `robots.txt` plus the conventional
   `/sitemap.xml`.  Sitemapindex documents are recursed one level deep.
   Gzip-compressed sitemaps (`.gz`) are transparently decompressed.

No HTML pages are fetched.

## SiteDiscovery

```python
info.base_url       # str
info.robots         # Robots
info.sitemaps       # list[Sitemap]
info.urls           # list[SitemapUrl]  (deduplicated)
info.url_count      # int
info.summary()      # human-readable str
info.to_dict()      # JSON-serialisable dict
```

## Robots

```python
info.robots.sitemaps        # list[str] — Sitemap: directive URLs
info.robots.crawl_delay     # float | None
info.robots.is_allowed(url) # bool — delegates to urllib.robotparser
info.robots.groups          # list[RobotsGroup]
```

## Sitemap / SitemapUrl

```python
sm.url           # str
sm.is_index      # bool
sm.urls          # list[SitemapUrl]
sm.child_sitemaps  # list[str]  (for sitemapindex)

u.loc            # str
u.lastmod        # str | None
u.changefreq     # str | None
u.priority       # float | None
```

## Caps

Pass `max_sitemaps=` and `max_urls=` to `Sitemapper()` or `discover()` to
control runaway behaviour on very large sites.
