"""Normalized domain models for Automated Job Hunter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class FitBucket(str, Enum):
    STRONG = "strong_fit"
    MAYBE = "maybe"
    SKIP = "skip"


class ApplicationState(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    REJECTED = "rejected"
    OFFER = "offer"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class Compensation:
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[str] = None


@dataclass(frozen=True)
class JobPosting:
    source: str
    source_job_id: str
    company: str
    title: str
    apply_url: str
    retrieved_at: datetime
    location: Optional[str] = None
    work_arrangement: Optional[str] = None
    employment_type: Optional[str] = None
    compensation: Optional[Compensation] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    canonical_key: Optional[str] = None


@dataclass(frozen=True)
class SearchProfile:
    target_roles: tuple[str, ...] = ()
    allowed_locations: tuple[str, ...] = ()
    remote_modes: tuple[str, ...] = ()
    employment_types: tuple[str, ...] = ()
    blocked_companies: tuple[str, ...] = ()
    minimum_compensation: Optional[float] = None
    required_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class FitDimension:
    name: str
    score: float
    reason: str


@dataclass(frozen=True)
class FitAssessment:
    bucket: FitBucket
    score: Optional[float]
    dimensions: tuple[FitDimension, ...] = ()
    hard_blockers: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


@dataclass
class ApplicationRecord:
    job_key: str
    state: ApplicationState = ApplicationState.SAVED
    notes: list[str] = field(default_factory=list)
