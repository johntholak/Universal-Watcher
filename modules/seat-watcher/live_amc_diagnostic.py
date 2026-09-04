"""Headless live diagnostic for the protected AMC Movies engine."""
import argparse
import asyncio
import json
import threading
from datetime import date, timedelta

from playwright.async_api import async_playwright

from seat_watcher_v44 import (
    DEFAULT_SETTINGS,
    WatcherEngine,
    normalize_amc_api_theaters,
    summarize_inventory_results,
)


CITYWALK = {
    "name": "AMC Universal CityWalk 19",
    "slug": "universal-cinema-an-amc-theatre",
    "theater_url": (
        "https://www.amctheatres.com/movie-theatres/los-angeles/"
        "universal-cinema-an-amc-theatre"
    ),
    "distance": 0.0,
    "lat": 34.1381,
    "lon": -118.3529,
}


async def run_diagnostic(start_date, days, check_seats, headed, theatre_slugs=None,
                         movie="The Odyssey", requested_format="IMAX 70MM"):
    settings = dict(DEFAULT_SETTINGS)
    settings.update({
        "movie": movie,
        "format": requested_format,
        "earliest_time": "12:00am",
        "latest_time": "11:59pm",
        "seats_required": 4,
        "minimum_row": 5,
        "date_mode": "SPECIFIC DATE",
        "date_start": start_date.isoformat(),
        "enabled_theaters": [CITYWALK["name"]],
        "theaters": [CITYWALK],
        "diagnostic_logging": True,
    })
    log = []

    def emit(message):
        line = str(message)
        log.append(line)
        print(line, flush=True)

    engine = WatcherEngine(
        settings,
        emit,
        lambda message: emit(f"STATUS: {message}"),
        threading.Event(),
        lambda match: emit(f"MATCH: {json.dumps(match, default=str)}"),
    )

    theaters = [CITYWALK]
    if theatre_slugs:
        if engine.amc_api_client is None:
            raise ValueError("Explicit theater diagnostics require an approved AMC catalog key")
        catalog = await asyncio.to_thread(engine.amc_api_client.list_theatres)
        theaters = []
        for slug in dict.fromkeys(theatre_slugs):
            record = next((t for t in catalog if t.get("slug") == slug), None)
            if record is None:
                raise ValueError(f"Theater not found in AMC catalog: {slug}")
            theaters.extend(normalize_amc_api_theaters(
                [record], record["location"]["latitude"], record["location"]["longitude"], 1
            ))
    totals = dict(discovery_checks=0, discovery_unavailable=0, showtimes=0,
                  seat_checks=0, matches=0, captured_no_match=0, inventory_unavailable=0)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        try:
            for theater, offset in ((t, d) for t in theaters for d in range(days)):
                search_date = (start_date + timedelta(days=offset)).isoformat()
                print(f"\n=== {theater['name']} | {search_date} ===", flush=True)
                engine.discovery_failures = []
                showtimes = await engine.discover_theater(
                    browser, theater, search_date, asyncio.Semaphore(1)
                )
                totals["discovery_checks"] += 1
                totals["discovery_unavailable"] += len(engine.discovery_failures)
                totals["showtimes"] += len(showtimes)
                print(
                    "DISCOVERY RESULT: "
                    + json.dumps(showtimes, indent=2, default=str),
                    flush=True,
                )
                if check_seats and showtimes:
                    results = []
                    for showtime in showtimes:
                        result = await engine.check_showtime(browser, showtime, asyncio.Semaphore(1))
                        results.append(result)
                        print("INVENTORY RESULT: " + json.dumps(result, default=str), flush=True)
                    matches, captured, unavailable, errors = (
                        summarize_inventory_results(results)
                    )
                    totals["seat_checks"] += len(results)
                    totals["matches"] += len(matches)
                    totals["captured_no_match"] += captured
                    totals["inventory_unavailable"] += unavailable
                    print(
                        "INVENTORY SUMMARY: "
                        f"matches={len(matches)} captured_no_match={captured} "
                        f"unavailable={unavailable} task_errors={errors}",
                        flush=True,
                    )
        finally:
            await browser.close()
    print("RUN SUMMARY (capture success is not accuracy): " + json.dumps(totals), flush=True)
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=date.today().isoformat())
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--check-seats", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--theatre-slug", action="append",
                        help="Repeat for multiple official AMC slugs; requires catalog access")
    parser.add_argument("--movie", default="The Odyssey")
    parser.add_argument("--format", default="IMAX 70MM")
    args = parser.parse_args()
    if not 1 <= args.days <= 35:
        parser.error("--days must be between 1 and 35; no dates are silently discarded")
    asyncio.run(
        run_diagnostic(
            date.fromisoformat(args.start),
            args.days,
            args.check_seats,
            args.headed,
            args.theatre_slug,
            args.movie,
            args.format,
        )
    )


if __name__ == "__main__":
    main()
