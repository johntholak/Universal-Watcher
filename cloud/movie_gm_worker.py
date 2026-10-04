from __future__ import annotations

import json
from urllib.parse import urlparse, parse_qs

from workers import Response, WorkerEntrypoint

from free_movie_search.movie_gm_decision import ViewerProfile, learn_taste_from_history
from free_movie_search.movie_gm_profile import TasteProfile, WatchRecord
from free_movie_search.movie_gm_runtime import RuntimeConfig, run_live_movie_gm


MAX_BODY_BYTES = 16_384
ALLOWED_MODES = {"everyone", "kids", "tonight", "hidden_gems"}


def _json_list(value):
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _viewer(row) -> ViewerProfile:
    taste = TasteProfile(
        preferred_genres=_json_list(json.loads(row["preferred_genres_json"] or "[]")),
        disliked_genres=_json_list(json.loads(row["disliked_genres_json"] or "[]")),
        preferred_keywords=_json_list(json.loads(row["preferred_keywords_json"] or "[]")),
        disliked_keywords=_json_list(json.loads(row["disliked_keywords_json"] or "[]")),
        preferred_runtime_min=row["preferred_runtime_min"],
        preferred_runtime_max=row["preferred_runtime_max"],
    )
    return ViewerProfile(
        viewer_id=row["viewer_id"],
        taste=taste,
        weight=float(row["weight"]),
    )


def _serialize(result):
    recommendations = []
    for item in result.recommendation.recommendations:
        movie = item.ranked.movie
        recommendations.append({
            "title": movie.title,
            "year": movie.year,
            "runtime_minutes": movie.runtime_minutes,
            "age_rating": movie.age_rating,
            "genres": list(movie.genres),
            "ratings": {
                "imdb": movie.ratings.imdb,
                "imdb_votes": movie.ratings.imdb_votes,
                "rotten_tomatoes_critics": movie.ratings.rotten_tomatoes_critics,
                "rotten_tomatoes_audience": movie.ratings.rotten_tomatoes_audience,
                "metacritic": movie.ratings.metacritic,
                "tmdb": movie.ratings.tmdb,
                "tmdb_votes": movie.ratings.tmdb_votes,
            },
            "quality_score": round(item.ranked.quality_score, 1),
            "personal_fit_score": round(item.ranked.personal_fit_score, 1),
            "combined_score": round(item.ranked.combined_score, 1),
            "confidence": round(item.ranked.confidence, 1),
            "availability_confidence": item.ranked.availability_confidence,
            "household_score": round(item.household.score, 1),
            "why": list(item.why),
            "offers": [
                {
                    "provider": offer.provider,
                    "access": offer.access,
                    "watch_url": offer.watch_url,
                    "availability_confidence": offer.availability_confidence,
                    "checked_at": offer.checked_at,
                    "source": offer.source,
                }
                for offer in movie.offers
            ],
        })

    upcoming = []
    for item in result.recommendation.upcoming:
        movie = item.ranked.movie
        upcoming.append({
            "title": movie.title,
            "year": movie.year,
            "runtime_minutes": movie.runtime_minutes,
            "age_rating": movie.age_rating,
            "combined_score": round(item.ranked.combined_score, 1),
            "why": list(item.why),
        })

    return {
        "providers_checked": list(result.providers_checked),
        "providers_unavailable": [
            {"provider": provider, "reason": reason}
            for provider, reason in result.providers_unavailable
        ],
        "total_candidates": result.total_candidates,
        "suppressed_count": result.recommendation.suppressed_count,
        "recommendations": recommendations,
        "upcoming": upcoming,
    }


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        if url.path != "/internal/movie-gm/search" or request.method != "POST":
            return Response.json({"error": "Not found"}, status=404)

        try:
            body = await request.json()
            raw = json.dumps(body)
            if len(raw.encode("utf-8")) > MAX_BODY_BYTES or not isinstance(body, dict):
                return Response.json({"error": "Invalid request"}, status=400)

            user_id = str(body.get("user_id") or "").strip()
            if not user_id:
                return Response.json({"error": "User identity required"}, status=400)

            mode = str(body.get("mode") or "everyone").casefold().strip()
            if mode not in ALLOWED_MODES:
                return Response.json({"error": "Unsupported Movie GM mode"}, status=400)

            query = str(body.get("query") or "").strip()
            if len(query) > 200:
                return Response.json({"error": "Query is too long"}, status=400)

            feedback_result = await self.env.DB.prepare(
                """SELECT title_key,title,rating,watched,genres_json FROM movie_feedback
                   WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 200"""
            ).bind(user_id).run()
            feedback_rows = feedback_result.results or []

            history = []
            learning_rows = []
            for row in feedback_rows:
                genres = _json_list(json.loads(row["genres_json"] or "[]"))
                record = WatchRecord(title_key=row["title_key"], rating=row["rating"])
                learning_rows.append((record, genres, row["title"]))
                if row["watched"]:
                    history.append(record)

            learned = learn_taste_from_history(learning_rows)
            taste_profile = TasteProfile(
                preferred_genres=learned.preferred_genres,
                disliked_genres=learned.disliked_genres,
                preferred_keywords=learned.preferred_keywords,
                disliked_keywords=learned.disliked_keywords,
            ) if learned.evidence_count else None

            viewer_result = await self.env.DB.prepare(
                """SELECT viewer_id,display_name,weight,preferred_genres_json,disliked_genres_json,
                          preferred_keywords_json,disliked_keywords_json,preferred_runtime_min,preferred_runtime_max
                   FROM movie_viewers WHERE user_id=? ORDER BY created_at,viewer_id"""
            ).bind(user_id).run()
            viewers = tuple(_viewer(row) for row in (viewer_result.results or []))

            config = RuntimeConfig(
                tmdb_token=str(getattr(self.env, "TMDB_READ_ACCESS_TOKEN", "") or "").strip(),
                # Keep the live search on the stable TMDB/JustWatch path.
                # OMDb enrichment remains supported by the engine, but is
                # disabled at the Worker boundary until it can be isolated
                # from the production request path.
                include_omdb=False,
                omdb_api_key=str(getattr(self.env, "OMDB_API_KEY", "") or "").strip(),
            )
            result = await run_live_movie_gm(
                query=query,
                mode=mode,
                child_ages=(6, 9) if mode == "kids" else (),
                taste_profile=taste_profile,
                watch_history=tuple(history),
                viewers=viewers,
                config=config,
            )
            return Response.json(_serialize(result))
        except Exception as exc:
            return Response.json(
                {"error": "Movie GM execution failed", "type": exc.__class__.__name__},
                status=503,
            )
