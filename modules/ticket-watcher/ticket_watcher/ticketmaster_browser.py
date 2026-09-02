from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TicketmasterOffer:
    offer_id: str
    section: str
    row: str
    currency: str
    base_price: float
    charges: float
    all_in_price: float
    offer_type: str


def parse_quickpicks(payload: dict[str, Any]) -> list[TicketmasterOffer]:
    embedded = payload.get("_embedded", {})
    raw_offers = embedded.get("offer", []) if isinstance(embedded, dict) else []
    parsed: list[TicketmasterOffer] = []
    for raw in raw_offers if isinstance(raw_offers, list) else []:
        if not isinstance(raw, dict):
            continue
        base = _number(raw.get("listPrice"))
        if base is None:
            continue
        charges = sum(
            amount
            for charge in raw.get("charges", [])
            if isinstance(charge, dict) and (amount := _number(charge.get("amount"))) is not None
        )
        offer_type = str(raw.get("type") or raw.get("ticketType") or raw.get("offerType") or "Unknown")
        parsed.append(TicketmasterOffer(
            offer_id=str(raw.get("id") or raw.get("offerId") or ""),
            section=str(raw.get("section") or "Unknown"),
            row=str(raw.get("row") or "Unknown"),
            currency=str(raw.get("currency") or "USD"),
            base_price=round(base, 2),
            charges=round(charges, 2),
            all_in_price=round(base + charges, 2),
            offer_type=offer_type,
        ))
    return sorted(parsed, key=lambda offer: offer.all_in_price)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
