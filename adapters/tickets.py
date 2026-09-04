"""Ticket Watcher to Universal Watcher result normalization.

The imported Ticket Watcher keeps its own event discovery, marketplace
sources, matching, and browser extraction. This adapter only translates a
completed Ticket Watcher job snapshot into the shared result/evidence
contract. It deliberately does not start a live watcher or contact a
marketplace.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from typing import Any

from core.contracts import Evidence, WatchAdapter as WatchAdapterProtocol, WatchDefinition, WatchResult


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _integer(value: Any) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _coverage(job: Mapping[str, Any]) -> str:
    explicit = _text(job.get("coverage")).lower()
    if explicit in {"complete", "partial", "unavailable", "unknown"}:
        return explicit

    status = _text(job.get("status")).lower()
    if status in {"error", "blocked"}:
        return "unavailable"
    if status != "done":
        return "unknown"

    sources_total = _integer(job.get("sources_total"))
    sources_checked = _integer(job.get("sources_checked"))
    if sources_total is None or sources_checked is None:
        return "unknown"
    return "complete" if sources_checked >= sources_total else "partial"


def _matches(job: Mapping[str, Any]) -> list[Any]:
    value = job.get("matches")
    if not isinstance(value, list):
        return []
    return [item for item in value if getattr(item, "listing", None) is not None]


def _starts_text(value: Any) -> str:
    if not isinstance(value, datetime):
        return "date unavailable"
    return value.astimezone().strftime("%a %b %d, %Y at %I:%M %p")


def _match_evidence(match: Any) -> tuple[Evidence, ...]:
    listing = match.listing
    details: list[str] = []
    price_each = _number(getattr(listing, "price_each", None))
    if price_each is not None:
        currency = _text(getattr(listing, "currency", None)) or "USD"
        details.append(f"Advertised minimum {currency} {price_each:,.2f} each")

    estimated_total = _number(getattr(match, "estimated_order_total", None))
    if estimated_total is not None:
        currency = _text(getattr(listing, "currency", None)) or "USD"
        details.append(f"Estimated order total {currency} {estimated_total:,.2f}")

    quantity = _integer(getattr(listing, "quantity_available", None))
    if quantity is not None:
        details.append(f"{quantity} tickets reported available")

    seats_together = getattr(listing, "seats_together", None)
    if seats_together is True:
        details.append("adjacency confirmed")
    elif seats_together is False:
        details.append("adjacency not confirmed")

    fees_included = getattr(listing, "fees_included", None)
    if fees_included is True:
        details.append("fees included")
    elif fees_included is None:
        details.append("fees unknown")

    starts = _starts_text(getattr(listing, "starts_at", None))
    if starts != "date unavailable":
        details.append(f"Starts {starts}")

    notes = tuple(_text(note) for note in (getattr(match, "notes", ()) or ()) if _text(note))
    if notes:
        details.extend(notes)
    summary = " · ".join(details) or "Ticket offer returned by the configured source."
    source = _text(getattr(listing, "source", None)) or "Ticket source"
    destination = _text(getattr(listing, "event_url", None)) or None
    return (Evidence(source=source, kind="ticket-offer", summary=summary, url=destination),)


def _verification(match: Any, watch: WatchDefinition) -> tuple[str, str | None]:
    listing = match.listing
    notes = tuple(_text(note) for note in (getattr(match, "notes", ()) or ()) if _text(note))
    quantity = _integer(getattr(listing, "quantity_available", None))
    requested_quantity = watch.criteria.get("quantity", 1)
    try:
        requested_quantity = int(requested_quantity)
    except (TypeError, ValueError):
        requested_quantity = 1

    if notes:
        return "unverified", "; ".join(notes)
    if getattr(listing, "fees_included", None) is not True:
        return "unverified", "Fees are not confirmed, so the displayed total remains an estimate."
    if quantity is None or quantity < requested_quantity:
        return "unverified", "The source did not confirm enough tickets for this watch."
    if bool(watch.criteria.get("must_be_together", True)) and getattr(listing, "seats_together", None) is not True:
        return "unverified", "Seat adjacency is not confirmed by the source."
    return "verified", None


def _match_result(match: Any, watch: WatchDefinition, job: Mapping[str, Any], index: int, coverage: str) -> WatchResult:
    listing = match.listing
    event_name = _text(getattr(listing, "event_name", None)) or "Ticket event"
    venue = _text(getattr(listing, "venue", None))
    title = f"{event_name} · {venue}" if venue else event_name
    verification, reason = _verification(match, watch)
    event_id = _text(getattr(listing, "event_id", None)) or str(index)
    job_id = _text(job.get("id")) or "ticket-run"
    destination = _text(getattr(listing, "event_url", None)) or None
    return WatchResult(
        result_id=f"{job_id}-match-{event_id}-{index}",
        watch_id=watch.watch_id,
        module="tickets",
        title=title,
        outcome="match",
        verification=verification,
        coverage=coverage,
        evidence=_match_evidence(match),
        destination_url=destination,
        reason=reason,
    )


def _coverage_evidence(job: Mapping[str, Any]) -> tuple[Evidence, ...]:
    total = _integer(job.get("sources_total"))
    checked = _integer(job.get("sources_checked"))
    if total is not None and checked is not None:
        summary = f"Checked {checked} of {total} configured ticket sources."
    else:
        summary = "Ticket source coverage was not reported by this run."
    return (Evidence(source="Ticket Watcher", kind="coverage", summary=summary),)


def normalize_ticket_job(job: Mapping[str, Any], watch: WatchDefinition) -> list[WatchResult]:
    """Convert one bounded Ticket Watcher snapshot into shared results."""
    if not isinstance(job, Mapping):
        raise TypeError("job must be a mapping")

    coverage = _coverage(job)
    status = _text(job.get("status")).lower()
    if status != "done":
        outcome = "error" if status in {"error", "blocked"} else "unavailable"
        reason = _text(job.get("message")) or f"Ticket verification is {status or 'not complete'}."
        return [
            WatchResult(
                result_id=f"{_text(job.get('id')) or 'ticket-run'}-status",
                watch_id=watch.watch_id,
                module="tickets",
                title="Ticket Watcher verification",
                outcome=outcome,
                coverage=coverage,
                reason=reason,
            )
        ]

    matches = _matches(job)
    if matches:
        return [_match_result(match, watch, job, index, coverage) for index, match in enumerate(matches)]

    verification = "verified" if coverage == "complete" else "unverified"
    reason = _text(job.get("message")) or "No qualifying ticket offers matched the current criteria."
    return [
        WatchResult(
            result_id=f"{_text(job.get('id')) or 'ticket-run'}-no-match",
            watch_id=watch.watch_id,
            module="tickets",
            title="Ticket Watcher search",
            outcome="no_match",
            verification=verification,
            coverage=coverage,
            evidence=_coverage_evidence(job),
            reason=reason,
        )
    ]


class TicketWatcherAdapter:
    """Run boundary for a future Ticket Watcher job provider.

    ``job_provider`` is injected so the current Ticketmaster watcher remains
    standalone until the control-plane execution model is accepted.
    """

    module_name = "tickets"

    def __init__(self, job_provider: Callable[[WatchDefinition], Mapping[str, Any]]) -> None:
        self._job_provider = job_provider

    def run_once(self, watch: WatchDefinition) -> Iterable[WatchResult]:
        return normalize_ticket_job(self._job_provider(watch), watch)


assert isinstance(TicketWatcherAdapter(lambda _watch: {}), WatchAdapterProtocol)
