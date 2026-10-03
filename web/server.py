"""Dependency-free local preview server for the Universal Watcher shell.

This server is intentionally in-memory and preview-only. It demonstrates the
web-to-core contract boundary without starting any live watcher or persisting
account data.
"""

from __future__ import annotations

import json
import mimetypes
import sys
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.contracts import Evidence, WatchDefinition, WatchResult
from modules.free_movie_search.movie_gm_runtime import run_live_movie_gm

SUPPORTED_MODULES = (
    {"id": "movies", "name": "Movies", "description": "Seat availability and showtimes"},
    {"id": "family-deals", "name": "Family Deals", "description": "Nearby offers that fit"},
)
SUPPORTED_MODULE_IDS = {module["id"] for module in SUPPORTED_MODULES}


class DraftWatchStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._watches: list[WatchDefinition] = []
        self._results: list[WatchResult] = []

    def add(self, watch: WatchDefinition) -> WatchDefinition:
        with self._lock:
            self._watches.insert(0, watch)
        return watch

    def all(self) -> list[WatchDefinition]:
        with self._lock:
            return list(self._watches)

    def transition(self, watch_id: str, status: str) -> WatchDefinition | None:
        with self._lock:
            for index, watch in enumerate(self._watches):
                if watch.watch_id != watch_id:
                    continue
                updated = watch.transition_to(status)
                self._watches[index] = updated
                return updated
        return None

    def add_result(self, result: WatchResult) -> WatchResult:
        with self._lock:
            self._results.insert(0, result)
        return result

    def results(self) -> list[WatchResult]:
        with self._lock:
            return list(self._results)


def serialize_watch(watch: WatchDefinition) -> dict[str, Any]:
    return {
        "watch_id": watch.watch_id,
        "module": watch.module,
        "query": watch.query,
        "criteria": dict(watch.criteria),
        "status": watch.status,
        "created_at": watch.created_at.isoformat(),
    }


def serialize_evidence(evidence: Evidence) -> dict[str, Any]:
    return {
        "source": evidence.source,
        "kind": evidence.kind,
        "summary": evidence.summary,
        "url": evidence.url,
        "captured_at": evidence.captured_at.isoformat(),
    }


def serialize_result(result: WatchResult) -> dict[str, Any]:
    return {
        "result_id": result.result_id,
        "watch_id": result.watch_id,
        "module": result.module,
        "title": result.title,
        "outcome": result.outcome,
        "verification": result.verification,
        "coverage": result.coverage,
        "evidence": [serialize_evidence(item) for item in result.evidence],
        "destination_url": result.destination_url,
        "reason": result.reason,
        "observed_at": result.observed_at.isoformat(),
    }


def serialize_movie_search(result) -> dict[str, Any]:
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
                {"provider": offer.provider, "access": offer.access,
                 "watch_url": offer.watch_url,
                 "availability_confidence": offer.availability_confidence,
                 "checked_at": offer.checked_at, "source": offer.source}
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


def make_handler(store: DraftWatchStore):
    class PreviewHandler(BaseHTTPRequestHandler):
        server_version = "UniversalWatcherPreview/1.0"

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_error_json(self, message: str, status: HTTPStatus) -> None:
            self._send_json({"error": message}, status)

        def _read_json(self) -> dict[str, Any] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            if length <= 0 or length > 16_384:
                return None
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None

        def _serve_static(self, request_path: str) -> None:
            relative = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
            candidate = (WEB_ROOT / relative).resolve()
            try:
                candidate.relative_to(WEB_ROOT)
            except ValueError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = candidate.read_bytes()
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/modules":
                self._send_json(list(SUPPORTED_MODULES))
            elif path == "/api/movies/search":
                params = parse_qs(urlparse(self.path).query)
                requested_mode = params.get("mode", ["everyone"])[-1].casefold()
                query = params.get("query", [""])[-1].strip()
                if requested_mode not in {"everyone", "kids", "tonight", "hidden_gems"}:
                    self._send_error_json("Unsupported Movie GM mode", HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = run_live_movie_gm(
                        query=query,
                        mode=requested_mode,
                        child_ages=(6, 9) if requested_mode == "kids" else (),
                    )
                    self._send_json(serialize_movie_search(result))
                except Exception as exc:
                    self._send_error_json(f"Movie search failed: {exc.__class__.__name__}", HTTPStatus.INTERNAL_SERVER_ERROR)
            elif path == "/api/watches":
                self._send_json([serialize_watch(watch) for watch in store.all()])
            elif path == "/api/results":
                self._send_json([serialize_result(result) for result in store.results()])
            else:
                self._serve_static(path)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/watches":
                self._send_error_json("Not found", HTTPStatus.NOT_FOUND)
                return
            payload = self._read_json()
            if payload is None:
                self._send_error_json("Request body must be a JSON object under 16 KB", HTTPStatus.BAD_REQUEST)
                return
            module = payload.get("module")
            if module not in SUPPORTED_MODULE_IDS:
                self._send_error_json("Unsupported watch module", HTTPStatus.BAD_REQUEST)
                return
            try:
                watch = WatchDefinition(
                    watch_id=str(payload.get("watch_id") or f"draft-{uuid.uuid4().hex[:12]}"),
                    module=module,
                    query=payload.get("query", ""),
                    criteria=payload.get("criteria") or {},
                    status="draft",
                    created_at=datetime.now(timezone.utc),
                )
            except (TypeError, ValueError) as exc:
                self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                return
            store.add(watch)
            self._send_json(serialize_watch(watch), HTTPStatus.CREATED)

        def do_PATCH(self) -> None:
            path = urlparse(self.path).path
            prefix = "/api/watches/"
            if not path.startswith(prefix) or not path[len(prefix):]:
                self._send_error_json("Not found", HTTPStatus.NOT_FOUND)
                return
            payload = self._read_json()
            status = payload.get("status") if payload else None
            if status not in {"active", "paused", "completed", "error"}:
                self._send_error_json("Unsupported watch status", HTTPStatus.BAD_REQUEST)
                return
            try:
                watch = store.transition(path[len(prefix):], status)
            except (TypeError, ValueError) as exc:
                self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
                return
            if watch is None:
                self._send_error_json("Watch not found", HTTPStatus.NOT_FOUND)
                return
            self._send_json(serialize_watch(watch))

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return PreviewHandler


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    store = DraftWatchStore()
    server = ThreadingHTTPServer((host, port), make_handler(store))
    print(f"Universal Watcher shell preview: http://{host}:{server.server_port}/")
    print("Drafts and preview results are held in memory only. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
