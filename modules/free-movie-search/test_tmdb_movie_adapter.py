"""Offline tests for the TMDB/JustWatch Movie GM adapter."""
from __future__ import annotations

from modules.free_movie_search.tmdb_movie_adapter import TMDBConfig, TMDBMovieAdapter


class FakeTMDB(TMDBMovieAdapter):
    def __init__(self):
        super().__init__(TMDBConfig(token="test-token"))
        self.calls = []

    def _get(self, path, params):
        self.calls.append((path, params))
        if path == "/discover/movie":
            return {
                "page": 1,
                "total_pages": 1,
                "results": [{
                    "id": 10,
                    "title": "Free Adventure",
                    "original_title": "Free Adventure",
                    "release_date": "2026-01-02",
                    "genre_ids": [12, 35],
                }],
            }
        if path == "/movie/10/watch/providers":
            return {
                "results": {
                    "US": {
                        "link": "https://www.themoviedb.org/movie/10",
                        "ads": [{"provider_name": "Tubi"}],
                        "flatrate": [{"provider_name": "Prime Video"}],
                        "rent": [{"provider_name": "Rental Store"}],
                    }
                }
            }
        raise AssertionError(path)


def test_adapter_normalizes_free_and_subscription_offers():
    result = FakeTMDB().discover(as_of="2026-10-03T00:00:00+00:00")
    assert result.status == "OK"
    assert len(result.movies) == 1
    movie = result.movies[0]
    assert movie.title == "Free Adventure"
    assert movie.genres == ("Adventure", "Comedy")
    assert {offer.provider for offer in movie.offers} == {"Tubi", "Prime Video"}
    assert {offer.access for offer in movie.offers} == {"free_ads", "subscription"}
    assert all(offer.verified for offer in movie.offers)
    assert all(offer.availability_confidence == "direct" for offer in movie.offers)


def test_adapter_does_not_turn_rental_only_into_accessible_offer():
    result = FakeTMDB().discover()
    assert all(offer.provider != "Rental Store" for movie in result.movies for offer in movie.offers)


def test_adapter_can_search_by_query():
    class SearchTMDB(FakeTMDB):
        def _get(self, path, params):
            if path == "/search/movie":
                assert params["query"] == "Tintin"
                return {"page": 1, "total_pages": 1, "results": [{
                    "id": 10, "title": "Tintin", "release_date": "2011-01-01", "genre_ids": [12]
                }]}
            return super()._get(path, params)

    result = SearchTMDB().discover(query="Tintin")
    assert [m.title for m in result.movies] == ["Tintin"]


def test_missing_token_fails_closed():
    try:
        TMDBMovieAdapter(TMDBConfig(token=""))
    except ValueError as exc:
        assert "TMDB_READ_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("missing token must fail closed")
