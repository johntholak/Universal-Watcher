from modules.free_movie_search.free_movie_search import (
    FreeOffer, MovieCandidate, RatingEvidence, rank_movies, split_current_and_upcoming
)
from modules.free_movie_search.movie_gm_profile import (
    TasteProfile, WatchRecord, feedback_signal, is_watched, normalize_title, score_taste
)


def movie(title="Test", score=8.0, votes=100000, availability="direct"):
    return MovieCandidate(
        title=title,
        year=2026,
        ratings=RatingEvidence(imdb=score, imdb_votes=votes),
        offers=(FreeOffer(
            provider="Peacock",
            watch_url="https://example.com",
            access="subscription",
            verified=True,
            availability_confidence=availability,
        ),),
    )


def test_included_subscription_is_accessible():
    results = rank_movies([movie()])
    assert len(results) == 1


def test_unverified_offer_is_not_accessible():
    m = movie()
    m = MovieCandidate(m.title, m.year, m.ratings, (
        FreeOffer("Peacock", "https://example.com", access="subscription", verified=False),
    ))
    assert rank_movies([m]) == []


def test_availability_confidence_is_exposed():
    result = rank_movies([movie()])[0]
    assert result.availability_confidence == 100.0
    assert any("Availability confidence" in reason for reason in result.reasons)


def test_upcoming_is_separate():
    m = MovieCandidate(
        title="Coming Soon", year=2026,
        ratings=RatingEvidence(imdb=7.0, imdb_votes=10000),
        offers=(FreeOffer("Peacock", "https://example.com", access="subscription", verified=True),),
        available_from="2026-10-10",
    )
    ranked = rank_movies([m])
    current, upcoming = split_current_and_upcoming(ranked, as_of="2026-10-03", days=30)
    assert current == []
    assert len(upcoming) == 1


def test_kids_mode_fails_closed_without_eligibility():
    m = movie()
    assert rank_movies([m], kids_mode=True, child_ages=(6, 9)) == []


def test_watch_history_normalizes_titles():
    history = (WatchRecord("the goonies", rating="loved"),)
    assert normalize_title("  The   Goonies ") == "the goonies"
    assert is_watched("The Goonies", history)
    assert feedback_signal("THE GOONIES", history) == 100.0


def test_taste_profile_explains_match():
    score, reasons = score_taste(
        genres=("Adventure", "Comedy"),
        title="Example",
        profile=TasteProfile(preferred_genres=("Adventure",)),
    )
    assert score > 50
    assert any("Preferred genre" in reason for reason in reasons)
