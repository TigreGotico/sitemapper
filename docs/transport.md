# Transport

All HTTP goes through `unblock_requests.CloudflareSession` (env prefix
`SITEMAPPER`) so recon works on Cloudflare-fronted sites.

## Environment variables

| Variable                           | Description |
|------------------------------------|-------------|
| `SITEMAPPER_FLARESOLVERR_URL`      | FlareSolverr base URL, e.g. `http://localhost:8191`. |
| `SITEMAPPER_FLARESOLVERR_FALLBACK` | `1` — escalate blocked GETs to the solver; keep curl_cffi as the fast path. |
| `SITEMAPPER_WAYBACK_FALLBACK`      | `1` — fall back to the Wayback Machine on failure. |
| `SITEMAPPER_TRANSPORT`             | Force a mode: `requests` / `curl_cffi` / `wayback` / `flaresolverr`. |

## Programmatic configuration

```python
from sitemapper import Sitemapper

sm = Sitemapper(
    flaresolverr_url="http://localhost:8191",
    flaresolverr_fallback=True,
    wayback_fallback=True,
    timeout=60.0,
)
```

Or set the solver URL only for the CLI:

```bash
python -m sitemapper https://example.com --flaresolverr http://localhost:8191
```

## Low-level access

```python
from sitemapper.transport import make_session
session = make_session(flaresolverr_url="http://localhost:8191")
# session is a CloudflareSession — use it like requests.Session
resp = session.get("https://example.com", timeout=30)
```
