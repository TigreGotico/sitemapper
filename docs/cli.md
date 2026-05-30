# CLI reference

```
python -m sitemapper <url> [options]
```

## Arguments

| Argument / Flag        | Default | Description |
|------------------------|---------|-------------|
| `url`                  | —       | Base URL to recon. |
| `--crawl`              | off     | Enable BFS crawl; default is passive discovery. |
| `--max-pages N`        | 200     | Max internal pages to fetch during crawl. |
| `--max-depth N`        | 3       | Max BFS depth. |
| `--same-domain`        | on      | Restrict crawl to same host. |
| `--no-same-domain`     | off     | Allow crawling across sub-domains. |
| `--json FILE`          | —       | Write JSON output to FILE. |
| `--dot FILE`           | —       | Write Graphviz DOT to FILE (requires `--crawl`). |
| `--flaresolverr URL`   | —       | FlareSolverr base URL. |
| `--timeout SECONDS`    | 30.0    | Per-request timeout. |

## Examples

```bash
# Passive discovery — prints summary
python -m sitemapper https://www.python.org

# Crawl + export
python -m sitemapper https://www.python.org \
    --crawl --max-pages 50 --max-depth 2 \
    --json graph.json --dot graph.dot

# Use FlareSolverr for Cloudflare-protected sites
python -m sitemapper https://example.com \
    --flaresolverr http://localhost:8191
```
