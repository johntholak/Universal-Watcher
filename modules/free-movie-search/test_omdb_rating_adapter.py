import unittest

from modules.free_movie_search.free_movie_search import FreeOffer, MovieCandidate, RatingEvidence
from modules.free_movie_search.omdb_rating_adapter import OMDbConfig, OMDbRatingAdapter


class FakeOMDb(OMDbRatingAdapter):
    def __init__(self):
        super().__init__(OMDbConfig(api_key="test"))

    def _get(self, params):
        assert params["type"] == "movie"
        assert params["tomatoes"] == "true"
        return {
            "Response": "True",
            "imdbRating": "7.8",
            "imdbVotes": "123,456",
            "Metascore": "72",
            "tomatoMeter": "84",
            "tomatoUserMeter": "79",
            "Runtime": "104 min",
            "Rated": "PG",
        }


class OMDbRatingAdapterTests(unittest.TestCase):
    def test_enriches_independent_rating_evidence(self):
        movie = MovieCandidate(
            title="Example Movie",
            year=2020,
            ratings=RatingEvidence(tmdb=7.2, tmdb_votes=5000),
            offers=(FreeOffer("Tubi", "https://tubitv.com", verified=True),),
        )
        enriched = FakeOMDb().enrich(movie)
        self.assertEqual(enriched.ratings.imdb, 7.8)
        self.assertEqual(enriched.ratings.imdb_votes, 123456)
        self.assertEqual(enriched.ratings.rotten_tomatoes_critics, 84)
        self.assertEqual(enriched.ratings.rotten_tomatoes_audience, 79)
        self.assertEqual(enriched.ratings.metacritic, 72)
        self.assertEqual(enriched.runtime_minutes, 104)
        self.assertEqual(enriched.age_rating, "PG")
        self.assertEqual(enriched.ratings.tmdb, 7.2)

    def test_missing_rating_response_leaves_movie_unchanged(self):
        class Missing(FakeOMDb):
            def _get(self, params):
                return {"Response": "False", "Error": "Movie not found"}

        movie = MovieCandidate("Missing", 2020, RatingEvidence(), ())
        self.assertEqual(Missing().enrich(movie), movie)


if __name__ == "__main__":
    unittest.main()
