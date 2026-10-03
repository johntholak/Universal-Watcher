"""Live runtime entry point for Movie GM.

Builds configured external adapters from runtime secrets without storing
credentials in source control. Missing credentials produce an empty adapter
set rather than crashing application startup.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from .movie_gm_pipeline import MoviePipelineResult, MovieSourceAdapter, run_movie_gm_pipeline
from .movie_gm_profile import TasteProfile, WatchRecord
from .movie_gm_decision import ViewerProfile
from .tmdb_movie_adapter import TMDBMovieAdapter


@dataclass(frozen=True)
class RuntimeConfig:
    include_tmdb: bool = True


def build_movie_adapters(config: RuntimeConfig | None = None) -> tuple[MovieSourceAdapter, ...]:
    """Build only adapters whose required runtime credentials are present."""
    config = config or RuntimeConfig()
    adapters: list[MovieSourceAdapter] = []
    if config.include_tmdb and os.getenv("TMDB_READ_ACCESS_TOKEN", "").strip():
        adapters.append(TMDBMovieAdapter())
    return tuple(adapters)


def run_live_movie_gm(
    *,
    query: str = "",
    mode: str = "everyone",
    as_of: str | None = None,
    taste_profile: TasteProfile | None = None,
    viewers: Sequence[ViewerProfile] = (),
    watch_history: Sequence[WatchRecord] = (),
    child_ages: Sequence[int] = (),
    allow_pg13: bool = True,
    runtime_max: int | None = None,
    minimum_imdb: float | None = None,
    minimum_votes: int | None = None,
) -> MoviePipelineResult:
    """Run Movie GM against all currently configured live sources."""
    return run_movie_gm_pipeline(
        build_movie_adapters(),
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
    )
