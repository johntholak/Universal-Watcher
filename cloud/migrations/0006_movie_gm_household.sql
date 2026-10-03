CREATE TABLE IF NOT EXISTS movie_viewers (
  viewer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  preferred_genres_json TEXT NOT NULL DEFAULT '[]',
  disliked_genres_json TEXT NOT NULL DEFAULT '[]',
  preferred_keywords_json TEXT NOT NULL DEFAULT '[]',
  disliked_keywords_json TEXT NOT NULL DEFAULT '[]',
  preferred_runtime_min INTEGER,
  preferred_runtime_max INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, viewer_id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_movie_viewers_user
  ON movie_viewers(user_id, created_at);