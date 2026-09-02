from __future__ import annotations

import json
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


PROJECT = Path(__file__).resolve().parent
OUTPUT = PROJECT / "data" / "stubhub_diagnostic.json"
CAPTURE_SECONDS = 120
MAX_BODY_BYTES = 4_000_000
URL_HINTS = ("listing", "inventory", "ticket", "event", "catalog", "price", "section")
KEY_HINTS = (
    "amount", "available", "currency", "event", "fee", "listing", "price", "quantity",
    "row", "seat", "section", "ticket", "total",
)
SENSITIVE_KEY_PARTS = (
    "authorization", "cookie", "credential", "email", "password", "secret", "session", "token",
)


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def safe_primitive_fields(value: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for raw_key, child in value.items():
        key = str(raw_key)
        folded = key.casefold()
        if any(part in folded for part in SENSITIVE_KEY_PARTS):
            continue
        if isinstance(child, (str, int, float, bool, type(None))):
            if isinstance(child, str) and len(child) > 500:
                output[key] = child[:500] + "..."
            else:
                output[key] = child
        elif isinstance(child, list) and len(child) <= 30 and all(isinstance(item, (str, int, float, bool, type(None))) for item in child):
            output[key] = child
    return output


def extract_candidate_objects(value: Any, path: str = "$", depth: int = 0) -> list[dict[str, Any]]:
    if depth > 16:
        return []
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        folded_keys = [str(key).casefold() for key in value]
        if any(any(hint in key for hint in KEY_HINTS) for key in folded_keys):
            fields = safe_primitive_fields(value)
            if fields:
                found.append({"path": path, "fields": fields})
        for key, child in value.items():
            if any(part in str(key).casefold() for part in SENSITIVE_KEY_PARTS):
                continue
            found.extend(extract_candidate_objects(child, f"{path}.{key}", depth + 1))
    elif isinstance(value, list):
        for index, child in enumerate(value[:1000]):
            found.extend(extract_candidate_objects(child, f"{path}[{index}]", depth + 1))
    return found


def main() -> int:
    print("=" * 60)
    print("STUBHUB LISTING DIAGNOSTIC V1")
    print("=" * 60)
    print("A fresh StubHub browser will open.")
    print("Search for: Los Angeles Lakers vs Boston Celtics")
    print("Open the January 7, 2027 event at Crypto.com Arena.")
    print(f"The diagnostic will watch for listing data for {CAPTURE_SECONDS} seconds.")
    print("Do not sign in, select tickets, or enter payment information.")

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
                    "objects": objects[:3000],
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
            page.goto("https://www.stubhub.com/", wait_until="domcontentloaded", timeout=60_000)
            print("\nBrowser opened. Search for the event now...")
            page.wait_for_timeout(CAPTURE_SECONDS * 1000)
            title = page.title()
            final_url = clean_url(page.url)
            body_text = page.locator("body").inner_text(timeout=10_000)
            visible_prices = sorted(set(re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", body_text)))[:100]
            relevant_lines = [
                line.strip() for line in body_text.splitlines()
                if line.strip() and ("$" in line or re.search(r"\b(?:section|sec|row|ticket)s?\b", line, re.I))
            ][:200]
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
    print("STUBHUB DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print(f"Page title: {title}")
    print(f"Final page: {final_url}")
    print(f"Visible prices found: {len(visible_prices)}")
    if visible_prices:
        print("Prices: " + ", ".join(visible_prices[:20]))
    print(f"Listing-related data responses: {len(captures)}")
    for endpoint in sorted({capture["url"] for capture in captures})[:25]:
        print(f"Data endpoint: {endpoint}")
    if errors:
        print(f"Nonfatal read errors: {len(errors)}")
    print(f"Diagnostic saved: {OUTPUT}")
    print("Send me this console output and upload stubhub_diagnostic.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
