"""Deterministic core for Universal Watcher's free movie search.

Provider adapters should feed normalized MovieCandidate records into this module.
No network access belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log10
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RatingEvidence:
    imdb: float | None = None
    imdb_votes: int | None = None
    rotten_tomatoes_critics: float | None = None
    rotten_tomatoes_audience: float | None = None
    metacritic: float | None = None


@dataclass(frozen=True)
class FreeOffer:
    provider: str
    watch_url: str | None
    access: str = "free_ads"
    checked_at: str = ""
    source: str = ""
    verified: bool = False


@dataclass(frozen=True)
class MovieCandidate:
    title: str
    year: int | None
    ratings: RatingEvidence
    offers: tuple[FreeOffer, ...]
    genres: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    age_rating: str | None = None
    personal_fit: float = 0.0
    taste_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RankedMovie:
    movie: MovieCandidate
    quality_score: float
    personal_fit_score: float
    combined_score: float
    confidence: float
    reasons: tuple[str, ...] = ()


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _bayesian_imdb(
    rating: float | None,
    votes: int | None,
    prior: float = 6.5,
    prior_votes: int = 5000,
) -> float | None:
    if rating is None:
        return None
    votes = max(0, votes or 0)
    return (
        (votes / (votes + prior_votes)) * rating
        + (prior_votes / (votes + prior_votes)) * prior
    )


def _rating_volume(votes: int | None) -> float:
    if not votes:
        return 0.0
    return _clamp((log10(max(votes, 1)) / 6.0) * 100.0)


def quality_score(ratings: RatingEvidence) -> tuple[float, float]:
    components: list[tuple[float, float]] = []

    imdb = _bayesian_imdb(ratings.imdb, ratings.imdb_votes)
    if imdb is not None:
        components.append((imdb * 10.0, 0.48))

    if ratings.rotten_tomatoes_critics is not None:
        components.append((_clamp(ratings.rotten_tomatoes_critics), 0.18))

    if ratings.rotten_tomatoes_audience is not None:
        components.append((_clamp(ratings.rotten_tomatoes_audience), 0.22))

    if ratings.metacritic is not None:
        components.append((_clamp(ratings.metacritic), 0.12))

    if not components:
        return 0.0, 0.0

    total_weight = sum(weight for _, weight in components)
    score = sum(value * weight for value, weight in components) / total_weight
    volume = _rating_volume(ratings.imdb_votes)
    confidence = min(100.0, (len(components) / 4.0) * 60.0 + volume * 0.40)
    return _clamp(score), _clamp(confidence)


def rank_movies(
    movies: Iterable[MovieCandidate],
    *,
    minimum_imdb: float | None = None,
    minimum_votes: int | None = None,
    allowed_genres: Sequence[str] = (),
    excluded_genres: Sequence[str] = (),
    preferred_providers: Sequence[str] = (),
    personal_fit_weight: float = 0.35,
) -> list[RankedMovie]:
    allowed = {g.casefold() for g in allowed_genres}
    excluded = {g.casefold() for g in excluded_genres}
    preferred = {p.casefold() for p in preferred_providers}

    results: list[RankedMovie] = []

    for movie in movies:
        verified_free = [
            offer for offer in movie.offers
            if offer.verified and offer.access in {"free_ads", "free"}
        ]
        if not verified_free:
            continue

        if minimum_imdb is not None:
            if movie.ratings.imdb is None or movie.ratings.imdb < minimum_imdb:
                continue

        if minimum_votes is not None:
            if (movie.ratings.imdb_votes or 0) < minimum_votes:
                continue

        genres = {g.casefold() for g in movie.genres}
        if allowed and not (genres & allowed):
            continue
        if excluded and genres & excluded:
            continue

        quality, confidence = quality_score(movie.ratings)

        provider_bonus = 0.0
        if preferred and any(
            offer.provider.casefold() in preferred for offer in verified_free
        ):
            provider_bonus = 5.0

        personal = _clamp(movie.personal_fit + provider_bonus)
        combined = _clamp(
            quality * (1.0 - personal_fit_weight)
            + personal * personal_fit_weight
        )

        reasons = list(movie.taste_reasons)
        if movie.ratings.imdb_votes:
            reasons.append(
                f"IMDb evidence: {movie.ratings.imdb:.1f}/10 "
                f"from {movie.ratings.imdb_votes:,} votes"
            )
        providers = sorted({offer.provider for offer in verified_free})
        reasons.append("Free on " + ", ".join(providers))

        results.append(
            RankedMovie(
                movie=movie,
                quality_score=round(quality, 2),
                personal_fit_score=round(personal, 2),
                combined_score=round(combined, 2),
                confidence=round(confidence, 2),
                reasons=tuple(reasons),
            )
        )

    return sorted(
        results,
        key=lambda result: (
            result.combined_score,
            result.quality_score,
            result.confidence,
            result.movie.title.casefold(),
        ),
        reverse=True,
    )
