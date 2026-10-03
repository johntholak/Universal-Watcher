"""Household taste and watch-history primitives for Movie GM.

This layer stores explicit preferences and feedback without making network calls.
It is intentionally separate from provider discovery and kids safety rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TasteProfile:
    preferred_genres: tuple[str, ...] = ()
    disliked_genres: tuple[str, ...] = ()
    preferred_keywords: tuple[str, ...] = ()
    disliked_keywords: tuple[str, ...] = ()
    preferred_runtime_max: int | None = None
    preferred_runtime_min: int | None = None


@dataclass(frozen=True)
class WatchRecord:
    title_key: str
    rating: str = "unrated"
    viewers: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "title_key", normalize_title(self.title_key))


VALID_FEEDBACK = frozenset({"loved", "liked", "fine", "disliked"})


def normalize_title(title: str) -> str:
    return " ".join(title.casefold().strip().split())


def is_watched(title: str, history: Sequence[WatchRecord]) -> bool:
    key = normalize_title(title)
    return any(record.title_key == key for record in history)


def feedback_signal(title: str, history: Sequence[WatchRecord]) -> float:
    key = normalize_title(title)
    signals = {"loved": 100.0, "liked": 70.0, "fine": 50.0, "disliked": 0.0}
    matches = [signals.get(r.rating, 50.0) for r in history if r.title_key == key]
    return sum(matches) / len(matches) if matches else 50.0


def score_taste(
    *,
    genres: Sequence[str],
    title: str,
    profile: TasteProfile,
    runtime_minutes: int | None = None,
) -> tuple[float, tuple[str, ...]]:
    genre_set = {g.casefold() for g in genres}
    preferred = {g.casefold() for g in profile.preferred_genres}
    disliked = {g.casefold() for g in profile.disliked_genres}
    title_text = title.casefold()

    score = 50.0
    reasons: list[str] = []

    matches = genre_set & preferred
    if matches:
        score += min(30.0, 10.0 * len(matches))
        reasons.append("Preferred genre: " + ", ".join(sorted(matches)))

    misses = genre_set & disliked
    if misses:
        score -= min(45.0, 15.0 * len(misses))
        reasons.append("Disliked genre: " + ", ".join(sorted(misses)))

    keyword_hits = [k for k in profile.preferred_keywords if k.casefold() in title_text]
    if keyword_hits:
        score += min(15.0, 5.0 * len(keyword_hits))
        reasons.append("Matches a preferred theme")

    keyword_misses = [k for k in profile.disliked_keywords if k.casefold() in title_text]
    if keyword_misses:
        score -= min(20.0, 10.0 * len(keyword_misses))
        reasons.append("Matches a disliked theme")

    if runtime_minutes is not None:
        if profile.preferred_runtime_max is not None and runtime_minutes <= profile.preferred_runtime_max:
            score += 5.0
            reasons.append("Runtime fits preference")
        elif profile.preferred_runtime_max is not None and runtime_minutes > profile.preferred_runtime_max:
            score -= 5.0
        if profile.preferred_runtime_min is not None and runtime_minutes >= profile.preferred_runtime_min:
            score += 3.0

    return max(0.0, min(100.0, score)), tuple(reasons)
