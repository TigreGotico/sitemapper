# Site survey — sitemapper against real scraper targets

A validation run of `sitemapper.discover()` across a representative spread of the
sources our client libraries scrape, plus one `crawl()` graph demo. It confirms
the tool works end to end (including on Cloudflare-fronted sites via the
`unblock_requests` transport) and doubles as recon: it shows **which targets
expose a sitemap we can consume directly instead of scraping**.

Run with the solver fallback enabled (`SITEMAPPER_FLARESOLVERR_URL` +
`SITEMAPPER_FLARESOLVERR_FALLBACK=1`) so the fast `curl_cffi` path is used by
default and only blocked requests escalate to FlareSolverr.

## discover() results

| Client | Site | robots | Declared sitemaps | Crawl-delay | Sitemap URLs | Verdict |
|---|---|---|---|---|---|---|
| pymusicbrainz | musicbrainz.org | ✅ | 1 | 2 s | **10,000+** (capped) | **rich sitemap** |
| pydiscogs | discogs.com | ✅ | 10 | 2 s | **~10,000** (capped) | **rich sitemap** (CF) |
| pypsychonaut | psychonautwiki.org | ✅ | 1 | — | **10,000+** (capped) | **rich sitemap** |
| pyvndb | vndb.org | ✅ | 0 | 10 s | 0 | no sitemap |
| pyrateyourmusic | rateyourmusic.com | ✅ | 0 | 5 s | 0 | no sitemap (heavy CF) |
| pyromhacking | romhacking.net | ✅ | 0 | — | 0 | no sitemap (CF) |
| pytvtropes | tvtropes.org | ✅ | 0 | — | 0 | no sitemap (CF) |
| pytcrf | tcrf.net | ✅ | 0 | 10 s | 0 | no sitemap (MediaWiki) |
| pysmwcentral | smwcentral.net | ✅ | 0 | — | 0 | no sitemap |
| pyimdb | imdb.com | ✅ | 0 | — | 0 | no sitemap surfaced (Akamai pages) |
| pyportaldalingua | portaldalinguaportuguesa.org | ✅ (29 B) | 0 | 3 s | 0 | no sitemap |
| pyeurobabe | eurobabeindex.com | ✅ (34 B) | 0 | — | 0 | no sitemap (catalogue = per-letter HTML) |
| pywikifeet | wikifeet.com | ✅ | 0 | — | 0 | no enumerable index |
| pyerowid | erowid.org | ⚠️ block page | 0 | — | 0 | soft-403 block (see limitations) |

## crawl() graph demo

A bounded crawl of `psychonautwiki.org` (`max_pages=10, max_depth=1`):

```
Pages crawled (internal): 10
Total internal URLs seen: 1716
External URLs seen: 849
Max depth reached: 1
Orphan pages (no inbound links): 1
Top external domains: en.wikipedia.org (206), www.youtube.com (198),
                      archive.org (62), www.discogs.com (44), www.imdb.com (38)
```

The graph (nodes, adjacency, internal/external split, `domains()`) builds
correctly from 10 fetched pages — including outgoing-link mapping.

## Findings

- **Three targets expose rich sitemaps**: musicbrainz, discogs, psychonautwiki.
  All three hit the default `max_urls=10000` cap, so each holds **more** — raise
  the cap to enumerate fully. These are candidates to **seed or replace** crawl
  logic with direct sitemap consumption.
- **Cloudflare did not block recon**: discogs and rateyourmusic both returned
  `robots.txt` (and discogs its sitemaps) over the fast `curl_cffi` path — CDNs
  serve `robots.txt`/sitemaps without a JS challenge. The solver fallback is in
  reserve for the rare endpoint that does challenge.
- **Most targets have no sitemap** — confirming that scraping / API-RE is the
  correct approach for them. Notably it **confirms empirically** that WikiFeet
  has no enumerable index and that eurobabeindex publishes no sitemap (its
  catalogue lives in per-letter HTML index pages).
- **`crawl_delay` is surfaced** where declared (vndb 10 s, rateyourmusic 5 s,
  musicbrainz/discogs 2 s, tcrf 10 s, portaldalingua 3 s) — politeness budgets
  to honour when scraping.

## Limitations surfaced

- **Site-specific soft blocks aren't detected.** erowid.org answers a datacenter
  IP with an HTTP **200** body titled *"403 - Blocked"*; sitemapper fetched that
  block page and parsed it as `robots.txt` (hence `robots ✅` but it is junk).
  This is the same class of soft block `pyerowid` handles via a Wayback
  fallback. Candidate enhancement: a `is_block_page()` heuristic + Wayback/solver
  retry, mirroring the client.
- **URL collection is capped** at `max_urls` (default 10,000); sitemaps larger
  than that are truncated. Raise the limit for full enumeration.
- `discover()` always attempts the conventional `/sitemap.xml`; rely on
  `url_count` / `robots.sitemaps` (not the raw sitemap-object count) to judge
  whether a usable sitemap exists.

## Recommendation

Run `sitemapper.discover(<site>)` as **step one** when building or revisiting any
scraper. For musicbrainz / discogs / psychonautwiki, prefer the sitemap as a URL
source; for the rest, recon confirms there is no shortcut and scraping/RE stands.
