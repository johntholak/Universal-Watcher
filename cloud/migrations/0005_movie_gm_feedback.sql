-- Persist Movie GM feedback. Raw feedback is the source of truth; learned taste is derived.
CREATE TABLE movie_feedback (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  title_key TEXT NOT NULL,
  title TEXT NOT NULL,
  rating TEXT NOT NULL CHECK (rating IN ('loved','liked','fine','disliked')),
  watched INTEGER NOT NULL DEFAULT 1 CHECK (watched IN (0,1)),
  genres_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(genres_json)),
  created_at TEXT NOT NULL
);
CREATE INDEX movie_feedback_user_created ON movie_feedback(user_id, created_at DESC);
CREATE INDEX movie_feedback_user_title ON movie_feedback(user_id, title_key, created_at DESC);
