"""Movie GM household decision and feedback primitives.

Provider-neutral, deterministic logic. No network or persistence belongs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .movie_gm_profile import TasteProfile, WatchRecord, normalize_title, score_taste


@dataclass(frozen=True)
class ViewerProfile:
    viewer_id: str
    taste: TasteProfile = TasteProfile()
    weight: float = 1.0


@dataclass(frozen=True)
class HouseholdFit:
    score: float
    average_fit: float
    disagreement: float
    viewer_scores: tuple[tuple[str, float], ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoreBreakdown:
    quality: float
    taste: float
    household: float
    availability: float
    final: float
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class LearnedTaste:
    preferred_genres: tuple[str, ...] = ()
    disliked_genres: tuple[str, ...] = ()
    preferred_keywords: tuple[str, ...] = ()
    disliked_keywords: tuple[str, ...] = ()
    evidence_count: int = 0


def household_fit(*, title: str, genres: Sequence[str], runtime_minutes: int | None,
                  viewers: Sequence[ViewerProfile]) -> HouseholdFit:
    if not viewers:
        return HouseholdFit(50.0, 50.0, 0.0, (), ("No individual household profiles supplied",))
    scored: list[tuple[str, float]] = []
    weighted_total = weight_total = 0.0
    for viewer in viewers:
        score, _ = score_taste(genres=genres, title=title, profile=viewer.taste, runtime_minutes=runtime_minutes)
        weight = max(0.0, viewer.weight)
        scored.append((viewer.viewer_id, score))
        weighted_total += score * weight
        weight_total += weight
    average = weighted_total / weight_total if weight_total else 50.0
    values = [score for _, score in scored]
    disagreement = max(values) - min(values) if values else 0.0
    final = max(0.0, min(100.0, average - disagreement * 0.20))
    reasons = [f"Household fit: {final:.0f}/100"]
    if disagreement >= 25:
        reasons.append(f"Household disagreement: {disagreement:.0f} points")
    return HouseholdFit(round(final, 2), round(average, 2), round(disagreement, 2),
                        tuple(scored), tuple(reasons))


def breakdown(*, quality: float, taste: float, household: float, availability: float,
              quality_weight: float = 0.40, taste_weight: float = 0.20,
              household_weight: float = 0.25, availability_weight: float = 0.15) -> ScoreBreakdown:
    weights = tuple(max(0.0, w) for w in
                    (quality_weight, taste_weight, household_weight, availability_weight))
    total = sum(weights)
    final = 0.0 if total == 0 else (
        quality * weights[0] + taste * weights[1] + household * weights[2] + availability * weights[3]
    ) / total
    reasons = (
        f"Quality: {quality:.0f}/100",
        f"Taste fit: {taste:.0f}/100",
        f"Household fit: {household:.0f}/100",
        f"Availability confidence: {availability:.0f}/100",
    )
    return ScoreBreakdown(round(quality, 2), round(taste, 2), round(household, 2),
                          round(availability, 2), round(max(0.0, min(100.0, final)), 2), reasons)


def learn_taste_from_history(history: Iterable[tuple[WatchRecord, Sequence[str], str]]) -> LearnedTaste:
    """Learn only from explicit loved, liked, or disliked feedback."""
    preferred_genres: dict[str, int] = {}
    disliked_genres: dict[str, int] = {}
    preferred_keywords: dict[str, int] = {}
    disliked_keywords: dict[str, int] = {}
    evidence = 0

    for record, genres, title in history:
        rating = record.rating.casefold().strip()
        if rating not in {"loved", "liked", "disliked"}:
            continue
        evidence += 1
        target = disliked_genres if rating == "disliked" else preferred_genres
        for genre in genres:
            key = genre.casefold().strip()
            if key:
                target[key] = target.get(key, 0) + 1
        words = [w for w in normalize_title(title).split() if len(w) >= 5]
        keyword_target = disliked_keywords if rating == "disliked" else preferred_keywords
        for word in words[:5]:
            keyword_target[word] = keyword_target.get(word, 0) + 1

    def top(mapping: dict[str, int]) -> tuple[str, ...]:
        return tuple(k for k, _ in sorted(mapping.items(), key=lambda item: (-item[1], item[0]))[:8])

    return LearnedTaste(
        preferred_genres=top(preferred_genres),
        disliked_genres=top(disliked_genres),
        preferred_keywords=top(preferred_keywords),
        disliked_keywords=top(disliked_keywords),
        evidence_count=evidence,
    )
