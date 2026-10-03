"""Tests for the Movie GM provider integration boundary."""
from __future__ import annotations

from modules.free_movie_search.free_movie_search import FreeOffer, MovieCandidate, RatingEvidence
from modules.free_movie_search.movie_gm_pipeline import ProviderBatch, run_movie_gm_pipeline
from modules.free_movie_search.movie_gm_profile import WatchRecord


def movie(title: str) -> MovieCandidate:
    return MovieCandidate(
        title=title,
        year=2026,
        ratings=RatingEvidence(imdb=7.5, imdb_votes=20000, rotten_tomatoes_critics=80),
        offers=(FreeOffer(provider="Peacock", watch_url="https://example.test",
                          verified=True, availability_confidence="direct"),),
        genres=("Adventure",),
        runtime_minutes=100,
    )


class GoodProvider:
    provider = "GoodProvider"

    def discover(self, *, query="", as_of=None):
        return ProviderBatch(provider=self.provider, movies=(movie("One"), movie("Two")))


class FailedProvider:
    provider = "BrokenProvider"

    def discover(self, *, query="", as_of=None):
        raise RuntimeError("provider unavailable")


class PartialProvider:
    provider = "PartialProvider"

    def discover(self, *, query="", as_of=None):
        return ProviderBatch(provider=self.provider, status="UNAVAILABLE", reason="source blocked")


def test_pipeline_combines_successful_sources():
    result = run_movie_gm_pipeline([GoodProvider()])
    assert result.providers_checked == ("GoodProvider",)
    assert result.total_candidates == 2
    assert len(result.recommendation.recommendations) == 2


def test_pipeline_preserves_provider_failure_as_unavailable():
    result = run_movie_gm_pipeline([GoodProvider(), FailedProvider(), PartialProvider()])
    assert result.providers_checked == ("GoodProvider", "PartialProvider")
    assert ("BrokenProvider", "UNAVAILABLE: RuntimeError") in result.providers_unavailable
    assert ("PartialProvider", "source blocked") in result.providers_unavailable
    assert result.total_candidates == 2


def test_pipeline_deduplicates_same_title_and_year():
    class DuplicateProvider:
        provider = "DuplicateProvider"

        def discover(self, *, query="", as_of=None):
            return ProviderBatch(provider=self.provider, movies=(movie("One"),))

    result = run_movie_gm_pipeline([GoodProvider(), DuplicateProvider()])
    assert result.total_candidates == 2


class RatingEnricher:
    provider = "OMDb"

    def __init__(self):
        self.calls = 0

    def enrich(self, candidate):
        self.calls += 1
        return MovieCandidate(
            title=candidate.title,
            year=candidate.year,
            ratings=RatingEvidence(
                imdb=8.2,
                imdb_votes=90000,
                rotten_tomatoes_critics=91,
                rotten_tomatoes_audience=88,
            ),
            offers=candidate.offers,
            genres=candidate.genres,
            runtime_minutes=candidate.runtime_minutes,
            age_rating=candidate.age_rating,
        )


def test_pipeline_enriches_selected_candidates_without_changing_availability():
    enricher = RatingEnricher()
    result = run_movie_gm_pipeline([GoodProvider()], rating_enrichers=[enricher], rating_enrichment_limit=1)
    assert enricher.calls == 1
    enriched = {item.ranked.movie.title: item.ranked.movie for item in result.recommendation.recommendations}
    assert enriched["One"].ratings.imdb == 8.2 or enriched["Two"].ratings.imdb == 8.2
    assert all(movie.offers[0].provider == "Peacock" for movie in enriched.values())


def test_pipeline_keeps_candidate_when_rating_enricher_fails():
    class BrokenEnricher:
        provider = "OMDb"

        def enrich(self, candidate):
            raise TimeoutError("rating source unavailable")

    result = run_movie_gm_pipeline([GoodProvider()], rating_enrichers=[BrokenEnricher()], rating_enrichment_limit=1)
    assert ("OMDb", "UNAVAILABLE: TimeoutError") in result.providers_unavailable
    assert result.total_candidates == 2
    assert len(result.recommendation.recommendations) == 2


def test_pipeline_reports_watched_suppression():
    result = run_movie_gm_pipeline([GoodProvider()], watch_history=[WatchRecord("One", rating="liked")])
    assert result.recommendation.suppressed_count == 1
    assert [item.ranked.movie.title for item in result.recommendation.recommendations] == ["Two"]
