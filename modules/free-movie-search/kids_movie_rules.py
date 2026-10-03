"""Conservative, deterministic kids-movie suitability rules.

This module converts normalized content evidence into per-child age fit.
It intentionally does not infer suitability from rating alone. Provider/content
adapters should supply explicit evidence such as family genre, content flags,
and a PG-13 rationale.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class KidsContentEvidence:
    age_rating: str | None
    genres: tuple[str, ...] = ()
    family_tags: tuple[str, ...] = ()
    adult_content_flags: tuple[str, ...] = ()
    scary_content_flags: tuple[str, ...] = ()
    violence_flags: tuple[str, ...] = ()
    language_flags: tuple[str, ...] = ()
    pg13_reason: str | None = None


@dataclass(frozen=True)
class KidsFit:
    eligible: bool
    pg13_kid_friendly: bool
    pg13_reason: str | None
    age_fit_by_age: tuple[tuple[int, float], ...]
    reasons: tuple[str, ...]


def _norm(values: Sequence[str]) -> set[str]:
    return {value.casefold().strip() for value in values if value.strip()}


def _score_for_age(
    age: int,
    *,
    family: bool,
    adult: bool,
    scary: bool,
    violence: bool,
    language: bool,
) -> float:
    score = 78.0
    if family:
        score += 12.0
    if adult:
        score -= 55.0
    if scary:
        score -= 24.0 if age <= 6 else 12.0
    if violence:
        score -= 18.0 if age <= 6 else 8.0
    if language:
        score -= 8.0 if age <= 6 else 3.0

    # A 9-year-old can tolerate more action/fantasy content than a 6-year-old,
    # but the engine never converts an adult-content flag into a recommendation.
    if age >= 9 and scary:
        score += 4.0
    return max(0.0, min(100.0, score))


def evaluate_kids_fit(
    evidence: KidsContentEvidence,
    *,
    child_ages: Sequence[int] = (6, 9),
) -> KidsFit:
    rating = (evidence.age_rating or "").upper().strip()
    genres = _norm(evidence.genres)
    family_tags = _norm(evidence.family_tags)
    adult_flags = _norm(evidence.adult_content_flags)
    scary_flags = _norm(evidence.scary_content_flags)
    violence_flags = _norm(evidence.violence_flags)
    language_flags = _norm(evidence.language_flags)

    family = bool(
        {"family", "kids", "animation", "children"} & genres
        or {"family", "kids", "children", "all-ages"} & family_tags
    )
    adult = bool(adult_flags)
    scary = bool(scary_flags)
    violence = bool(violence_flags)
    language = bool(language_flags)

    if rating in {"R", "NC-17"} or adult:
        return KidsFit(
            eligible=False,
            pg13_kid_friendly=False,
            pg13_reason=None,
            age_fit_by_age=tuple((age, 0.0) for age in child_ages),
            reasons=("Rejected: adult-content evidence or R/NC-17 rating",),
        )

    pg13 = rating == "PG-13"
    pg13_kid_friendly = (
        pg13
        and family
        and not adult
        and not scary
        and bool(evidence.pg13_reason)
    )

    if pg13 and not pg13_kid_friendly:
        return KidsFit(
            eligible=False,
            pg13_kid_friendly=False,
            pg13_reason=None,
            age_fit_by_age=tuple((age, 0.0) for age in child_ages),
            reasons=("Rejected: PG-13 lacks strong family/kid-friendly evidence",),
        )

    if rating not in {"G", "PG", "PG-13", "TV-G", "TV-PG"}:
        return KidsFit(
            eligible=False,
            pg13_kid_friendly=False,
            pg13_reason=None,
            age_fit_by_age=tuple((age, 0.0) for age in child_ages),
            reasons=("Rejected: unknown or unsupported age classification",),
        )

    age_fit = tuple(
        (
            age,
            round(
                _score_for_age(
                    age,
                    family=family,
                    adult=adult,
                    scary=scary,
                    violence=violence,
                    language=language,
                ),
                1,
            ),
        )
        for age in child_ages
    )

    reasons = []
    if family:
        reasons.append("Family/kids evidence present")
    if scary:
        reasons.append("Scary-content evidence present")
    if violence:
        reasons.append("Action/violence evidence present")
    if language:
        reasons.append("Language evidence present")
    if pg13:
        reasons.append(f"PG-13 rationale: {evidence.pg13_reason}")

    return KidsFit(
        eligible=True,
        pg13_kid_friendly=pg13_kid_friendly,
        pg13_reason=evidence.pg13_reason if pg13 else None,
        age_fit_by_age=age_fit,
        reasons=tuple(reasons),
    )
