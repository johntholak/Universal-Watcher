"""Deterministic ranking core for Universal Watcher's Movie GM.

Provider adapters feed normalized MovieCandidate records into this module.
No network access belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import log10
from typing import Iterable, Sequence

from .movie_gm_profile import TasteProfile, WatchRecord, is_watched, score_taste

DEFAULT_INCLUDED_SUBSCRIPTIONS: tuple[str, ...] = (
    "Prime Video", "Max", "Apple TV+", "Hulu", "Peacock", "YouTube TV",
)
DEFAULT_OPTIONAL_SERVICES: tuple[str, ...] = ("Netflix",)


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
    availability_confidence: str = "unknown"


@dataclass(frozen=True)
class MovieCandidate:
    title: str
    year: int | None
    ratings: RatingEvidence
    offers: tuple[FreeOffer, ...]
    available_from: str | None = None
    genres: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    age_rating: str | None = None
    personal_fit: float = 50.0
    taste_reasons: tuple[str, ...] = ()
    age_fit_by_age: tuple[tuple[int, float], ...] = ()
    kids_eligible: bool | None = None
    pg13_kid_friendly: bool | None = None
    pg13_reason: str | None = None


@dataclass(frozen=True)
class RankedMovie:
    movie: MovieCandidate
    quality_score: float
    personal_fit_score: float
    combined_score: float
    confidence: float
    availability_confidence: float
    reasons: tuple[str, ...] = ()


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _bayesian_imdb(
    rating: float | None, votes: int | None, prior: float = 6.5, prior_votes: int = 5000,
) -> float | None:
    if rating is None:
        return None
    v = max(0, votes or 0)
    return (v / (v + prior_votes)) * rating + (prior_votes / (v + prior_votes)) * prior


def _rating_volume(votes: int | None) -> float:
    if not votes:
        return 0.0
    return _clamp((log10(max(votes, 1)) / 6.0) * 100.0)


def _offer_confidence(offer: FreeOffer) -> float:
    if not offer.verified:
        return 0.0
    return {
        "direct": 100.0,
        "recent": 95.0,
        "multi_source": 92.0,
        "indirect": 65.0,
        "stale": 40.0,
        "unknown": 50.0,
    }.get(offer.availability_confidence, 50.0)


def _offer_accessible(
    offer: FreeOffer,
    *,
    included_subscriptions: Sequence[str],
    include_optional_services: Sequence[str],
    include_optional_as_free: bool,
) -> bool:
    if not offer.verified:
        return False
    access = offer.access.casefold()
    provider = offer.provider.casefold()
    included = {p.casefold() for p in included_subscriptions}
    optional = {p.casefold() for p in include_optional_services}
    if access in {"free", "free_ads"}:
        return True
    if access in {"subscription", "included_subscription", "paid_subscription"}:
        return provider in included or (include_optional_as_free and provider in optional)
    return False


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
    total = sum(weight for _, weight in components)
    score = sum(value * weight for value, weight in components) / total
    confidence = min(100.0, (len(components) / 4.0) * 60.0 + _rating_volume(ratings.imdb_votes) * 0.40)
    return _clamp(score), _clamp(confidence)


def _age_fit_score(movie: MovieCandidate, age: int) -> float:
    for candidate_age, score in movie.age_fit_by_age:
        if candidate_age == age:
            return _clamp(score)
    return 0.0


def _kids_gate(movie: MovieCandidate, allow_pg13: bool) -> tuple[bool, str | None]:
    rating = (movie.age_rating or "").upper().strip()
    if movie.kids_eligible is False or rating in {"R", "NC-17"}:
        return False, None
    if movie.kids_eligible is None:
        return False, None
    if rating == "PG-13":
        if not allow_pg13 or movie.pg13_kid_friendly is not True:
            return False, None
        return True, movie.pg13_reason or "PG-13 approved as kid-friendly"
    if rating in {"G", "PG", "TV-G", "TV-PG"}:
        return True, None
    return movie.kids_eligible is True, None


def rank_movies(
    movies: Iterable[MovieCandidate],
    *,
    minimum_imdb: float | None = None,
    minimum_votes: int | None = None,
    allowed_genres: Sequence[str] = (),
    excluded_genres: Sequence[str] = (),
    preferred_providers: Sequence[str] = (),
    personal_fit_weight: float = 0.35,
    kids_mode: bool = False,
    child_ages: Sequence[int] = (),
    allow_pg13: bool = True,
    age_fit_weight: float = 0.45,
    included_subscriptions: Sequence[str] = DEFAULT_INCLUDED_SUBSCRIPTIONS,
    include_optional_services: Sequence[str] = DEFAULT_OPTIONAL_SERVICES,
    include_optional_as_free: bool = False,
    availability_weight: float = 0.10,
    taste_profile: TasteProfile | None = None,
    watch_history: Sequence[WatchRecord] = (),
    suppress_watched: bool = True,
) -> list[RankedMovie]:
    allowed = {g.casefold() for g in allowed_genres}
    excluded = {g.casefold() for g in excluded_genres}
    preferred = {p.casefold() for p in preferred_providers}
    results: list[RankedMovie] = []

    for movie in movies:
        if suppress_watched and is_watched(movie.title, watch_history):
            continue

        accessible = [
            o for o in movie.offers
            if _offer_accessible(
                o,
                included_subscriptions=included_subscriptions,
                include_optional_services=include_optional_services,
                include_optional_as_free=include_optional_as_free,
            )
        ]
        if not accessible:
            continue
        if minimum_imdb is not None and (movie.ratings.imdb is None or movie.ratings.imdb < minimum_imdb):
            continue
        if minimum_votes is not None and (movie.ratings.imdb_votes or 0) < minimum_votes:
            continue
        genres = {g.casefold() for g in movie.genres}
        if allowed and not genres.intersection(allowed):
            continue
        if excluded and genres.intersection(excluded):
            continue

        pg13_note = None
        if kids_mode:
            passed, pg13_note = _kids_gate(movie, allow_pg13)
            if not passed:
                continue

        quality, quality_confidence = quality_score(movie.ratings)
        availability = max(_offer_confidence(o) for o in accessible)
        provider_bonus = 5.0 if preferred and any(o.provider.casefold() in preferred for o in accessible) else 0.0

        personal = _clamp(movie.personal_fit + provider_bonus)
        reasons = list(movie.taste_reasons)

        if taste_profile is not None:
            taste_score, taste_reasons = score_taste(
                genres=movie.genres,
                title=movie.title,
                profile=taste_profile,
                runtime_minutes=movie.runtime_minutes,
            )
            personal = _clamp((personal + taste_score) / 2.0)
            reasons.extend(taste_reasons)
            reasons.append(f"Taste fit: {taste_score:.0f}/100")

        if kids_mode and child_ages:
            scores = [(age, _age_fit_score(movie, age)) for age in child_ages]
            average = sum(score for _, score in scores) / len(scores)
            spread = max(score for _, score in scores) - min(score for _, score in scores)
            age_component = _clamp(average - spread * 0.20)
            personal = _clamp(personal * (1.0 - age_fit_weight) + age_component * age_fit_weight)
            reasons.extend(f"Age {age} fit: {score:.0f}/100" for age, score in scores)
            reasons.append(f"Mixed-age fit: {age_component:.0f}/100")
            if pg13_note:
                reasons.append(f"PG-13 approved for kids: {pg13_note}")

        combined = _clamp(
            quality * (1.0 - personal_fit_weight)
            + personal * personal_fit_weight
            + availability * availability_weight
            - 100.0 * availability_weight
        )
        if movie.ratings.imdb_votes:
            reasons.append(f"IMDb evidence: {movie.ratings.imdb:.1f}/10 from {movie.ratings.imdb_votes:,} votes")
        providers = sorted({o.provider for o in accessible})
        reasons.append("Accessible on " + ", ".join(providers))
        reasons.append(f"Availability confidence: {availability:.0f}/100")
        if suppress_watched and watch_history:
            reasons.append("Watched-history suppression is active")

        results.append(RankedMovie(
            movie=movie,
            quality_score=round(quality, 2),
            personal_fit_score=round(personal, 2),
            combined_score=round(combined, 2),
            confidence=round(quality_confidence, 2),
            availability_confidence=round(availability, 2),
            reasons=tuple(reasons),
        ))

    return sorted(
        results,
        key=lambda r: (r.combined_score, r.quality_score, r.availability_confidence, r.movie.title.casefold()),
        reverse=True,
    )


def split_current_and_upcoming(
    ranked: Sequence[RankedMovie], *, as_of: str, days: int = 30,
) -> tuple[list[RankedMovie], list[RankedMovie]]:
    start = date.fromisoformat(as_of)
    end = start + timedelta(days=days)
    current: list[RankedMovie] = []
    upcoming: list[RankedMovie] = []
    for result in ranked:
        if result.movie.available_from:
            release_date = date.fromisoformat(result.movie.available_from)
            if start < release_date <= end:
                upcoming.append(result)
                continue
        current.append(result)
    return current, upcoming
