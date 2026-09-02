from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    from playwright.sync_api import Response, sync_playwright
except ImportError:
    print("SETUP ERROR: Browser tools are not installed.")
    print("Double-click SETUP_BROWSER.bat first, then run this diagnostic again.")
    raise SystemExit(1)

from ticket_watcher.config import load_config, load_dotenv
from ticket_watcher.sources.ticketmaster import TicketmasterSource


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "ticketmaster_diagnostic.json"
MAX_BODY_BYTES = 2_000_000
INTERESTING_URL_WORDS = ("offer", "price", "inventory", "ticket", "seat", "event", "quickpicks")
INTERESTING_KEYS = {
    "amount", "currency", "displayprice", "facevalue", "fee", "fees", "inventory",
    "listprice", "offer", "offers", "price", "prices", "quantity", "row", "seat",
    "seats", "section", "standardprice", "total", "value",
}


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def extract_fields(value: Any, path: str = "$", depth: int = 0) -> list[dict[str, Any]]:
    if depth > 14:
        return []
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        selected = {str(k): v for k, v in value.items() if str(k).casefold() in INTERESTING_KEYS and isinstance(v, (str, int, float, bool, type(None)))}
        if selected:
            found.append({"path": path, "fields": selected})
        for key, child in value.items():
            found.extend(extract_fields(child, f"{path}.{key}", depth + 1))
    elif isinstance(value, list):
        for index, child in enumerate(value[:500]):
            found.extend(extract_fields(child, f"{path}[{index}]", depth + 1))
    return found


def main() -> int:
    os.chdir(PROJECT)
    load_dotenv(PROJECT / ".env")
    config = load_config(PROJECT / "watch.json")
    source = TicketmasterSource(os.getenv("TICKETMASTER_API_KEY", ""))

    print("Locating the Ticketmaster event...")
    events = source.search(config)
    if not events:
        print("No Ticketmaster event was found.")
        return 1
    event = max(events, key=lambda item: item.event_match)
    print(f"Event: {event.event_name}")
    print(f"Venue: {event.venue}, {event.city}")
    print(f"Event page: {event.event_url}")
    print("\nOpening a fresh Ticketmaster browser for 75 seconds.")
    print("Do not sign in or enter payment information during this diagnostic.")

    captured: list[dict[str, Any]] = []
    errors: list[str] = []

    def inspect_response(response: Response) -> None:
        content_type = response.headers.get("content-type", "").casefold()
        lower_url = response.url.casefold()
        interesting_url = any(word in lower_url for word in INTERESTING_URL_WORDS)
        if "json" not in content_type and not interesting_url:
            return
        try:
            body = response.body()
            if not body or len(body) > MAX_BODY_BYTES:
                return
            text = body.decode("utf-8", errors="replace")
            if "json" not in content_type and not text.lstrip().startswith(("{", "[")):
                return
            payload = json.loads(text)
            fields = extract_fields(payload)
            if fields:
                captured.append({
                    "url": clean_url(response.url),
                    "status": response.status,
                    "content_type": content_type,
                    "fields": fields[:1000],
                })
        except Exception as exc:
            if len(errors) < 20:
                errors.append(f"{clean_url(response.url)}: {type(exc).__name__}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("response", inspect_response)
        try:
            page.goto(event.event_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(75_000)
            title = page.title()
            visible_text = page.locator("body").inner_text(timeout=10_000)
            visible_prices = sorted(set(re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", visible_text)))[:100]
            final_url = clean_url(page.url)
        except Exception as exc:
            title = page.title()
            visible_prices = []
            final_url = clean_url(page.url)
            errors.append(f"PAGE: {type(exc).__name__}: {exc}")
        finally:
            context.close()
            browser.close()

    unique_endpoints = sorted({item["url"] for item in captured})
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event": event.event_name,
        "venue": event.venue,
        "event_url": clean_url(event.event_url),
        "final_url": final_url,
        "page_title": title,
        "visible_prices": visible_prices,
        "candidate_response_count": len(captured),
        "candidate_endpoints": unique_endpoints,
        "responses": captured,
        "errors": errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print("TICKETMASTER DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print(f"Page title: {title}")
    print(f"Final page: {final_url}")
    print(f"Visible prices found: {len(visible_prices)}")
    if visible_prices:
        print("Prices: " + ", ".join(visible_prices[:20]))
    print(f"Listing-related data responses: {len(captured)}")
    for endpoint in unique_endpoints[:20]:
        print(f"Data endpoint: {endpoint}")
    if errors:
        print(f"Nonfatal read errors: {len(errors)}")
    print(f"Diagnostic saved: {OUTPUT}")
    print("Send me the complete console output shown above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
