"""Independent OMDb rating enrichment for Movie GM.

OMDb is used only as rating/content evidence. It does not determine streaming
availability. Its free key tier is quota-limited, so the caller controls how
many candidates are enriched.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from workers import fetch
except ImportError:  # Local test environment
    fetch = None

from .free_movie_search import MovieCandidate, RatingEvidence


@dataclass(frozen=True)
class OMDbConfig:
    api_key: str
    timeout_seconds: int = 15


class OMDbRatingAdapter:
    provider = "OMDb"

    def __init__(self, config: OMDbConfig | None = None):
        key = (config.api_key if config else os.getenv("OMDB_API_KEY", "")).strip()
        if not key:
            raise ValueError("OMDB_API_KEY is required")
        self.config = config or OMDbConfig(api_key=key)

    def _get(self, params: dict[str, str | int]) -> dict:
        query = urlencode({"apikey": self.config.api_key, "r": "json", **params})
        request = Request(
            f"https://www.omdbapi.com/?{query}",
            headers={"accept": "application/json"},
        )
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _number(value: object) -> float | None:
        try:
            if value in (None, "", "N/A"):
                return None
            return float(str(value).replace("%", "").replace("/100", "").strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _votes(value: object) -> int | None:
        try:
            if value in (None, "", "N/A"):
                return None
            return int(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return None

    async def _get_async(self, params: dict[str, str | int]) -> dict:
        query = urlencode({"apikey": self.config.api_key, "r": "json", **params})
        response = await fetch(
            f"https://www.omdbapi.com/?{query}",
            headers={"accept": "application/json"},
        )
        if not response.ok:
            raise RuntimeError(f"OMDb HTTP {response.status}")
        return await response.json()

    async def enrich_async(self, movie: MovieCandidate) -> MovieCandidate:
        params: dict[str, str | int] = {"t": movie.title, "type": "movie"}
        if movie.year is not None:
            params["y"] = movie.year
        payload = await self._get_async(params)
        if str(payload.get("Response", "")).casefold() != "true":
            return movie

        ratings = RatingEvidence(
            imdb=self._number(payload.get("imdbRating")),
            imdb_votes=self._votes(payload.get("imdbVotes")),
            rotten_tomatoes_critics=self._number(payload.get("tomatoMeter")),
            rotten_tomatoes_audience=self._number(payload.get("tomatoUserMeter")),
            metacritic=self._number(payload.get("Metascore")),
            tmdb=movie.ratings.tmdb,
            tmdb_votes=movie.ratings.tmdb_votes,
        )
        runtime = movie.runtime_minutes
        raw_runtime = str(payload.get("Runtime", ""))
        if runtime is None and raw_runtime.endswith(" min"):
            try:
                runtime = int(raw_runtime.split()[0])
            except ValueError:
                pass

        return MovieCandidate(
            title=movie.title,
            year=movie.year,
            ratings=ratings,
            offers=movie.offers,
            available_from=movie.available_from,
            genres=movie.genres,
            runtime_minutes=runtime,
            age_rating=movie.age_rating or (str(payload.get("Rated", "")).strip() or None),
            personal_fit=movie.personal_fit,
            taste_reasons=movie.taste_reasons,
            age_fit_by_age=movie.age_fit_by_age,
            kids_eligible=movie.kids_eligible,
            pg13_kid_friendly=movie.pg13_kid_friendly,
            pg13_reason=movie.pg13_reason,
        )

    def enrich(self, movie: MovieCandidate) -> MovieCandidate:
        params: dict[str, str | int] = {"t": movie.title, "type": "movie", "tomatoes": "true"}
        if movie.year is not None:
            params["y"] = movie.year
        payload = self._get(params)
        if str(payload.get("Response", "")).casefold() != "true":
            return movie

        ratings = RatingEvidence(
            imdb=self._number(payload.get("imdbRating")),
            imdb_votes=self._votes(payload.get("imdbVotes")),
            rotten_tomatoes_critics=self._number(payload.get("tomatoMeter")),
            rotten_tomatoes_audience=self._number(payload.get("tomatoUserMeter")),
            metacritic=self._number(payload.get("Metascore")),
            tmdb=movie.ratings.tmdb,
            tmdb_votes=movie.ratings.tmdb_votes,
        )
        runtime = movie.runtime_minutes
        raw_runtime = str(payload.get("Runtime", ""))
        if runtime is None and raw_runtime.endswith(" min"):
            try:
                runtime = int(raw_runtime.split()[0])
            except ValueError:
                pass

        return MovieCandidate(
            title=movie.title,
            year=movie.year,
            ratings=ratings,
            offers=movie.offers,
            available_from=movie.available_from,
            genres=movie.genres,
            runtime_minutes=runtime,
            age_rating=movie.age_rating or (str(payload.get("Rated", "")).strip() or None),
            personal_fit=movie.personal_fit,
            taste_reasons=movie.taste_reasons,
            age_fit_by_age=movie.age_fit_by_age,
            kids_eligible=movie.kids_eligible,
            pg13_kid_friendly=movie.pg13_kid_friendly,
            pg13_reason=movie.pg13_reason,
        )
