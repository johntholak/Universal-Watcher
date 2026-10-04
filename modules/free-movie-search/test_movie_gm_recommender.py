"""Tests for Movie GM recommendation orchestration."""
from __future__ import annotations

from modules.free_movie_search.free_movie_search import FreeOffer, MovieCandidate, RatingEvidence
from modules.free_movie_search.movie_gm_profile import TasteProfile, WatchRecord
from modules.free_movie_search.movie_gm_decision import ViewerProfile
from modules.free_movie_search.movie_gm_recommender import recommend_movies


def candidate(title: str, genres=("Adventure",), votes=100000, runtime=100, rating=7.5,
              available_from=None, age_rating="PG"):
    return MovieCandidate(
        title=title,
        year=2026,
        ratings=RatingEvidence(imdb=rating, imdb_votes=votes, rotten_tomatoes_critics=80,
                               rotten_tomatoes_audience=85, metacritic=72),
        offers=(FreeOffer(provider="Peacock", watch_url="https://example.test", verified=True,
                          availability_confidence="direct"),),
        available_from=available_from,
        genres=tuple(genres),
        runtime_minutes=runtime,
        age_rating=age_rating,
        kids_eligible=age_rating in {"G", "PG"},
        age_fit_by_age=((6, 90.0), (9, 92.0)),
    )


def test_recommendation_builds_structured_breakdown():
    result = recommend_movies([candidate("Space Adventure")])
    assert len(result.recommendations) == 1
    rec = result.recommendations[0]
    assert 0 <= rec.score.final <= 100
    assert rec.score.quality == rec.ranked.quality_score
    assert rec.why


def test_watched_movies_are_suppressed():
    history = (WatchRecord(title_key="space adventure", rating="fine"),)
    result = recommend_movies([candidate("Space Adventure"), candidate("New Movie")],
                              watch_history=history)
    assert [r.ranked.movie.title for r in result.recommendations] == ["New Movie"]


def test_kids_mode_keeps_strict_gate():
    adult = candidate("Adult Movie", age_rating="R")
    adult = MovieCandidate(**{**adult.__dict__, "kids_eligible": False})
    kids = candidate("Kids Movie")
    kids = MovieCandidate(**{**kids.__dict__, "genres": ("Family",), "age_rating": "PG", "kids_eligible": True})
    result = recommend_movies([adult, kids], mode="kids", child_ages=(6, 9))
    assert [r.ranked.movie.title for r in result.recommendations] == ["Kids Movie"]


def test_tonight_excludes_upcoming_and_runtime_over_limit():
    result = recommend_movies(
        [candidate("Short Now", runtime=95),
         candidate("Long Now", runtime=140),
         candidate("Tomorrow", available_from="2026-10-04", runtime=90)],
        mode="tonight",
        as_of="2026-10-03",
        runtime_max=120,
    )
    assert [r.ranked.movie.title for r in result.recommendations] == ["Short Now"]
    assert [r.movie.title for r in result.upcoming] == ["Tomorrow"]


def test_household_disagreement_is_explained():
    viewers = (
        ViewerProfile("viewer-a", TasteProfile(preferred_genres=("Adventure",))),
        ViewerProfile("viewer-b", TasteProfile(disliked_genres=("Adventure",))),
    )
    result = recommend_movies([candidate("Split Decision")], viewers=viewers)
    rec = result.recommendations[0]
    assert rec.household.disagreement > 0
    assert any("disagreement" in reason.casefold() for reason in rec.why)


def test_hidden_gem_requires_quality_and_low_vote_volume():
    result = recommend_movies(
        [candidate("Hidden Gem", votes=12000), candidate("Popular", votes=200000)],
        mode="hidden_gems",
        hidden_gem_max_votes=50000,
    )
    assert [r.ranked.movie.title for r in result.recommendations] == ["Hidden Gem"]
    assert result.recommendations[0].hidden_gem is True


def test_hidden_gem_does_not_treat_missing_votes_as_evidence():
    no_votes = candidate("Unknown Reach", votes=0)
    result = recommend_movies([no_votes], mode="hidden_gems")
    assert result.recommendations == ()
