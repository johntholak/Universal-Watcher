"""Minimal cross-module contracts.

These types describe the handoff between the future Universal Watcher control
plane and module-specific engines. They intentionally do not prescribe how a
module discovers, verifies, or monitors its source.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Mapping, Protocol, runtime_checkable


WatchStatus = Literal["draft", "active", "paused", "completed", "error"]
ResultOutcome = Literal["match", "no_match", "unavailable", "error"]
VerificationStatus = Literal["unverified", "verified", "rejected"]
CoverageStatus = Literal["complete", "partial", "unavailable", "unknown"]

WATCH_STATUSES = frozenset({"draft", "active", "paused", "completed", "error"})
RESULT_OUTCOMES = frozenset({"match", "no_match", "unavailable", "error"})
VERIFICATION_STATUSES = frozenset({"unverified", "verified", "rejected"})
COVERAGE_STATUSES = frozenset({"complete", "partial", "unavailable", "unknown"})

WATCH_TRANSITIONS = {
    "draft": frozenset({"active", "error"}),
    "active": frozenset({"paused", "completed", "error"}),
    "paused": frozenset({"active", "completed", "error"}),
    "completed": frozenset(),
    "error": frozenset(),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class WatchDefinition:
    """A user request in a module-neutral shape."""

    watch_id: str
    module: str
    query: str
    criteria: Mapping[str, Any] = field(default_factory=dict)
    status: WatchStatus = "draft"
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "watch_id", _require_text(self.watch_id, "watch_id"))
        object.__setattr__(self, "module", _require_text(self.module, "module"))
        object.__setattr__(self, "query", _require_text(self.query, "query"))
        if self.status not in WATCH_STATUSES:
            raise ValueError(f"unsupported watch status: {self.status}")
        if not isinstance(self.criteria, Mapping):
            raise TypeError("criteria must be a mapping")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

    def with_status(self, status: WatchStatus) -> "WatchDefinition":
        if status not in WATCH_STATUSES:
            raise ValueError(f"unsupported watch status: {status}")
        return replace(self, status=status)

    def transition_to(self, status: WatchStatus) -> "WatchDefinition":
        """Return a copy after enforcing the watch lifecycle."""
        if status not in WATCH_STATUSES:
            raise ValueError(f"unsupported watch status: {status}")
        if status == self.status:
            return self
        if status not in WATCH_TRANSITIONS[self.status]:
            raise ValueError(f"cannot transition watch from {self.status} to {status}")
        return replace(self, status=status)


@dataclass(frozen=True)
class Evidence:
    """A concise, user-displayable explanation for a result."""

    source: str
    kind: str
    summary: str
    url: str | None = None
    captured_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _require_text(self.source, "source"))
        object.__setattr__(self, "kind", _require_text(self.kind, "kind"))
        object.__setattr__(self, "summary", _require_text(self.summary, "summary"))
        if self.url is not None:
            object.__setattr__(self, "url", _require_text(self.url, "url"))
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")


@dataclass(frozen=True)
class WatchResult:
    """One normalized outcome from a module adapter.

    ``unavailable`` is intentionally separate from ``no_match``. A source
    that could not be checked must never be presented as an empty result.
    """

    result_id: str
    watch_id: str
    module: str
    title: str
    outcome: ResultOutcome
    verification: VerificationStatus = "unverified"
    coverage: CoverageStatus = "unknown"
    evidence: tuple[Evidence, ...] = ()
    destination_url: str | None = None
    reason: str | None = None
    observed_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.result_id, "result_id"),
            (self.watch_id, "watch_id"),
            (self.module, "module"),
            (self.title, "title"),
        ):
            object.__setattr__(self, field_name, _require_text(value, field_name))
        if self.outcome not in RESULT_OUTCOMES:
            raise ValueError(f"unsupported result outcome: {self.outcome}")
        if self.verification not in VERIFICATION_STATUSES:
            raise ValueError(f"unsupported verification status: {self.verification}")
        if self.coverage not in COVERAGE_STATUSES:
            raise ValueError(f"unsupported coverage status: {self.coverage}")
        if not isinstance(self.evidence, tuple) or not all(isinstance(item, Evidence) for item in self.evidence):
            raise TypeError("evidence must be a tuple of Evidence values")
        if self.destination_url is not None:
            object.__setattr__(self, "destination_url", _require_text(self.destination_url, "destination_url"))
        if self.reason is not None:
            object.__setattr__(self, "reason", _require_text(self.reason, "reason"))
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")


@runtime_checkable
class WatchAdapter(Protocol):
    """The intentionally small control-plane bridge for a module.

    Module adapters keep their own discovery, browser, API, and worker logic.
    The shared layer only requires a name and one normalized run boundary.
    """

    module_name: str

    def run_once(self, watch: WatchDefinition) -> Iterable[WatchResult]:
        """Execute one bounded check and return normalized outcomes."""
