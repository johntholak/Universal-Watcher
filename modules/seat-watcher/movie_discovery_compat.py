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


# Current canonical showtime routes for the local acceptance theatres. Existing
# theater_url values are still tried first so previously saved data keeps working.
CANONICAL_SHOWTIME_URL_OVERRIDES = {
    "amc-topanga-12": (
        "https://www.amctheatres.com/movie-theatres/los-angeles/"
        "amc-topanga-12/showtimes"
    ),
    "amc-fallbrook-7": (
        "https://www.amctheatres.com/movie-theatres/west-hills/"
        "amc-fallbrook-7/showtimes"
    ),
    "amc-northridge-10": (
        "https://www.amctheatres.com/movie-theatres/los-angeles/"
        "amc-northridge-10/showtimes"
    ),
    "amc-porter-ranch-9": (
        "https://www.amctheatres.com/movie-theatres/los-angeles/"
        "amc-porter-ranch-9/showtimes"
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
    "get tickets",
    "movie info",
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
    "movies showing",
    "no remaining showtimes",
    "try tomorrow",
    "trailers and info",
    "showtimes & movie tickets",
)


def _basic_title_shape(title: str, theater_name: str = "") -> bool:
    title = str(title or "").strip()
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
    return True


def extract_link_title(text: str) -> str | None:
    """Preserve the compact-link extraction V44 already used."""
    value = str(text or "").strip()
    if not value or len(value) > 140:
        return None
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if not lines:
        return None
    title = lines[0]
    return title if _basic_title_shape(title) else None


def heading_looks_like_movie_title(title: str, nearby_text: str, theater_name: str = "") -> bool:
    """Legacy-compatible heading check using nearby runtime evidence."""
    if not _basic_title_shape(title, theater_name):
        return False
    return bool(_RUNTIME_RE.search(str(nearby_text or "")))


def h1_looks_like_movie_title(title: str, theater_name: str = "") -> bool:
    """AMC's current showtimes page renders each movie name as an H1."""
    return _basic_title_shape(title, theater_name)


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


async def _titles_from_current_h1s(page, theater_name: str) -> list[str]:
    """Read AMC's current server-rendered movie-title structure directly."""
    headings = page.locator("h1")
    movies: list[str] = []
    for index in range(await headings.count()):
        try:
            title = (await headings.nth(index).inner_text()).strip()
            if h1_looks_like_movie_title(title, theater_name):
                movies.append(title)
        except Exception:
            continue
    return movies


async def _titles_from_rendered_headings(page, theater_name: str) -> list[str]:
    """Fallback when a page uses other heading levels around movie cards."""
    headings = page.locator("h1, h2, h3, h4")
    movies: list[str] = []

    for index in range(await headings.count()):
        heading = headings.nth(index)
        try:
            title = (await heading.inner_text()).strip()
            evidence = await heading.evaluate(
                """
                (el) => {
                  const parent = el.parentElement;
                  return (parent && parent.innerText) || '';
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
                try:
                    await page.wait_for_selector("h1", timeout=5000)
                except Exception:
                    pass
                await page.wait_for_timeout(500)

                # Preserve V44 first. AMC's current H1 movie-title structure is
                # the compatibility path that follows it.
                movies = await _titles_from_legacy_links(page)
                if not movies:
                    movies = await _titles_from_current_h1s(
                        page, theater.get("name", "")
                    )
                if not movies:
                    movies = await _titles_from_rendered_headings(
                        page, theater.get("name", "")
                    )

                if movies:
                    if attempt:
                        say(f"Movie discovery route refreshed for {theater['name']}.")
                    say(f"  Found {len(set(movies))} movie titles at {theater['name']}.")
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
