"""Offline tests for the transport factory (env-var fallback wiring)."""
from sitemapper.transport import make_session


def test_flaresolverr_url_env_fallback(monkeypatch):
    """SITEMAPPER_FLARESOLVERR_URL is honoured when the kwarg is omitted."""
    monkeypatch.setenv("SITEMAPPER_FLARESOLVERR_URL", "http://localhost:8191")
    s = make_session()
    assert s.flaresolverr_url == "http://localhost:8191"


def test_flaresolverr_url_kwarg_overrides_env(monkeypatch):
    """An explicit kwarg wins over the env var."""
    monkeypatch.setenv("SITEMAPPER_FLARESOLVERR_URL", "http://env:8191")
    s = make_session(flaresolverr_url="http://explicit:8191")
    assert s.flaresolverr_url == "http://explicit:8191"


def test_wayback_fallback_env_is_not_shadowed_by_a_hardcoded_default(monkeypatch):
    """Regression test: ``make_session`` used to default ``wayback_fallback``
    (and ``flaresolverr_fallback``) to a hardcoded ``True``, which always
    overrode the ``None`` sentinel ``CloudflareSession`` needs to consult its
    own ``SITEMAPPER_WAYBACK_FALLBACK`` / ``SITEMAPPER_FLARESOLVERR_FALLBACK``
    env vars — making those documented env vars dead code. Omitting the
    kwarg must let the underlying session read the env var."""
    monkeypatch.setenv("SITEMAPPER_FLARESOLVERR_URL", "http://localhost:8191")
    monkeypatch.setenv("SITEMAPPER_WAYBACK_FALLBACK", "0")
    monkeypatch.setenv("SITEMAPPER_FLARESOLVERR_FALLBACK", "0")
    s = make_session()
    assert s.wayback_fallback is None  # unset -> CloudflareSession reads the env lazily
    assert s._do_wayback_fallback() is False
    assert s._do_flaresolverr_fallback() is False

    monkeypatch.setenv("SITEMAPPER_WAYBACK_FALLBACK", "1")
    monkeypatch.setenv("SITEMAPPER_FLARESOLVERR_FALLBACK", "1")
    s = make_session()
    assert s._do_wayback_fallback() is True
    assert s._do_flaresolverr_fallback() is True


def test_wayback_fallback_kwarg_overrides_env(monkeypatch):
    """An explicit kwarg still wins over the env var."""
    monkeypatch.setenv("SITEMAPPER_WAYBACK_FALLBACK", "1")
    s = make_session(wayback_fallback=False)
    assert s._do_wayback_fallback() is False
