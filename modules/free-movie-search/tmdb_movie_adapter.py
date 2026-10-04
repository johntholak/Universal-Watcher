"""TMDB/JustWatch availability adapter for Movie GM.

TMDB's watch-provider data is powered by JustWatch. This adapter uses the
official TMDB API as a discovery/availability source and converts only the
returned US streaming offers into normalized MovieCandidate records.

No credentials are stored in source control. Set TMDB_READ_ACCESS_TOKEN in the
runtime environment. If it is missing, the adapter fails closed.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from workers import fetch
except ImportError:  # Local test environment
    fetch = None

from .free_movie_search import FreeOffer, MovieCandidate, RatingEvidence
from .movie_gm_pipeline import ProviderBatch


GENRE_NAMES = {
    12: "Adventure", 14: "Fantasy", 16: "Animation", 18: "Drama",
    27: "Horror", 28: "Action", 35: "Comedy", 36: "History",
    37: "Western", 53: "Thriller", 80: "Crime", 99: "Documentary",
    878: "Science Fiction", 9648: "Mystery", 10402: "Music",
    10749: "Romance", 10751: "Family", 10752: "War",
}


@dataclass(frozen=True)
class TMDBConfig:
    token: str
    region: str = "US"
    language: str = "en-US"
    page_size: int = 20
    timeout_seconds: int = 20


class TMDBMovieAdapter:
    provider = "TMDB/JustWatch"

    def __init__(self, config: TMDBConfig | None = None):
        token = (config.token if config else os.getenv("TMDB_READ_ACCESS_TOKEN", "")).strip()
        if not token:
            raise ValueError("TMDB_READ_ACCESS_TOKEN is required")
        self.config = config or TMDBConfig(token=token)

    async def _get_async(self, path: str, params: dict[str, str | int]) -> dict:
        query = urlencode(params)
        response = await fetch(
            f"https://api.themoviedb.org/3{path}?{query}",
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "accept": "application/json",
            },
        )
        if not response.ok:
            raise RuntimeError(f"TMDB HTTP {response.status}")
        return await response.json()

    def _get(self, path: str, params: dict[str, str | int]) -> dict:
        query = urlencode(params)
        request = Request(
            f"https://api.themoviedb.org/3{path}?{query}",
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "accept": "application/json",
            },
        )
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _discover_params(self, *, mode: str = "") -> dict[str, str | int]:
        params: dict[str, str | int] = {"include_adult": "false", "include_video": "false", "language": self.config.language, "region": self.config.region, "watch_region": self.config.region, "with_watch_monetization_types": "free|ads|flatrate", "sort_by": "popularity.desc", "page": 1}
        if mode.casefold().strip() == "kids":
            params["certification_country"] = self.config.region
            params["certification.lte"] = "PG"
        return params

    def discover(self, *, query: str = "", as_of: str | None = None, mode: str = "") -> ProviderBatch:
        checked_at = as_of or datetime.now(timezone.utc).isoformat()
        movies: list[MovieCandidate] = []
        try:
            if query.strip():
                payload = self._get("/search/movie", {
                    "query": query.strip(),
                    "include_adult": "false",
                    "language": self.config.language,
                    "region": self.config.region,
                    "page": 1,
                })
            else:
                payload = self._get("/discover/movie", self._discover_params(mode=mode))

            for item in payload.get("results", []):
                candidate = self._normalize(item, checked_at)
                if candidate is not None:
                    movies.append(candidate)

            return ProviderBatch(
                provider=self.provider,
                movies=tuple(movies),
                status="OK",
                checked_at=checked_at,
                source="TMDB watch providers powered by JustWatch",
            )
        except Exception as exc:
            return ProviderBatch(
                provider=self.provider,
                status="UNAVAILABLE",
                reason=f"{exc.__class__.__name__}: {exc}",
                checked_at=checked_at,
                source="TMDB watch providers powered by JustWatch",
            )

    async def _normalize_async(self, item: dict, checked_at: str) -> MovieCandidate | None:
        movie_id = item.get("id")
        title = (item.get("title") or item.get("original_title") or "").strip()
        if not movie_id or not title:
            return None
        try:
            details = await self._get_async(
                f"/movie/{int(movie_id)}",
                {"language": self.config.language, "append_to_response": "watch/providers,release_dates"},
            )
        except Exception:
            return None
        provider_payload = details.get("watch/providers", {})
        region = provider_payload.get("results", {}).get(self.config.region, {})
        offers: list[FreeOffer] = []
        seen: set[str] = set()
        for access, key in (("free_ads", "ads"), ("free", "free"), ("subscription", "flatrate")):
            for entry in region.get(key, []) or []:
                name = (entry.get("provider_name") or "").strip()
                if not name or name.casefold() in seen:
                    continue
                seen.add(name.casefold())
                offers.append(FreeOffer(provider=name, watch_url=region.get("link") or "https://www.themoviedb.org/", access=access, checked_at=checked_at, source="TMDB/JustWatch", verified=True, availability_confidence="direct"))
        if not offers:
            return None
        release_date = (item.get("release_date") or "").strip() or None
        year = int(release_date[:4]) if release_date and release_date[:4].isdigit() else None
        genres = tuple(GENRE_NAMES[g] for g in item.get("genre_ids", []) if g in GENRE_NAMES)
        runtime = details.get("runtime")
        runtime_minutes = int(runtime) if isinstance(runtime, (int, float)) and runtime > 0 else None
        age_rating = self._us_certification(details.get("release_dates", {}))
        # Kids mode requires an explicit safety classification. TMDB supplies the
        # US certification, so do not leave this as None and accidentally make
        # every title fail the kids gate. Keep PG-13 conservative until a title
        # has independent kid-friendly evidence.
        kids_eligible = age_rating in {"G", "PG", "TV-G", "TV-PG"}
        pg13_kid_friendly = False if age_rating == "PG-13" else None
        pg13_reason = "PG-13 requires independent kid-friendly evidence" if age_rating == "PG-13" else None
        if not genres:
            genres = tuple(g.get("name", "").strip() for g in details.get("genres", []) if g.get("name"))
        return MovieCandidate(title=title, year=year, ratings=RatingEvidence(tmdb=item.get("vote_average"), tmdb_votes=item.get("vote_count")), offers=tuple(offers), available_from=None, genres=genres, runtime_minutes=runtime_minutes, age_rating=age_rating, kids_eligible=kids_eligible, pg13_kid_friendly=pg13_kid_friendly, pg13_reason=pg13_reason)

    async def discover_async(self, *, query: str = "", as_of: str | None = None, mode: str = "") -> ProviderBatch:
        checked_at = as_of or datetime.now(timezone.utc).isoformat()
        try:
            if query.strip():
                payload = await self._get_async("/search/movie", {"query": query.strip(), "include_adult": "false", "language": self.config.language, "region": self.config.region, "page": 1})
            else:
                payload = await self._get_async("/discover/movie", self._discover_params(mode=mode))
            movies = []
            for item in payload.get("results", []):
                candidate = await self._normalize_async(item, checked_at)
                if candidate is not None:
                    movies.append(candidate)
            return ProviderBatch(provider=self.provider, movies=tuple(movies), status="OK", checked_at=checked_at, source="TMDB watch providers powered by JustWatch")
        except Exception as exc:
            return ProviderBatch(provider=self.provider, status="UNAVAILABLE", reason=f"{exc.__class__.__name__}: {exc}", checked_at=checked_at, source="TMDB watch providers powered by JustWatch")

    @staticmethod
    def _us_certification(release_dates: dict) -> str | None:
        results = release_dates.get("results", []) if isinstance(release_dates, dict) else []
        us = next((entry for entry in results if entry.get("iso_3166_1") == "US"), None)
        if not us:
            return None
        certifications = [
            (entry.get("certification") or "").strip().upper()
            for entry in (us.get("release_dates", []) or [])
            if (entry.get("certification") or "").strip()
        ]
        return certifications[0] if certifications else None

    def _normalize(self, item: dict, checked_at: str) -> MovieCandidate | None:
        movie_id = item.get("id")
        title = (item.get("title") or item.get("original_title") or "").strip()
        if not movie_id or not title:
            return None

        # One detail request carries both watch-provider and release-date data.
        # This keeps the complete request well below Cloudflare Free's
        # external-subrequest limit while retaining runtime and rating data.
        try:
            details = self._get(
                f"/movie/{int(movie_id)}",
                {
                    "language": self.config.language,
                    "append_to_response": "watch/providers,release_dates",
                },
            )
        except Exception:
            return None

        provider_payload = details.get("watch/providers", {})
        region = provider_payload.get("results", {}).get(self.config.region, {})
        offers: list[FreeOffer] = []
        seen: set[str] = set()

        for access, key in (
            ("free_ads", "ads"),
            ("free", "free"),
            ("subscription", "flatrate"),
        ):
            for entry in region.get(key, []) or []:
                name = (entry.get("provider_name") or "").strip()
                if not name or name.casefold() in seen:
                    continue
                seen.add(name.casefold())
                offers.append(FreeOffer(
                    provider=name,
                    watch_url=region.get("link") or "https://www.themoviedb.org/",
                    access=access,
                    checked_at=checked_at,
                    source="TMDB/JustWatch",
                    verified=True,
                    availability_confidence="direct",
                ))

        if not offers:
            return None

        release_date = (item.get("release_date") or "").strip() or None
        year = int(release_date[:4]) if release_date and release_date[:4].isdigit() else None
        genres = tuple(GENRE_NAMES[g] for g in item.get("genre_ids", []) if g in GENRE_NAMES)
        runtime = details.get("runtime")
        runtime_minutes = int(runtime) if isinstance(runtime, (int, float)) and runtime > 0 else None
        age_rating = self._us_certification(details.get("release_dates", {}))
        kids_eligible = age_rating in {"G", "PG", "TV-G", "TV-PG"}
        pg13_kid_friendly = False if age_rating == "PG-13" else None
        pg13_reason = "PG-13 requires independent kid-friendly evidence" if age_rating == "PG-13" else None
        if not genres:
            genres = tuple(
                g.get("name", "").strip()
                for g in details.get("genres", [])
                if g.get("name")
            )

        return MovieCandidate(
            title=title,
            year=year,
            ratings=RatingEvidence(
                imdb=None,
                imdb_votes=None,
                rotten_tomatoes_critics=None,
                rotten_tomatoes_audience=None,
                metacritic=None,
                tmdb=item.get("vote_average"),
                tmdb_votes=item.get("vote_count"),
            ),
            offers=tuple(offers),
            available_from=None,
            genres=genres,
            runtime_minutes=runtime_minutes,
            age_rating=age_rating,
            kids_eligible=kids_eligible,
            pg13_kid_friendly=pg13_kid_friendly,
            pg13_reason=pg13_reason,
        )