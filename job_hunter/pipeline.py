"""Provider-agnostic pipeline helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import JobPosting, SearchProfile


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def posting_key(posting: JobPosting) -> str:
    if posting.canonical_key:
        return posting.canonical_key
    if posting.source_job_id:
        return f"{_norm(posting.source)}::{_norm(posting.source_job_id)}"
    return "::".join((_norm(posting.company), _norm(posting.title), _norm(posting.location)))


def deduplicate(postings: Iterable[JobPosting]) -> list[JobPosting]:
    seen: set[str] = set()
    unique: list[JobPosting] = []
    for posting in postings:
        key = posting_key(posting)
        if key in seen:
            continue
        seen.add(key)
        unique.append(posting)
    return unique


def hard_filter_reasons(posting: JobPosting, profile: SearchProfile) -> list[str]:
    reasons: list[str] = []
    company = _norm(posting.company)
    title_blob = _norm(f"{posting.title} {posting.description or ''}")

    if company and company in {_norm(x) for x in profile.blocked_companies}:
        reasons.append("blocked company")

    if profile.employment_types and posting.employment_type:
        allowed = {_norm(x) for x in profile.employment_types}
        if _norm(posting.employment_type) not in allowed:
            reasons.append("employment type mismatch")

    if profile.minimum_compensation is not None and posting.compensation:
        known_max = posting.compensation.maximum
        if known_max is not None and known_max < profile.minimum_compensation:
            reasons.append("known compensation below minimum")

    for term in profile.required_terms:
        if _norm(term) not in title_blob:
            reasons.append(f"missing required term: {term}")

    for term in profile.excluded_terms:
        if _norm(term) and _norm(term) in title_blob:
            reasons.append(f"excluded term present: {term}")

    return reasons


def passes_hard_filters(posting: JobPosting, profile: SearchProfile) -> bool:
    return not hard_filter_reasons(posting, profile)
