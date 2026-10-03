"""Tests for the Movie GM provider integration boundary."""
from __future__ import annotations

from modules.free_movie_search.free_movie_search import FreeOffer, MovieCandidate, RatingEvidence
from modules.free_movie_search.movie_gm_pipeline import ProviderBatch, run_movie_gm_pipeline


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
    assert result.providers_checked == ("GoodProvider",)
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
