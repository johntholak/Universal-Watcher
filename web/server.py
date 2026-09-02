"""Dependency-free local preview server for the Universal Watcher shell.

This server is intentionally in-memory and draft-only. It demonstrates the
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
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.contracts import WatchDefinition


SUPPORTED_MODULES = (
    {"id": "movies", "name": "Movies", "description": "Seat availability and showtimes"},
    {"id": "tickets", "name": "Tickets", "description": "Events, prices, and inventory"},
    {"id": "family-deals", "name": "Family Deals", "description": "Nearby offers that fit"},
)
SUPPORTED_MODULE_IDS = {module["id"] for module in SUPPORTED_MODULES}


class DraftWatchStore:
    """Small thread-safe in-memory store used only by the local preview."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._watches: list[WatchDefinition] = []

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
                updated = watch.transition_to(status)  # type: ignore[arg-type]
                self._watches[index] = updated
                return updated
        return None


def serialize_watch(watch: WatchDefinition) -> dict[str, Any]:
    return {
        "watch_id": watch.watch_id,
        "module": watch.module,
        "query": watch.query,
        "criteria": dict(watch.criteria),
        "status": watch.status,
        "created_at": watch.created_at.isoformat(),
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

        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            path = urlparse(self.path).path
            if path == "/api/modules":
                self._send_json(list(SUPPORTED_MODULES))
            elif path == "/api/watches":
                self._send_json([serialize_watch(watch) for watch in store.all()])
            else:
                self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
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

        def do_PATCH(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
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
    print("Drafts are held in memory only. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
