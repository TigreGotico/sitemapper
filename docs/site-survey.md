# Site survey: sitemapper against real scraper targets

A validation run of `sitemapper.discover()` across a representative spread of
the sources our client libraries scrape, plus one `crawl()` graph demo. It
confirms the tool works end to end, including on Cloudflare-fronted sites via
the `unblock_requests` transport. It also doubles as recon: it shows which
targets expose a sitemap we can consume directly instead of scraping.

Run with the solver fallback enabled (`SITEMAPPER_FLARESOLVERR_URL` and
`SITEMAPPER_FLARESOLVERR_FALLBACK=1`) so the fast `curl_cffi` path is used by
default. Only blocked requests escalate to FlareSolverr.

## discover() results

| Client | Site | robots | Declared sitemaps | Crawl-delay | Sitemap URLs | Verdict |
|---|---|---|---|---|---|---|
| pymusicbrainz | musicbrainz.org | yes | 1 | 2 s | 10,000+ (capped) | rich sitemap |
| pydiscogs | discogs.com | yes | 10 | 2 s | ~10,000 (capped) | rich sitemap (CF) |
| pypsychonaut | psychonautwiki.org | yes | 1 | none | 10,000+ (capped) | rich sitemap |
| pyvndb | vndb.org | yes | 0 | 10 s | 0 | no sitemap |
| pyrateyourmusic | rateyourmusic.com | yes | 0 | 5 s | 0 | no sitemap (heavy CF) |
| pyromhacking | romhacking.net | yes | 0 | none | 0 | no sitemap (CF) |
| pytvtropes | tvtropes.org | yes | 0 | none | 0 | no sitemap (CF) |
| pytcrf | tcrf.net | yes | 0 | 10 s | 0 | no sitemap (MediaWiki) |
| pysmwcentral | smwcentral.net | yes | 0 | none | 0 | no sitemap |
| pyimdb | imdb.com | yes | 0 | none | 0 | no sitemap surfaced (Akamai pages) |
| pyportaldalingua | portaldalinguaportuguesa.org | yes (29 B) | 0 | 3 s | 0 | no sitemap |
| pyeurobabe | eurobabeindex.com | yes (34 B) | 0 | none | 0 | no sitemap (catalogue = per-letter HTML) |
| pywikifeet | wikifeet.com | yes | 0 | none | 0 | no enumerable index |
| pyerowid | erowid.org | block page | 0 | none | 0 | soft-403 block (see limitations) |

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
correctly from 10 fetched pages, including outgoing-link mapping.

## Findings

- Three targets expose rich sitemaps: musicbrainz, discogs, and
  psychonautwiki. All three hit the default `max_urls=10000` cap, so each
  holds more. Raise the cap to enumerate them fully. These targets are
  candidates to seed or replace crawl logic with direct sitemap consumption.

- Cloudflare did not block recon. Discogs and rateyourmusic both returned
  `robots.txt` (and discogs its sitemaps) over the fast `curl_cffi` path.
  CDNs serve `robots.txt` and sitemaps without a JS challenge. The solver
  fallback stays in reserve for the rare endpoint that does challenge.

- Most targets have no sitemap, confirming that scraping or API
  reverse-engineering is the correct approach for them. The run confirms that
  WikiFeet has no enumerable index and that eurobabeindex publishes no
  sitemap, since its catalogue lives in per-letter HTML index pages.

- `crawl_delay` is surfaced where declared: vndb 10 s, rateyourmusic 5 s,
  musicbrainz and discogs 2 s, tcrf 10 s, portaldalingua 3 s. These are
  politeness budgets to honor when scraping.

## Limitations surfaced

- Soft blocks are detected via title/body markers ("403 Forbidden", "Access
  Denied", "Permission Denied") and Cloudflare interstitials, but the
  heuristic covers only common WAF/CDN block pages. A block page that uses
  none of those markers is indistinguishable from real `robots.txt`
  content, so `discover()` may still report `robots: yes` with junk data.
  Callers that need certainty should inspect `SiteDiscovery.blocked` and,
  when detection misses a variant, add a Wayback or solver retry, mirroring
  the client.

- URL collection is capped at `max_urls` (default 10,000). Sitemaps larger
  than that are truncated. Raise the limit for full enumeration.

- `discover()` always attempts the conventional `/sitemap.xml`. Rely on
  `url_count` and `robots.sitemaps` (not the raw sitemap-object count) to
  judge whether a usable sitemap exists.

## Recommendation

Run `sitemapper.discover(<site>)` as the first step when building or
revisiting any scraper. For musicbrainz, discogs, and psychonautwiki, prefer
the sitemap as a URL source. For the rest, recon confirms there is no
shortcut, and scraping or reverse-engineering the API stands.

---
[← CLI](cli.md) · [Home](../README.md)
