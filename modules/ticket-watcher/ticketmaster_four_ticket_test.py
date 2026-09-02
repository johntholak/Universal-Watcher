from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import Page, Response, sync_playwright
except ImportError:
    print("SETUP ERROR: Browser tools are not installed.")
    print("Double-click SETUP_BROWSER.bat first, then run this test again.")
    raise SystemExit(1)

from ticket_watcher.config import load_config, load_dotenv
from ticket_watcher.sources.ticketmaster import TicketmasterSource
from ticket_watcher.ticketmaster_browser import parse_quickpicks


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "four_ticket_test.json"


def choose_quantity(page: Page, quantity: int) -> str:
    label = f"{quantity} Tickets" if quantity != 1 else "1 Ticket"
    selects = page.locator("select")
    for index in range(selects.count()):
        select = selects.nth(index)
        options = select.locator("option").all_text_contents()
        if any("Ticket" in option for option in options) and any(label.casefold() == option.strip().casefold() for option in options):
            select.select_option(label=label, force=True)
            return "native ticket selector"

    current = page.get_by_text(re.compile(r"^\s*\d+\s+Tickets?\s*$", re.I)).first
    current.click(timeout=10_000)
    page.get_by_text(re.compile(rf"^\s*{quantity}\s+Tickets?\s*$", re.I)).last.click(timeout=10_000)
    return "ticket menu"


def main() -> int:
    os.chdir(PROJECT)
    load_dotenv(PROJECT / ".env")
    config = load_config(PROJECT / "watch.json")
    source = TicketmasterSource(os.getenv("TICKETMASTER_API_KEY", ""))
    events = source.search(config)
    if not events:
        print("No Ticketmaster event was found.")
        return 1
    event = max(events, key=lambda item: item.event_match)
    print("=" * 60)
    print("TICKETMASTER FOUR-TICKET EXTRACTION TEST")
    print("=" * 60)
    print(f"Event: {event.event_name}")
    print(f"Venue: {event.venue}, {event.city}")
    print(f"Tickets requested: {config.quantity}")
    print(f"Maximum price each: ${config.max_price_each:,.2f}" if config.max_price_each else "Maximum price each: None")
    print("\nOpening Ticketmaster and changing the ticket quantity...")

    quickpicks: list[dict[str, Any]] = []
    errors: list[str] = []

    def capture(response: Response) -> None:
        if "/quickpicks" not in response.url:
            return
        try:
            quickpicks.append(response.json())
        except Exception as exc:
            errors.append(f"Quickpicks read error: {type(exc).__name__}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("response", capture)
        try:
            page.goto(event.event_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(12_000)
            before_count = len(quickpicks)
            method = choose_quantity(page, config.quantity)
            print(f"Quantity changed using: {method}")
            page.wait_for_timeout(20_000)
            if len(quickpicks) <= before_count:
                print("No new quickpicks response arrived after changing quantity; waiting once more.")
                page.wait_for_timeout(15_000)
            selected_text = page.get_by_text(re.compile(rf"^\s*{config.quantity}\s+Tickets?\s*$", re.I)).first.inner_text(timeout=5_000)
            print(f"Ticketmaster now shows: {selected_text.strip()}")
        except Exception as exc:
            errors.append(f"Page error: {type(exc).__name__}: {exc}")
        finally:
            context.close()
            browser.close()

    payload = quickpicks[-1] if quickpicks else {}
    offers = parse_quickpicks(payload)
    qualifying = [offer for offer in offers if config.max_price_each is None or offer.all_in_price <= config.max_price_each]

    report = {
        "event": event.event_name,
        "tickets_requested": config.quantity,
        "quickpicks_responses": len(quickpicks),
        "offers_parsed": len(offers),
        "qualifying_offers": len(qualifying),
        "cheapest": [offer.__dict__ for offer in offers[:25]],
        "errors": errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("FOUR-TICKET RESULTS")
    print("=" * 60)
    print(f"Quickpicks responses captured: {len(quickpicks)}")
    print(f"Four-ticket offers parsed: {len(offers)}")
    print(f"Offers at or below ${config.max_price_each:,.2f}: {len(qualifying)}" if config.max_price_each else f"Offers parsed: {len(offers)}")
    if offers:
        print("\nCheapest four-ticket options, all-in before taxes:")
        for offer in offers[:10]:
            print(f"  Section {offer.section} | Row {offer.row} | ${offer.all_in_price:,.2f} each (${offer.base_price:,.2f} + ${offer.charges:,.2f} charges)")
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  {error}")
    print(f"\nReport saved: {OUTPUT}")
    print("Send me the complete console output.")
    return 0 if offers else 1


if __name__ == "__main__":
    raise SystemExit(main())
