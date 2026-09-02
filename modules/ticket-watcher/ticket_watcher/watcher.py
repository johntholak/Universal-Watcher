from __future__ import annotations

import json
import time
import webbrowser
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .matcher import rank_matches, rejection_reasons
from .models import Listing, Match, WatchConfig


class Source(Protocol):
    name: str
    def search(self, config: WatchConfig) -> list[Listing]: ...


def run(config: WatchConfig, sources: list[Source], once: bool = False) -> Match | None:
    cycle = 0
    while True:
        cycle += 1
        print(f"\n{'=' * 56}\nSEARCH CYCLE {cycle}  {datetime.now().astimezone():%Y-%m-%d %I:%M:%S %p}\n{'=' * 56}")
        listings: list[Listing] = []
        for source in sources:
            try:
                found = source.search(config)
                listings.extend(found)
                print(f"{source.name}: {len(found)} events found")
            except Exception as exc:
                print(f"{source.name}: ERROR - {exc}")
        matches = rank_matches(listings, config)
        if matches:
            best = matches[0]
            announce(best, config)
            save_match(best)
            if config.open_browser_on_match and best.listing.event_url:
                webbrowser.open(best.listing.event_url)
            if config.stop_after_match or once:
                return best
        else:
            print("No qualifying ticket offers found.")
            show_rejected(listings, config)
        if once:
            return None
        print(f"Checking again in {config.check_every_seconds} seconds. Press Ctrl+C to stop.")
        time.sleep(config.check_every_seconds)


def show_rejected(listings: list[Listing], config: WatchConfig) -> None:
    if not listings:
        return
    print("\nClosest event results:")
    for item in listings[:5]:
        price = f"{item.currency} {item.price_each:,.2f}" if item.price_each is not None else "not published"
        distance = f" | {item.distance_miles:.1f} miles" if item.distance_miles is not None else ""
        starts = item.starts_at.astimezone().strftime("%a %b %d, %Y at %I:%M %p") if item.starts_at else "date unavailable"
        print(f"- {item.event_name}")
        print(f"  {item.venue}, {item.city}{distance}")
        print(f"  {starts} | advertised minimum: {price}")
        for reason in rejection_reasons(item, config):
            print(f"  Rejected: {reason}")


def announce(match: Match, config: WatchConfig) -> None:
    item = match.listing
    if config.sound_alert:
        print("\a" * 3, end="")
    price = f"{item.currency} {item.price_each:,.2f}" if item.price_each is not None else "Unknown"
    total = f"{item.currency} {match.estimated_order_total:,.2f}" if match.estimated_order_total is not None else "Unknown"
    print(f"\nBEST MATCH FOUND\nSource: {item.source}\nEvent: {item.event_name}\nVenue: {item.venue}, {item.city}")
    if item.distance_miles is not None:
        print(f"Distance: {item.distance_miles:.1f} miles")
    print(f"Starts: {item.starts_at.astimezone():%a %b %d, %Y at %I:%M %p}" if item.starts_at else "Starts: Unknown")
    print(f"Advertised price each: {price}\nEstimated {config.quantity}-ticket total: {total}\nMatch score: {match.score}/100")
    for note in match.notes:
        print(f"Note: {note}")
    print(f"Purchase page: {item.event_url}")


def save_match(match: Match) -> None:
    output = Path("data/matches.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(match)
    payload["found_at"] = datetime.now(timezone.utc).isoformat()
    if match.listing.starts_at:
        payload["listing"]["starts_at"] = match.listing.starts_at.isoformat()
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
