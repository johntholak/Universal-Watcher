"""Provider and scorer contracts for Automated Job Hunter."""

from __future__ import annotations

from typing import Protocol, Sequence

from .models import FitAssessment, JobPosting, SearchProfile


class JobSourceAdapter(Protocol):
    name: str

    def discover(self, profile: SearchProfile) -> Sequence[JobPosting]:
        """Return normalized postings or raise a provider-specific availability error."""
        ...


class JobScorer(Protocol):
    def assess(self, posting: JobPosting, profile: SearchProfile) -> FitAssessment:
        """Return an explainable fit assessment for a posting that passed hard filters."""
        ...
