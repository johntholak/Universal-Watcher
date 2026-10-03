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

    def discover(self, *, query: str = "", as_of: str | None = None) -> ProviderBatch:
        checked_at = as_of or datetime.now(timezone.utc).isoformat()
        movies: list[MovieCandidate] = []
        try:
            page = 1
            total_pages = 1
            while page <= total_pages:
                if query.strip():
                    payload = self._get("/search/movie", {
                        "query": query.strip(),
                        "include_adult": "false",
                        "language": self.config.language,
                        "region": self.config.region,
                        "page": page,
                    })
                else:
                    payload = self._get("/discover/movie", {
                        "include_adult": "false",
                        "include_video": "false",
                        "language": self.config.language,
                        "region": self.config.region,
                        "watch_region": self.config.region,
                        "with_watch_monetization_types": "free,ads,flatrate",
                        "sort_by": "popularity.desc",
                        "page": page,
                    })

                results = payload.get("results", [])
                for item in results:
                    candidate = self._normalize(item, checked_at)
                    if candidate is not None:
                        movies.append(candidate)

                total_pages = int(payload.get("total_pages", page) or page)
                page += 1

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

    def _normalize(self, item: dict, checked_at: str) -> MovieCandidate | None:
        movie_id = item.get("id")
        title = (item.get("title") or item.get("original_title") or "").strip()
        if not movie_id or not title:
            return None

        provider_payload = self._get(f"/movie/{int(movie_id)}/watch/providers", {})
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
            runtime_minutes=None,
            age_rating=None,
        )
