from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import Listing, Match, WatchConfig


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def event_similarity(wanted: str, found: str) -> float:
    left, right = normalize(wanted), normalize(found)
    if not left or not right:
        return 0.0
    sequence = SequenceMatcher(None, left, right).ratio()
    wanted_tokens, found_tokens = set(left.split()), set(right.split())
    overlap = len(wanted_tokens & found_tokens) / max(1, len(wanted_tokens))
    return max(sequence, overlap)


def rejection_reasons(listing: Listing, config: WatchConfig) -> list[str]:
    reasons: list[str] = []
    similarity = event_similarity(config.event, listing.event_name)
    if similarity < config.minimum_event_match:
        reasons.append(f"event-name match {similarity:.0%} is below required {config.minimum_event_match:.0%}")
    if config.venue and normalize(config.venue) not in normalize(listing.venue):
        reasons.append(f"venue does not match {config.venue}")
    if config.require_fees_included and listing.fees_included is not True:
        reasons.append("fees-included pricing is not confirmed")
    if listing.quantity_available is not None and listing.quantity_available < config.quantity:
        reasons.append(f"only {listing.quantity_available} tickets are reported available")
    if config.must_be_together and listing.seats_together is False:
        reasons.append("tickets are not together")
    if listing.price_each is None and (config.max_price_each is not None or config.max_order_total is not None):
        reasons.append("Ticketmaster did not publish an event price range")
    if listing.price_each is not None:
        if config.max_price_each is not None and listing.price_each > config.max_price_each:
            reasons.append(f"advertised minimum ${listing.price_each:,.2f} exceeds ${config.max_price_each:,.2f} per ticket")
        total = listing.price_each * config.quantity
        if config.max_order_total is not None and total > config.max_order_total:
            reasons.append(f"estimated total ${total:,.2f} exceeds ${config.max_order_total:,.2f}")
    return reasons


def qualify(listing: Listing, config: WatchConfig) -> Match | None:
    notes: list[str] = []
    similarity = event_similarity(config.event, listing.event_name)
    if rejection_reasons(listing, config):
        return None
    if config.must_be_together and listing.seats_together is None:
        notes.append("Seat adjacency is not supplied by this source")
    if listing.price_each is None:
        total = None
    else:
        total = listing.price_each * config.quantity
    if listing.fees_included is None:
        notes.append("Fees are unknown; total is an estimate")
    price_score = 0.5
    if listing.price_each is not None and config.max_price_each:
        price_score = max(0.0, 1 - listing.price_each / config.max_price_each)
    score = round(100 * (similarity * 0.75 + price_score * 0.25), 1)
    return Match(listing=listing, estimated_order_total=total, score=score, notes=tuple(notes))


def rank_matches(listings: list[Listing], config: WatchConfig) -> list[Match]:
    matches = [match for item in listings if (match := qualify(item, config))]
    return sorted(matches, key=lambda match: (-match.score, match.estimated_order_total or float("inf")))
