"""Movie GM recommendation orchestration.

Combines the existing deterministic search/ranking primitives into explicit
recommendation modes. This layer does not perform provider/network calls or
persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from .free_movie_search import MovieCandidate, RankedMovie, rank_movies, split_current_and_upcoming
from .movie_gm_decision import HouseholdFit, ScoreBreakdown, ViewerProfile, breakdown, household_fit
from .movie_gm_profile import TasteProfile, WatchRecord, is_watched


@dataclass(frozen=True)
class MovieRecommendation:
    ranked: RankedMovie
    score: ScoreBreakdown
    household: HouseholdFit
    mode: str
    hidden_gem: bool = False
    hidden_gem_reason: str | None = None
    why: tuple[str, ...] = ()


@dataclass(frozen=True)
class MovieRecommendationResult:
    recommendations: tuple[MovieRecommendation, ...]
    upcoming: tuple[RankedMovie, ...] = ()
    suppressed_count: int = 0


def _hidden_gem_signal(result: RankedMovie, *, minimum_votes: int = 50000,
                       minimum_quality: float = 68.0,
                       minimum_confidence: float = 55.0) -> tuple[bool, str | None]:
    votes = result.movie.ratings.imdb_votes or 0
    if votes <= 0 or votes >= minimum_votes:
        return False, None
    if result.quality_score < minimum_quality or result.confidence < minimum_confidence:
        return False, None
    return True, f"Strong quality signal with a smaller IMDb audience ({votes:,} votes)"


def recommend_movies(
    movies: Sequence[MovieCandidate],
    *,
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
) -> MovieRecommendationResult:
    """Run the explicit Movie GM pipeline on already-normalized candidates.

    Modes:
      everyone: current accessible household catalog.
      kids: strict kids gate.
      tonight: current catalog, optionally bounded by runtime.
      hidden_gems: quality-first discovery among less-watched titles by vote volume.

    Unknown or unsupported modes fail closed.
    """
    normalized_mode = mode.casefold().strip()
    if normalized_mode not in {"everyone", "kids", "tonight", "hidden_gems"}:
        raise ValueError(f"Unsupported Movie GM mode: {mode}")

    kids_mode = normalized_mode == "kids"
    suppressed_count = sum(1 for movie in movies if is_watched(movie.title, watch_history)) if watch_history else 0
    ranked = rank_movies(
        movies,
        minimum_imdb=minimum_imdb,
        minimum_votes=minimum_votes,
        kids_mode=kids_mode,
        child_ages=child_ages,
        allow_pg13=allow_pg13,
        taste_profile=taste_profile,
        watch_history=watch_history,
        suppress_watched=True,
    )

    current = ranked
    upcoming: list[RankedMovie] = []
    if as_of:
        current, upcoming = split_current_and_upcoming(ranked, as_of=as_of, days=30)

    if normalized_mode == "tonight" and runtime_max is not None:
        current = [r for r in current if r.movie.runtime_minutes is not None and r.movie.runtime_minutes <= runtime_max]

    recommendations: list[MovieRecommendation] = []
    for result in current:
        household = household_fit(
            title=result.movie.title,
            genres=result.movie.genres,
            runtime_minutes=result.movie.runtime_minutes,
            viewers=viewers,
        )
        taste = result.personal_fit_score if taste_profile is not None else 50.0
        household_score = household.score if viewers else taste
        score = breakdown(
            quality=result.quality_score,
            taste=taste,
            household=household_score,
            availability=result.availability_confidence,
        )
        hidden, hidden_reason = _hidden_gem_signal(
            result,
            minimum_votes=hidden_gem_max_votes,
            minimum_quality=hidden_gem_min_quality,
        )
        if normalized_mode == "hidden_gems" and not hidden:
            continue

        why = list(score.reasons)
        why.extend(household.reasons)
        if hidden_reason:
            why.append(hidden_reason)
        if result.movie.runtime_minutes:
            why.append(f"Runtime: {result.movie.runtime_minutes} minutes")
        recommendations.append(MovieRecommendation(
            ranked=result,
            score=score,
            household=household,
            mode=normalized_mode,
            hidden_gem=hidden,
            hidden_gem_reason=hidden_reason,
            why=tuple(why),
        ))

    recommendations.sort(
        key=lambda r: (
            r.score.final,
            r.ranked.quality_score,
            r.ranked.availability_confidence,
            r.ranked.movie.title.casefold(),
        ),
        reverse=True,
    )
    if normalized_mode == "hidden_gems":
        recommendations.sort(
            key=lambda r: (
                r.score.final,
                r.ranked.quality_score,
                -(r.ranked.movie.ratings.imdb_votes or 0),
                r.ranked.movie.title.casefold(),
            ),
            reverse=True,
        )

    return MovieRecommendationResult(
        recommendations=tuple(recommendations),
        upcoming=tuple(upcoming),
        suppressed_count=suppressed_count,
    )
