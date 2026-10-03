"""Deterministic core for Universal Watcher's free movie search.

Provider adapters should feed normalized MovieCandidate records into this module.
No network access belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import log10
from typing import Iterable, Sequence


# Household services the caller already pays for. Offers on these services
# can be treated as zero incremental cost by the search engine.
DEFAULT_INCLUDED_SUBSCRIPTIONS: tuple[str, ...] = (
    "Prime Video",
    "Max",
    "Apple TV+",
    "Hulu",
    "Peacock",
    "YouTube TV",
)

# Services the caller does not currently own but wants surfaced as options.
# These are never treated as actually accessible without an explicit override.
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


@dataclass(frozen=True)
class MovieCandidate:
    title: str
    year: int | None
    ratings: RatingEvidence
    offers: tuple[FreeOffer, ...]
    # Streaming availability date. None means currently available or unknown.
    available_from: str | None = None
    # Streaming availability date. None means currently available or unknown.
    available_from: str | None = None
    genres: tuple[str, ...] = ()
    runtime_minutes: int | None = None
    age_rating: str | None = None
    personal_fit: float = 0.0
    taste_reasons: tuple[str, ...] = ()
    # Explicit per-child fit supplied by the normalization/content-review layer.
    # This keeps developmental judgments out of the generic quality score.
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


def _age_fit_score(movie: MovieCandidate, age: int) -> float:
    """Return explicit fit for one child age, without inventing missing evidence."""
    for candidate_age, score in movie.age_fit_by_age:
        if candidate_age == age:
            return _clamp(score)
    return 0.0


def _kids_gate(movie: MovieCandidate, allow_pg13: bool) -> tuple[bool, str | None]:
    rating = (movie.age_rating or "").upper().strip()

    if movie.kids_eligible is False:
        return False, None

    if rating in {"R", "NC-17"}:
        return False, None

    if movie.kids_eligible is None:
        return False, None

    if rating == "PG-13":
        if not allow_pg13 or movie.pg13_kid_friendly is not True:
            return False, None
        return True, movie.pg13_reason or "PG-13 approved as kid-friendly"

    if rating in {"G", "PG", "TV-G", "TV-PG"}:
        return True, None

    # Unrated or unknown classifications require explicit kid eligibility.
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
) -> list[RankedMovie]:
    allowed = {g.casefold() for g in allowed_genres}
    excluded = {g.casefold() for g in excluded_genres}
    preferred = {p.casefold() for p in preferred_providers}

    results: list[RankedMovie] = []

    for movie in movies:
        accessible_offers = [
            offer for offer in movie.offers
            if _offer_accessible(
                offer,
                included_subscriptions=included_subscriptions,
                include_optional_services=include_optional_services,
                include_optional_as_free=include_optional_as_free,
            )
        ]
        if not accessible_offers:
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

        pg13_note: str | None = None
        if kids_mode:
            passed, pg13_note = _kids_gate(movie, allow_pg13)
            if not passed:
                continue

        quality, confidence = quality_score(movie.ratings)

        provider_bonus = 0.0
        if preferred and any(
            offer.provider.casefold() in preferred for offer in accessible_offers
        ):
            provider_bonus = 5.0

        personal = _clamp(movie.personal_fit + provider_bonus)

        reasons = list(movie.taste_reasons)

        if kids_mode and child_ages:
            child_scores = [
                (age, _age_fit_score(movie, age))
                for age in child_ages
            ]
            combined_age_fit = sum(score for _, score in child_scores) / len(child_scores)
            # Penalize a large age mismatch instead of hiding it inside one family score.
            spread = max(score for _, score in child_scores) - min(
                score for _, score in child_scores
            )
            age_component = _clamp(combined_age_fit - spread * 0.20)
            personal = _clamp(
                personal * (1.0 - age_fit_weight)
                + age_component * age_fit_weight
            )
            for age, score in child_scores:
                reasons.append(f"Age {age} fit: {score:.0f}/100")
            reasons.append(f"Mixed-age fit: {age_component:.0f}/100")
            if pg13_note:
                reasons.append(f"PG-13 approved for kids: {pg13_note}")

        combined = _clamp(
            quality * (1.0 - personal_fit_weight)
            + personal * personal_fit_weight
        )

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


def split_current_and_upcoming(
    ranked: Sequence[RankedMovie],
    *,
    as_of: str,
    days: int = 30,
) -> tuple[list[RankedMovie], list[RankedMovie]]:
    """Split ranked results into currently available and upcoming releases.

    Dates are ISO-8601 YYYY-MM-DD strings. Unknown dates stay in the current
    bucket only when the candidate already has a verified accessible offer.
    The provider layer should supply future availability dates for upcoming
    titles. This function does not invent them.
    """
    from datetime import date, timedelta

    start = date.fromisoformat(as_of)
    end = start + timedelta(days=days)
    current: list[RankedMovie] = []
    upcoming: list[RankedMovie] = []

    for result in ranked:
        available_from = result.movie.available_from
        if available_from:
            release_date = date.fromisoformat(available_from)
            if start < release_date <= end:
                upcoming.append(result)
                continue
        current.append(result)

    return current, upcoming


def split_current_and_upcoming(
    ranked: Sequence[RankedMovie],
    *,
    as_of: str,
    days: int = 30,
) -> tuple[list[RankedMovie], list[RankedMovie]]:
    """Split ranked results into currently available and upcoming releases."""
    from datetime import date, timedelta

    start = date.fromisoformat(as_of)
    end = start + timedelta(days=days)
    current: list[RankedMovie] = []
    upcoming: list[RankedMovie] = []

    for result in ranked:
        available_from = result.movie.available_from
        if available_from:
            release_date = date.fromisoformat(available_from)
            if start < release_date <= end:
                upcoming.append(result)
                continue
        current.append(result)

    return current, upcoming
