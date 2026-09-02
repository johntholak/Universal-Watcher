"""Family Deals to Universal Watcher result normalization.

The imported Family Deals engine keeps its own discovery, crawling, caching,
and strict semantic verifier. This adapter only translates a completed (or
in-progress) Family Deals job record into the shared result/evidence contract.
It deliberately does not start a live job or change the legacy engine.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from core.contracts import Evidence, WatchAdapter as WatchAdapterProtocol, WatchDefinition, WatchResult


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _count(job: Mapping[str, Any], key: str) -> int:
    try:
        return max(0, int(job.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _records(job: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = job.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _coverage(job: Mapping[str, Any]) -> str:
    status = _text(job.get("status")).lower()
    if status in {"error", "blocked"}:
        return "unavailable"
    if status != "done":
        return "unknown"

    total = _count(job, "total")
    processed = _count(job, "processed")
    unresolved = _count(job, "unresolved")
    blocked = _count(job, "blocked")
    sources_total = _count(job, "sources_total")
    sources_checked = _count(job, "sources_checked")
    if processed < total or unresolved or blocked or sources_checked < sources_total:
        return "partial"
    return "complete"


def _record_evidence(record: Mapping[str, Any]) -> tuple[Evidence, ...]:
    summary = _text(record.get("evidence"))
    price = record.get("price")
    capacity = _text(record.get("capacity_label"))
    qualifiers: list[str] = []
    if price is not None:
        qualifiers.append(f"${price}")
    if capacity:
        qualifiers.append(f"serves {capacity}")
    if qualifiers:
        summary = " · ".join(qualifiers) + (f" · {summary}" if summary else "")
    if not summary:
        summary = "Family meal evidence returned by the strict verifier."

    source_url = _text(record.get("source_url") or record.get("website")) or None
    return (Evidence(source="Family Deals official source", kind="official-source", summary=summary, url=source_url),)


def _record_result(
    watch: WatchDefinition,
    job: Mapping[str, Any],
    record: Mapping[str, Any],
    index: int,
    *,
    kind: str,
    coverage: str,
) -> WatchResult:
    name = _text(record.get("name")) or "Family Deals restaurant"
    destination_url = _text(record.get("source_url") or record.get("website")) or None
    if kind == "match":
        title = f"{name} · Family deal"
        outcome = "match"
        verification = "verified"
        reason = None
    elif kind == "needs_hours":
        title = f"{name} · Hours need confirmation"
        outcome = "unavailable"
        verification = "unverified"
        reason = "Meal and serving evidence were found, but dinner availability could not be verified."
    else:
        title = f"{name} · Serving capacity needs confirmation"
        outcome = "unavailable"
        verification = "unverified"
        reason = "Meal evidence was found, but serving capacity for the requested party was not verified."

    return WatchResult(
        result_id=f"{_text(job.get('id') or 'family-deals-run')}-{kind}-{index}",
        watch_id=watch.watch_id,
        module="family-deals",
        title=title,
        outcome=outcome,
        verification=verification,
        coverage=coverage,
        evidence=_record_evidence(record),
        destination_url=destination_url,
        reason=reason,
    )


def _coverage_evidence(job: Mapping[str, Any]) -> tuple[Evidence, ...]:
    total = _count(job, "total")
    processed = _count(job, "processed")
    checked = _count(job, "sources_checked")
    sources_total = _count(job, "sources_total")
    unresolved = _count(job, "unresolved")
    blocked = _count(job, "blocked")
    summary = (
        f"Checked {processed} of {total} restaurants and {checked} of {sources_total} official sources; "
        f"{unresolved} unresolved and {blocked} blocked."
    )
    return (Evidence(source="Family Deals", kind="coverage", summary=summary),)


def normalize_family_deals_job(job: Mapping[str, Any], watch: WatchDefinition) -> list[WatchResult]:
    """Convert one Family Deals job snapshot into truthful shared results."""
    if not isinstance(job, Mapping):
        raise TypeError("job must be a mapping")

    coverage = _coverage(job)
    status = _text(job.get("status")).lower()
    if status != "done":
        outcome = "error" if status == "error" else "unavailable"
        reason = _text(job.get("message")) or f"Family Deals verification is {status or 'not complete'}."
        return [
            WatchResult(
                result_id=f"{_text(job.get('id') or 'family-deals-run')}-status",
                watch_id=watch.watch_id,
                module="family-deals",
                title="Family Deals verification",
                outcome=outcome,
                coverage=coverage,
                reason=reason,
            )
        ]

    results: list[WatchResult] = []
    for index, record in enumerate(_records(job, "matches")):
        results.append(_record_result(watch, job, record, index, kind="match", coverage=coverage))
    for index, record in enumerate(_records(job, "needs_hours")):
        results.append(_record_result(watch, job, record, index, kind="needs_hours", coverage=coverage))
    for index, record in enumerate(_records(job, "needs_capacity")):
        results.append(_record_result(watch, job, record, index, kind="needs_capacity", coverage=coverage))

    if not results:
        reason = _text(job.get("message")) or "No fully verified family meal matched the current criteria."
        verification = "verified" if coverage == "complete" else "unverified"
        results.append(
            WatchResult(
                result_id=f"{_text(job.get('id') or 'family-deals-run')}-no-match",
                watch_id=watch.watch_id,
                module="family-deals",
                title="Family Deals search",
                outcome="no_match",
                verification=verification,
                coverage=coverage,
                evidence=_coverage_evidence(job),
                reason=reason,
            )
        )
    return results


class FamilyDealsAdapter:
    """Run boundary for a future Family Deals job provider.

    ``job_provider`` is intentionally injected. The current Family Deals
    server remains standalone; a later control-plane worker can supply a
    provider that starts/waits for that engine without moving its internals.
    """

    module_name = "family-deals"

    def __init__(self, job_provider: Callable[[WatchDefinition], Mapping[str, Any]]) -> None:
        self._job_provider = job_provider

    def run_once(self, watch: WatchDefinition) -> Iterable[WatchResult]:
        return normalize_family_deals_job(self._job_provider(watch), watch)


assert isinstance(FamilyDealsAdapter(lambda _watch: {}), WatchAdapterProtocol)
