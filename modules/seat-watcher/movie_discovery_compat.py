"""Compatibility layer for AMC movie-title discovery.

The legacy V44/V44.7 flow is preserved. This module only broadens the title
extraction/route fallback used by the Find Movies button when AMC's rendered
showtimes markup no longer exposes the historical /movies/ links.
"""
from __future__ import annotations

import asyncio
import re

from playwright.async_api import async_playwright

from seat_watcher_v44 import (
    MAX_CONCURRENT_DISCOVERY,
    build_amc_url,
    normalize_movie_name,
)


# Known current AMC canonical-route exceptions observed during the Sept. 8, 2026
# Mac acceptance pass. Existing theater_url values are still tried first.
CANONICAL_SHOWTIME_URL_OVERRIDES = {
    "amc-topanga-12": (
        "https://www.amctheatres.com/movie-theatres/los-angeles/"
        "amc-dine-in-topanga-12/showtimes"
    ),
    "amc-fallbrook-7": (
        "https://www.amctheatres.com/movie-theatres/amc-fallbrook-7/"
        "amc-fallbrook-7/showtimes"
    ),
}

_RUNTIME_RE = re.compile(r"\b\d+\s*HR(?:\s+\d+\s*MIN)?\b", re.I)

_BAD_TITLE_EXACT = {
    "movies",
    "showtimes",
    "tickets",
    "learn more",
    "view details",
    "digital",
    "sign in",
    "join",
}

_BAD_TITLE_PARTS = (
    " at amc",
    "picture a better world",
    "completely captivating",
    "premium 3d experience",
    "reserved seating",
    "closed caption",
    "audio description",
    "movies start ",
    "no remaining showtimes",
    "try tomorrow",
)


def extract_link_title(text: str) -> str | None:
    """Preserve the compact-link extraction V44 already used."""
    value = str(text or "").strip()
    if not value or len(value) > 140:
        return None
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return None
    title = lines[0]
    if len(title) < 2 or title.lower() in _BAD_TITLE_EXACT:
        return None
    return title


def heading_looks_like_movie_title(title: str, nearby_text: str, theater_name: str = "") -> bool:
    """Recognize a rendered movie heading by the runtime evidence beside it."""
    title = str(title or "").strip()
    nearby_text = str(nearby_text or "")
    if not title or len(title) < 2 or len(title) > 140:
        return False

    lower = title.lower()
    if lower in _BAD_TITLE_EXACT:
        return False
    if lower.startswith("amc "):
        return False
    if theater_name and normalize_movie_name(title) == normalize_movie_name(theater_name):
        return False
    if any(part in lower for part in _BAD_TITLE_PARTS):
        return False
    if re.fullmatch(r"(?:g|pg|pg13|pg-13|r|nc-17|nr)", title, re.I):
        return False

    return bool(_RUNTIME_RE.search(nearby_text))


def candidate_showtime_urls(theater: dict) -> list[str]:
    """Keep the saved route first, then try narrow current AMC fallbacks."""
    candidates: list[str] = []

    existing = str(theater.get("theater_url") or "").strip()
    if existing:
        existing = existing.rstrip("/")
        if not existing.endswith("/showtimes"):
            existing += "/showtimes"
        candidates.append(existing)
    else:
        slug = str(theater.get("slug") or "").strip()
        if slug:
            candidates.append(build_amc_url(slug))

    slug = str(theater.get("slug") or "").strip()
    override = CANONICAL_SHOWTIME_URL_OVERRIDES.get(slug)
    if override:
        candidates.append(override)

    if slug:
        candidates.append(
            f"https://www.amctheatres.com/movie-theatres/los-angeles/{slug}/showtimes"
        )

    unique: list[str] = []
    seen = set()
    for url in candidates:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


async def _titles_from_legacy_links(page) -> list[str]:
    links = page.locator('a[href*="/movies/"]')
    movies: list[str] = []
    for index in range(await links.count()):
        try:
            title = extract_link_title(await links.nth(index).inner_text())
            if title:
                movies.append(title)
        except Exception:
            continue
    return movies


async def _titles_from_rendered_headings(page, theater_name: str) -> list[str]:
    """Fallback for AMC pages that render titles without legacy /movies/ anchors."""
    headings = page.locator("h1, h2, h3, h4")
    movies: list[str] = []

    for index in range(await headings.count()):
        heading = headings.nth(index)
        try:
            title = (await heading.inner_text()).strip()
            evidence = await heading.evaluate(
                """
                (el) => {
                  const chunks = [];
                  let node = el.nextElementSibling;
                  let steps = 0;
                  while (node && steps < 5) {
                    if (/^H[1-4]$/.test(node.tagName)) break;
                    chunks.push(node.innerText || '');
                    if (chunks.join('\n').length > 500) break;
                    node = node.nextElementSibling;
                    steps += 1;
                  }
                  if (chunks.join('\n').trim()) return chunks.join('\n');
                  return (el.parentElement && el.parentElement.innerText) || '';
                }
                """
            )
            if heading_looks_like_movie_title(title, evidence, theater_name):
                movies.append(title)
        except Exception:
            continue

    return movies


async def discover_movies_at_theater_compat(browser, theater, semaphore, emit=None):
    async with semaphore:
        def say(message):
            if emit:
                emit(message)

        say(f"Checking movies: {theater['name']}")

        for attempt, theater_url in enumerate(candidate_showtime_urls(theater)):
            page = None
            try:
                page = await browser.new_page()
                await page.goto(theater_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(900)

                movies = await _titles_from_legacy_links(page)
                if not movies:
                    movies = await _titles_from_rendered_headings(page, theater.get("name", ""))

                if movies:
                    if attempt:
                        say(f"Movie discovery route refreshed for {theater['name']}.")
                    return movies
            except Exception:
                pass
            finally:
                try:
                    if page:
                        await page.close()
                except Exception:
                    pass

        return []


async def discover_movies_for_theaters(theaters, emit=None):
    """Drop-in replacement for V44's Find Movies discovery boundary."""
    if not theaters:
        raise ValueError("Select at least one theater first.")

    def say(message):
        if emit:
            emit(message)

    say(f"Finding movies across {len(theaters)} selected theaters...")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            semaphore = asyncio.Semaphore(
                min(MAX_CONCURRENT_DISCOVERY, max(1, len(theaters)))
            )
            results = await asyncio.gather(
                *[
                    discover_movies_at_theater_compat(
                        browser, theater, semaphore, emit=emit
                    )
                    for theater in theaters
                ],
                return_exceptions=True,
            )
        finally:
            await browser.close()

    unique = {}
    for result in results:
        if not isinstance(result, list):
            continue
        for title in result:
            normalized = normalize_movie_name(title)
            if normalized:
                unique.setdefault(normalized, title.strip())

    movies = sorted(unique.values(), key=lambda value: value.lower())
    if not movies:
        raise RuntimeError("No movie titles were found at the selected theaters.")

    say(f"Found {len(movies)} unique movies.")
    return movies
