"""Provider integration boundary for Movie GM.

This module owns orchestration around provider adapters. Adapters perform actual
network/provider work and return normalized MovieCandidate records. The GM
decision code remains deterministic and never performs network calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .free_movie_search import MovieCandidate
from .movie_gm_decision import ViewerProfile
from .movie_gm_profile import TasteProfile, WatchRecord
from .movie_gm_recommender import MovieRecommendationResult, recommend_movies


@dataclass(frozen=True)
class ProviderBatch:
    provider: str
    movies: tuple[MovieCandidate, ...] = ()
    status: str = "OK"
    reason: str = ""
    checked_at: str = ""
    source: str = ""


class MovieEvidenceEnricher(Protocol):
    provider: str

    def enrich(self, movie: MovieCandidate) -> MovieCandidate:
        """Add independent evidence without changing availability offers."""


class MovieSourceAdapter(Protocol):
    provider: str

    def discover(self, *, query: str = "", as_of: str | None = None) -> ProviderBatch:
        """Discover and normalize provider evidence into MovieCandidate records."""


@dataclass(frozen=True)
class MoviePipelineResult:
    recommendation: MovieRecommendationResult
    providers_checked: tuple[str, ...]
    providers_unavailable: tuple[tuple[str, str], ...]
    total_candidates: int


def _dedupe_movies(movies: Sequence[MovieCandidate]) -> tuple[MovieCandidate, ...]:
    seen: set[tuple[str, int | None]] = set()
    output: list[MovieCandidate] = []
    for movie in movies:
        key = (" ".join(movie.title.casefold().split()), movie.year)
        if key in seen:
            continue
        seen.add(key)
        output.append(movie)
    return tuple(output)


def run_movie_gm_pipeline(
    adapters: Sequence[MovieSourceAdapter],
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
    hidden_gem_max_votes: int = 50000,
    hidden_gem_min_quality: float = 68.0,
    rating_enrichers: Sequence[MovieEvidenceEnricher] = (),
    rating_enrichment_limit: int = 25,
) -> MoviePipelineResult:
    """Run all supplied provider adapters, then hand normalized evidence to GM.

    Provider failures are retained as UNAVAILABLE metadata and never converted
    into an empty NO_MATCH result. Duplicate titles are removed only after
    normalization, using title + year as the stable local key.
    """
    candidates: list[MovieCandidate] = []
    checked: list[str] = []
    unavailable: list[tuple[str, str]] = []

    for adapter in adapters:
        provider = getattr(adapter, "provider", adapter.__class__.__name__)
        try:
            batch = adapter.discover(query=query, as_of=as_of)
        except Exception as exc:
            unavailable.append((provider, f"UNAVAILABLE: {exc.__class__.__name__}"))
            continue
        checked.append(provider)
        if batch.status.casefold() != "ok":
            unavailable.append((provider, batch.reason or f"UNAVAILABLE: {batch.status}"))
            continue
        candidates.extend(batch.movies)

    unique = _dedupe_movies(candidates)

    # Discovery remains uncapped. Free external rating APIs can have daily
    # quotas, so enrichment is a separate, explicit evidence budget. We select
    # candidates using the existing deterministic GM ordering, enrich that set,
    # then run the final recommendation pass with the added evidence.
    if rating_enrichers and unique and rating_enrichment_limit > 0:
        preview = recommend_movies(
            unique,
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
            hidden_gem_max_votes=hidden_gem_max_votes,
            hidden_gem_min_quality=hidden_gem_min_quality,
        )
        selected_titles = {(item.ranked.movie.title.casefold(), item.ranked.movie.year) for item in preview.recommendations[:rating_enrichment_limit]}
        enriched = []
        for movie in unique:
            key = (movie.title.casefold(), movie.year)
            if key in selected_titles:
                current = movie
                for enricher in rating_enrichers:
                    try:
                        current = enricher.enrich(current)
                    except Exception as exc:
                        unavailable.append((getattr(enricher, "provider", enricher.__class__.__name__), f"UNAVAILABLE: {exc.__class__.__name__}"))
                        break
                enriched.append(current)
            else:
                enriched.append(movie)
        unique = tuple(enriched)

    recommendation = recommend_movies(
        unique,
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
        hidden_gem_max_votes=hidden_gem_max_votes,
        hidden_gem_min_quality=hidden_gem_min_quality,
    )
    return MoviePipelineResult(
        recommendation=recommendation,
        providers_checked=tuple(checked),
        providers_unavailable=tuple(unavailable),
        total_candidates=len(unique),
    )
