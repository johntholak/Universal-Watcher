from __future__ import annotations

import argparse
import json
import os
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

try:
    import playwright.sync_api  # noqa: F401
except ImportError:
    print("SETUP ERROR: Browser tools are not installed.")
    print("Double-click SETUP_BROWSER.bat first, then start the watcher again.")
    raise SystemExit(1)

from ticket_watcher.ticketmaster_live import fetch_inventory

from ticket_watcher.config import load_config, load_dotenv
from ticket_watcher.sources.ticketmaster import TicketmasterSource


PROJECT = Path(__file__).resolve().parent
HISTORY = PROJECT / "data" / "ticketmaster_watch_history.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch live Ticketmaster browser inventory.")
    parser.add_argument("--once", action="store_true", help="Run one browser inventory cycle and exit")
    args = parser.parse_args()
    os.chdir(PROJECT)
    load_dotenv(PROJECT / ".env")
    config = load_config(PROJECT / "watch.json")
    source = TicketmasterSource(os.getenv("TICKETMASTER_API_KEY", ""))

    print("=" * 60)
    print("TICKETMASTER LIVE WATCHER V1.9")
    print("=" * 60)
    print(f"Event: {config.event}")
    print(f"Radius: {config.radius_miles:,.0f} miles" if config.radius_miles else "Radius: Not set")
    print(f"Tickets: {config.quantity} together")
    print(f"Maximum all-in price: ${config.max_price_each:,.2f} each" if config.max_price_each else "Maximum price: None")
    mode = "HEADLESS" if config.browser_headless else ("OFFSCREEN" if config.browser_offscreen else "VISIBLE")
    print(f"Search browser: {mode}")
    print(f"Check interval: {config.check_every_seconds} seconds")
    print("Browser opens only after a qualifying offer is found.")

    events = source.search(config)
    if not events:
        print("No matching Ticketmaster event was discovered.")
        return 1
    event = max(events, key=lambda item: item.event_match)
    print(f"\nWatching: {event.event_name}")
    print(f"Venue: {event.venue}, {event.city}")
    if event.distance_miles is not None:
        print(f"Distance: {event.distance_miles:.1f} miles")
    print(f"Event page: {event.event_url}")

    cycle = 0
    while True:
        cycle += 1
        print(f"\n{'=' * 60}\nSEARCH CYCLE {cycle}  {datetime.now().astimezone():%Y-%m-%d %I:%M:%S %p}\n{'=' * 60}")
        result = fetch_inventory(
            event_url=event.event_url,
            quantity=config.quantity,
            headless=config.browser_headless,
            offscreen=config.browser_offscreen,
            page_wait_seconds=config.browser_page_wait_seconds,
        )
        if result.error:
            print(f"Ticketmaster inventory read failed: {result.error}")
        else:
            offers = result.offers
            qualifying = [offer for offer in offers if config.max_price_each is None or offer.all_in_price <= config.max_price_each]
            cheapest = offers[0]
            print(f"Four-ticket offers found: {len(offers)}")
            print(f"Cheapest: Section {cheapest.section} | Row {cheapest.row} | ${cheapest.all_in_price:,.2f} each, fees included before taxes")
            print(f"Offers at or below ${config.max_price_each:,.2f}: {len(qualifying)}" if config.max_price_each else f"Qualifying offers: {len(qualifying)}")
            save_cycle(event.event_name, config.quantity, offers, qualifying)
            if qualifying:
                best = qualifying[0]
                if config.sound_alert:
                    print("\a" * 5, end="")
                print("\n" + "!" * 60)
                print("QUALIFYING FOUR-TICKET OFFER FOUND")
                print("!" * 60)
                print(f"Section: {best.section}")
                print(f"Row: {best.row}")
                print(f"All-in price each: ${best.all_in_price:,.2f}")
                print(f"Estimated four-ticket total: ${best.all_in_price * config.quantity:,.2f} before taxes")
                if config.open_browser_on_match:
                    print("Opening the Ticketmaster event page...")
                    webbrowser.open(event.event_url)
                return 0

        if args.once:
            return 0 if result.offers else 1
        print(f"Checking again in {config.check_every_seconds} seconds. Press Ctrl+C to stop.")
        time.sleep(config.check_every_seconds)


def save_cycle(event_name, quantity, offers, qualifying) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        "quantity": quantity,
        "offer_count": len(offers),
        "qualifying_count": len(qualifying),
        "cheapest": offers[0].__dict__ if offers else None,
    }
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nWatcher stopped.")
        raise SystemExit(0)
