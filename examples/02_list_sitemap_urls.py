"""Example 02 — list URLs from the sitemaps.

Iterates over every URL collected across all sitemap documents and prints
a TSV of loc, lastmod, changefreq, priority.

Run::

    python examples/02_list_sitemap_urls.py
"""
from sitemapper import discover


def main() -> None:
    info = discover("https://www.python.org")
    print(f"{'loc':<60} {'lastmod':<12} {'changefreq':<12} {'priority'}")
    print("-" * 100)
    for u in info.urls[:30]:
        print(f"{u.loc:<60} {u.lastmod or '':<12} {u.changefreq or '':<12} {u.priority or ''}")
    if info.url_count > 30:
        print(f"... and {info.url_count - 30} more.")


if __name__ == "__main__":
    main()
