from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from playwright.sync_api import Response, sync_playwright
except ImportError:
    print("SETUP ERROR: Browser tools are not installed.")
    print("Double-click SETUP_BROWSER.bat first, then run this diagnostic again.")
    raise SystemExit(1)

from stubhub_diagnostic import MAX_BODY_BYTES, URL_HINTS, clean_url, extract_candidate_objects


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "stubhub_event_diagnostic.json"
EVENT_URL = "https://www.stubhub.com/los-angeles-lakers-los-angeles-tickets-1-7-2027/event/161689730/"
CAPTURE_SECONDS = 120


def main() -> int:
    print("=" * 60)
    print("STUBHUB EVENT INVENTORY DIAGNOSTIC V2")
    print("=" * 60)
    print("Event: Boston Celtics at Los Angeles Lakers")
    print("Date: January 7, 2027 at 7:00 PM")
    print("Venue: Crypto.com Arena")
    print("The exact StubHub event page will open automatically.")
    print("If a ticket-quantity selector appears, change it to 4 tickets.")
    print(f"Leave the page open for {CAPTURE_SECONDS} seconds while listings load.")
    print("Do not sign in, select a listing, or enter payment information.")

    captures: list[dict[str, Any]] = []
    errors: list[str] = []

    def inspect_response(response: Response) -> None:
        content_type = response.headers.get("content-type", "").casefold()
        lower_url = response.url.casefold()
        if "json" not in content_type and not any(hint in lower_url for hint in URL_HINTS):
            return
        try:
            body = response.body()
            if not body or len(body) > MAX_BODY_BYTES:
                return
            text = body.decode("utf-8", errors="replace")
            if "json" not in content_type and not text.lstrip().startswith(("{", "[")):
                return
            payload = json.loads(text)
            objects = extract_candidate_objects(payload)
            if objects:
                captures.append({
                    "url": clean_url(response.url),
                    "status": response.status,
                    "objects": objects[:5000],
                })
        except Exception as exc:
            if len(errors) < 30:
                errors.append(f"{clean_url(response.url)}: {type(exc).__name__}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("response", inspect_response)
        try:
            page.goto(EVENT_URL, wait_until="domcontentloaded", timeout=60_000)
            print("\nExact event page opened. Set the quantity to 4 if that option is shown.")
            page.wait_for_timeout(CAPTURE_SECONDS * 1000)
            title = page.title()
            final_url = clean_url(page.url)
            body_text = page.locator("body").inner_text(timeout=10_000)
            visible_prices = sorted(set(re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", body_text)))[:200]
            relevant_lines = [
                line.strip() for line in body_text.splitlines()
                if line.strip() and ("$" in line or re.search(r"\b(?:section|sec|row|ticket)s?\b", line, re.I))
            ][:400]
        except Exception as exc:
            title = page.title()
            final_url = clean_url(page.url)
            visible_prices = []
            relevant_lines = []
            errors.append(f"PAGE: {type(exc).__name__}: {exc}")
        finally:
            context.close()
            browser.close()

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expected_event_url": EVENT_URL,
        "page_title": title,
        "final_url": final_url,
        "visible_prices": visible_prices,
        "relevant_visible_lines": relevant_lines,
        "candidate_response_count": len(captures),
        "candidate_endpoints": sorted({capture["url"] for capture in captures}),
        "responses": captures,
        "errors": errors,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print("STUBHUB EVENT DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print(f"Page title: {title}")
    print(f"Final page: {final_url}")
    print(f"Visible prices found: {len(visible_prices)}")
    if visible_prices:
        print("Prices: " + ", ".join(visible_prices[:25]))
    print(f"Listing-related data responses: {len(captures)}")
    for endpoint in sorted({capture["url"] for capture in captures})[:30]:
        print(f"Data endpoint: {endpoint}")
    if errors:
        print(f"Nonfatal read errors: {len(errors)}")
    print(f"Diagnostic saved: {OUTPUT}")
    print("Send me this console output and upload stubhub_event_diagnostic.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
