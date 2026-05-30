"""Example 01 — passively discover a site's structure.

Fetches robots.txt and all sitemaps listed there (plus /sitemap.xml) without
touching any HTML pages.  The result includes the crawl-delay and all URLs
declared in the sitemaps.

Run::

    python examples/01_discover_site.py
"""
from sitemapper import discover


def main() -> None:
    info = discover("https://www.python.org")
    print(info.summary())
    print()
    print(f"Robots.txt sitemaps listed: {info.robots.sitemaps}")
    print(f"Crawl-delay: {info.robots.crawl_delay}")
    print(f"Total sitemap documents fetched: {len(info.sitemaps)}")
    print(f"Total unique URLs in sitemaps: {info.url_count}")


if __name__ == "__main__":
    main()
