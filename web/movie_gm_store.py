"""Small SQLite persistence layer for Movie GM feedback.

The local preview uses SQLite so feedback survives server restarts. Production
will use the matching D1 schema in cloud/migrations/0005_movie_gm_feedback.sql.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from modules.free_movie_search.movie_gm_profile import WatchRecord, normalize_title


class MovieGMStore:
    def __init__(self, path: str | Path = "data/movie_gm.sqlite3") -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS movie_feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title_key TEXT NOT NULL,
              title TEXT NOT NULL,
              rating TEXT NOT NULL CHECK (rating IN ('loved','liked','fine','disliked')),
              watched INTEGER NOT NULL DEFAULT 1 CHECK (watched IN (0,1)),
              genres_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS movie_feedback_title ON movie_feedback(title_key)")
        self._db.commit()

    def add_feedback(self, *, title: str, rating: str, genres: Iterable[str]) -> None:
        watched = 0 if rating == "disliked" else 1
        stamp = datetime.now(timezone.utc).isoformat()
        import json
        clean_genres = tuple(dict.fromkeys(g.strip() for g in genres if g.strip()))
        with self._lock:
            self._db.execute(
                "INSERT INTO movie_feedback(title_key,title,rating,watched,genres_json,created_at) VALUES (?,?,?,?,?,?)",
                (normalize_title(title), title.strip(), rating, watched, json.dumps(clean_genres), stamp),
            )
            self._db.commit()

    def history(self) -> tuple[WatchRecord, ...]:
        with self._lock:
            rows = self._db.execute(
                "SELECT title_key,rating FROM movie_feedback WHERE watched=1 ORDER BY created_at,id"
            ).fetchall()
        return tuple(WatchRecord(title_key=row["title_key"], rating=row["rating"]) for row in rows)

    def learning_rows(self) -> tuple[tuple[WatchRecord, tuple[str, ...], str], ...]:
        import json
        with self._lock:
            rows = self._db.execute(
                "SELECT title_key,rating,genres_json,title FROM movie_feedback ORDER BY created_at,id"
            ).fetchall()
        return tuple(
            (WatchRecord(title_key=row["title_key"], rating=row["rating"]),
             tuple(json.loads(row["genres_json"])), row["title"])
            for row in rows
        )

    def close(self) -> None:
        with self._lock:
            self._db.close()
