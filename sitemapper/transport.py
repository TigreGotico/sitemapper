"""Transport layer for sitemapper.

All HTTP is routed through :class:`unblock_requests.CloudflareSession` so
recon works on Cloudflare-fronted sites.  The session reads its configuration
from the ``SITEMAPPER_*`` env namespace:

    SITEMAPPER_FLARESOLVERR_URL       FlareSolverr base URL (e.g. http://localhost:8191)
    SITEMAPPER_FLARESOLVERR_FALLBACK  ``1`` to escalate blocked GETs to the solver
    SITEMAPPER_TRANSPORT              force a mode (requests/curl_cffi/wayback/flaresolverr)
    SITEMAPPER_WAYBACK_FALLBACK       ``1`` to fall back to the Wayback Machine on failure
"""
from __future__ import annotations

import os
from typing import Optional

from unblock_requests import CloudflareSession

_ENV_PREFIX = "SITEMAPPER"


def make_session(
    *,
    flaresolverr_url: Optional[str] = None,
    flaresolverr_fallback: bool = True,
    wayback_fallback: bool = True,
    timeout: float = 30.0,
) -> CloudflareSession:
    """Return a :class:`~unblock_requests.CloudflareSession` configured for
    sitemapper recon.

    Args:
        flaresolverr_url:      FlareSolverr base URL.  Overrides the env var
                               ``SITEMAPPER_FLARESOLVERR_URL``.
        flaresolverr_fallback: Escalate blocked GETs to FlareSolverr; keep
                               the fast curl-cffi path for normal requests.
        wayback_fallback:      Fall back to the Wayback Machine when the live
                               request fails completely.
        timeout:               Default socket timeout in seconds (unused by
                               the session itself but stored for callers).

    Returns:
        A ready-to-use :class:`~unblock_requests.CloudflareSession`.
    """
    fs_url = flaresolverr_url or os.environ.get(f"{_ENV_PREFIX}_FLARESOLVERR_URL")
    s = CloudflareSession(
        flaresolverr_url=fs_url,
        flaresolverr_fallback=flaresolverr_fallback,
        wayback_fallback=wayback_fallback,
        env_prefix=_ENV_PREFIX,
    )
    return s
