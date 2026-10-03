"""Tests for the live Movie GM runtime adapter factory."""
from __future__ import annotations

from modules.free_movie_search.movie_gm_runtime import RuntimeConfig, build_movie_adapters


def test_runtime_factory_fails_closed_without_tmdb_token(monkeypatch):
    monkeypatch.delenv("TMDB_READ_ACCESS_TOKEN", raising=False)
    adapters = build_movie_adapters()
    assert len(adapters) == 1
    assert adapters[0].provider == "TMDB/JustWatch"


def test_runtime_factory_builds_tmdb_when_token_exists(monkeypatch):
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "test-token")
    adapters = build_movie_adapters()
    assert len(adapters) == 1
    assert adapters[0].provider == "TMDB/JustWatch"


def test_runtime_factory_can_disable_tmdb(monkeypatch):
    monkeypatch.setenv("TMDB_READ_ACCESS_TOKEN", "test-token")
    assert build_movie_adapters(RuntimeConfig(include_tmdb=False)) == ()
