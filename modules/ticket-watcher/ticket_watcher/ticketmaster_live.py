from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .ticketmaster_browser import TicketmasterOffer, parse_quickpicks

if TYPE_CHECKING:
    from playwright.sync_api import Page


@dataclass(frozen=True)
class BrowserInventoryResult:
    offers: list[TicketmasterOffer]
    selected_quantity: int
    page_title: str
    quickpicks_responses: int
    error: str = ""


def choose_quantity(page: "Page", quantity: int) -> str:
    label = f"{quantity} Tickets" if quantity != 1 else "1 Ticket"
    selects = page.locator("select")
    for index in range(selects.count()):
        select = selects.nth(index)
        options = select.locator("option").all_text_contents()
        if any("Ticket" in option for option in options) and any(label.casefold() == option.strip().casefold() for option in options):
            select.select_option(label=label, force=True)
            return label

    current = page.get_by_text(re.compile(r"^\s*\d+\s+Tickets?\s*$", re.I)).first
    current.click(timeout=10_000)
    page.get_by_text(re.compile(rf"^\s*{quantity}\s+Tickets?\s*$", re.I)).last.click(timeout=10_000)
    return label


def quantity_url(url: str, quantity: int) -> str:
    parts = urlsplit(url)
    parameters = parse_qsl(parts.query, keep_blank_values=True)
    replaced = False
    updated: list[tuple[str, str]] = []
    for key, value in parameters:
        if key.casefold() == "qty":
            updated.append((key, str(quantity)))
            replaced = True
        else:
            updated.append((key, value))
    if not replaced:
        updated.append(("qty", str(quantity)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(updated), parts.fragment))


def requested_quantity(url: str) -> int | None:
    for key, value in parse_qsl(urlsplit(url).query, keep_blank_values=True):
        if key.casefold() == "qty":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def fetch_inventory(event_url: str, quantity: int, headless: bool, offscreen: bool, page_wait_seconds: int) -> BrowserInventoryResult:
    from playwright.sync_api import sync_playwright

    quickpicks: list[dict[str, Any]] = []
    quickpick_urls: list[str] = []

    def capture(response: Any) -> None:
        if "/quickpicks" not in response.url:
            return
        try:
            quickpick_urls.append(response.url)
            payload = response.json()
            if isinstance(payload, dict):
                quickpicks.append(payload)
        except Exception:
            pass

    with sync_playwright() as playwright:
        launch_args = ["--window-position=-32000,-32000", "--window-size=1440,900"] if offscreen else []
        browser = playwright.chromium.launch(headless=headless, args=launch_args)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("response", capture)
        title = ""
        selected_quantity = 0
        error = ""
        try:
            page.goto(event_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(max(8_000, page_wait_seconds * 1000))
            title = page.title()
            if headless:
                if not quickpick_urls:
                    error = "Ticketmaster did not load its initial inventory request in headless mode"
                else:
                    request_url = quantity_url(quickpick_urls[-1], quantity)
                    api_response = context.request.get(request_url, headers={
                        "origin": "https://www.ticketmaster.com",
                        "referer": event_url,
                    }, timeout=30_000)
                    if api_response.ok:
                        payload = api_response.json()
                        if isinstance(payload, dict):
                            quickpicks.append(payload)
                            selected_quantity = quantity
                    else:
                        error = f"Direct four-ticket request returned HTTP {api_response.status}"
            else:
                before_count = len(quickpicks)
                before_urls = len(quickpick_urls)
                choose_quantity(page, quantity)
                page.wait_for_timeout(page_wait_seconds * 1000)
                if len(quickpicks) <= before_count:
                    page.wait_for_timeout(8_000)
                refreshed_urls = quickpick_urls[before_urls:]
                if any(requested_quantity(url) == quantity for url in refreshed_urls):
                    selected_quantity = quantity
            if selected_quantity == 0 and not error:
                error = f"Ticketmaster did not confirm the {quantity}-ticket selection"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            try:
                title = page.title()
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    offers = parse_quickpicks(quickpicks[-1]) if quickpicks and selected_quantity == quantity else []
    if not offers and not error:
        error = "No four-ticket inventory response was captured"
    return BrowserInventoryResult(
        offers=offers,
        selected_quantity=selected_quantity,
        page_title=title,
        quickpicks_responses=len(quickpicks),
        error=error,
    )
