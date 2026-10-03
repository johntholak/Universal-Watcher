"""Persistent household viewer profiles for Movie GM.

The decision engine stays provider-neutral. This module owns serialization and
normalization of viewer preferences so the same model can be stored in D1 or
SQLite by the application layer.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from modules.free_movie_search.movie_gm_decision import ViewerProfile
from modules.free_movie_search.movie_gm_profile import TasteProfile


class HouseholdProfileStore:
    def __init__(self, path: str | Path = "data/movie_gm.sqlite3") -> None:
        path = Path(path)
        if str(path) != ":memory:": path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS movie_viewers (
              viewer_id TEXT PRIMARY KEY,
              display_name TEXT NOT NULL,
              weight REAL NOT NULL DEFAULT 1.0,
              preferred_genres_json TEXT NOT NULL DEFAULT '[]',
              disliked_genres_json TEXT NOT NULL DEFAULT '[]',
              preferred_keywords_json TEXT NOT NULL DEFAULT '[]',
              disliked_keywords_json TEXT NOT NULL DEFAULT '[]',
              preferred_runtime_min INTEGER,
              preferred_runtime_max INTEGER,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
        """)
        self._db.commit()

    def upsert(self, viewer_id: str, display_name: str, profile: TasteProfile, weight: float = 1.0) -> None:
        from datetime import datetime, timezone
        stamp = datetime.now(timezone.utc).isoformat()
        values = (
            viewer_id.strip(), display_name.strip() or viewer_id.strip(), max(0.0, float(weight)),
            json.dumps(profile.preferred_genres), json.dumps(profile.disliked_genres),
            json.dumps(profile.preferred_keywords), json.dumps(profile.disliked_keywords),
            profile.preferred_runtime_min, profile.preferred_runtime_max, stamp, stamp,
        )
        with self._lock:
            self._db.execute("""INSERT INTO movie_viewers
              (viewer_id,display_name,weight,preferred_genres_json,disliked_genres_json,
               preferred_keywords_json,disliked_keywords_json,preferred_runtime_min,
               preferred_runtime_max,created_at,updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?)
              ON CONFLICT(viewer_id) DO UPDATE SET display_name=excluded.display_name,
              weight=excluded.weight,preferred_genres_json=excluded.preferred_genres_json,
              disliked_genres_json=excluded.disliked_genres_json,
              preferred_keywords_json=excluded.preferred_keywords_json,
              disliked_keywords_json=excluded.disliked_keywords_json,
              preferred_runtime_min=excluded.preferred_runtime_min,
              preferred_runtime_max=excluded.preferred_runtime_max,updated_at=excluded.updated_at""", values)
            self._db.commit()

    def viewers(self) -> tuple[ViewerProfile, ...]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM movie_viewers ORDER BY created_at,viewer_id").fetchall()
        return tuple(ViewerProfile(
            viewer_id=row["viewer_id"],
            weight=float(row["weight"]),
            taste=TasteProfile(
                preferred_genres=tuple(json.loads(row["preferred_genres_json"])),
                disliked_genres=tuple(json.loads(row["disliked_genres_json"])),
                preferred_keywords=tuple(json.loads(row["preferred_keywords_json"])),
                disliked_keywords=tuple(json.loads(row["disliked_keywords_json"])),
                preferred_runtime_min=row["preferred_runtime_min"],
                preferred_runtime_max=row["preferred_runtime_max"],
            ),
        ) for row in rows)

    def close(self) -> None:
        with self._lock:
            self._db.close()
