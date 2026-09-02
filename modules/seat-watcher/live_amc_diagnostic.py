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
    chrome_user_agent,
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


async def run_diagnostic(start_date, days, check_seats, headed):
    settings = dict(DEFAULT_SETTINGS)
    settings.update({
        "movie": "The Odyssey",
        "format": "IMAX 70MM",
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

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not headed)
        try:
            for offset in range(days):
                search_date = (start_date + timedelta(days=offset)).isoformat()
                print(f"\n=== {search_date} ===", flush=True)
                showtimes = await engine.discover_theater(
                    browser, CITYWALK, search_date, asyncio.Semaphore(1)
                )
                print(
                    "DISCOVERY RESULT: "
                    + json.dumps(showtimes, indent=2, default=str),
                    flush=True,
                )
                if check_seats and showtimes:
                    results = []
                    for showtime in showtimes:
                        results.append(
                            await engine.check_showtime(
                                browser, showtime, asyncio.Semaphore(1)
                            )
                        )
                    matches, captured, unavailable, errors = (
                        summarize_inventory_results(results)
                    )
                    print(
                        "INVENTORY SUMMARY: "
                        f"matches={len(matches)} captured_no_match={captured} "
                        f"unavailable={unavailable} task_errors={errors}",
                        flush=True,
                    )
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=date.today().isoformat())
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--check-seats", action="store_true")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        run_diagnostic(
            date.fromisoformat(args.start),
            max(1, min(args.days, 35)),
            args.check_seats,
            args.headed,
        )
    )


if __name__ == "__main__":
    main()
