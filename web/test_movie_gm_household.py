from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from modules.free_movie_search.movie_gm_decision import ViewerProfile, household_fit, learn_taste_from_history
from modules.free_movie_search.movie_gm_profile import TasteProfile, WatchRecord
from web.movie_gm_household import HouseholdProfileStore


class MovieGMHouseholdTests(unittest.TestCase):
    def test_profiles_persist_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "movie.sqlite3"
            first = HouseholdProfileStore(path)
            first.upsert("kid", "Kid", TasteProfile(preferred_genres=("Animation",), disliked_genres=("Horror",)), 2)
            first.close()

            second = HouseholdProfileStore(path)
            rows = second.viewer_rows()
            viewers = second.viewers()
            second.close()

            self.assertEqual(rows[0]["display_name"], "Kid")
            self.assertEqual(rows[0]["preferred_genres"], ["Animation"])
            self.assertEqual(viewers[0].weight, 2)
            self.assertEqual(viewers[0].taste.disliked_genres, ("Horror",))

    def test_household_fit_weights_and_disagreement(self) -> None:
        viewers = (
            ViewerProfile("adult", TasteProfile(preferred_genres=("Comedy",)), 1),
            ViewerProfile("kid", TasteProfile(preferred_genres=("Animation",)), 3),
        )
        result = household_fit(title="Animated Comedy", genres=("Animation", "Comedy"), runtime_minutes=100, viewers=viewers)
        self.assertEqual(len(result.viewer_scores), 2)
        self.assertGreater(result.score, 50)

    def test_learning_uses_feedback_strength_and_ignores_neutral(self) -> None:
        history = (
            (WatchRecord("a", "liked"), ("Comedy",), "The Great Adventure"),
            (WatchRecord("b", "loved"), ("Comedy",), "The Great Adventure"),
            (WatchRecord("c", "disliked"), ("Horror",), "Scary Blood"),
            (WatchRecord("d", "fine"), ("Drama",), "Fine Drama"),
        )
        learned = learn_taste_from_history(history)
        self.assertEqual(learned.evidence_count, 3)
        self.assertEqual(learned.preferred_genres[0], "comedy")
        self.assertEqual(learned.disliked_genres[0], "horror")
        self.assertNotIn("drama", learned.preferred_genres)
        self.assertNotIn("great", learned.preferred_keywords)


if __name__ == "__main__":
    unittest.main()
