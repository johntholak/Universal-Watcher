"""Secure live Movie GM runtime entry point.

Provider credentials are read only from environment variables. Missing credentials
fail closed and are reported through the pipeline's provider status.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .movie_gm_pipeline import MoviePipelineResult, ProviderBatch, run_movie_gm_pipeline_async
from .movie_gm_profile import TasteProfile, WatchRecord
from .movie_gm_decision import ViewerProfile
from .tmdb_movie_adapter import TMDBConfig, TMDBMovieAdapter
from .omdb_rating_adapter import OMDbConfig, OMDbRatingAdapter


@dataclass(frozen=True)
class RuntimeConfig:
    include_tmdb: bool = True
    include_omdb: bool = True
    rating_enrichment_limit: int = 20
    tmdb_token: str | None = None
    omdb_api_key: str | None = None


class _UnavailableAdapter:
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason

    def discover(self, *, query: str = "", as_of: str | None = None) -> ProviderBatch:
        return ProviderBatch(provider=self.provider, status="UNAVAILABLE", reason=self.reason)


def build_movie_adapters(config: RuntimeConfig | None = None):
    config = config or RuntimeConfig()
    adapters = []
    if config.include_tmdb:
        token = (config.tmdb_token or os.getenv("TMDB_READ_ACCESS_TOKEN", "")).strip()
        if token:
            adapters.append(TMDBMovieAdapter(TMDBConfig(token=token)))
        else:
            adapters.append(_UnavailableAdapter("TMDB/JustWatch", "TMDB_READ_ACCESS_TOKEN is not configured"))
    return tuple(adapters)


def build_movie_rating_enrichers(config: RuntimeConfig | None = None):
    config = config or RuntimeConfig()
    if not config.include_omdb:
        return ()
    key = (config.omdb_api_key or os.getenv("OMDB_API_KEY", "")).strip()
    if not key:
        return ()
    return (OMDbRatingAdapter(OMDbConfig(api_key=key)),)


async def run_live_movie_gm(
    *,
    query: str = "",
    mode: str = "everyone",
    as_of: str | None = None,
    taste_profile: TasteProfile | None = None,
    viewers: tuple[ViewerProfile, ...] = (),
    watch_history: tuple[WatchRecord, ...] = (),
    child_ages: tuple[int, ...] = (),
    allow_pg13: bool = True,
    runtime_max: int | None = None,
    minimum_imdb: float | None = None,
    minimum_votes: int | None = None,
    config: RuntimeConfig | None = None,
) -> MoviePipelineResult:
    config = config or RuntimeConfig()
    return await run_movie_gm_pipeline_async(
        build_movie_adapters(config),
        query=query,
        mode=mode,
        as_of=as_of,
        taste_profile=taste_profile,
        viewers=viewers,
        watch_history=watch_history,
        child_ages=child_ages,
        allow_pg13=allow_pg13,
        runtime_max=runtime_max,
        minimum_imdb=minimum_imdb,
        minimum_votes=minimum_votes,
        rating_enrichers=build_movie_rating_enrichers(config),
        rating_enrichment_limit=config.rating_enrichment_limit,
    )
