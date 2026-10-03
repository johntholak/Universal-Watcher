# Free Movie Search / Movie GM

Universal Watcher's movie engine is evolving from a free-streaming finder into a household movie decision engine.

## Stable commands

- **Run Everyone Mode**: full household movie search without the Kids Mode suitability gate.
- **Run Kids Mode**: full movie search with the conservative kids gate and age-specific fit.
- **Run the movie search**: defaults to Everyone Mode.
- Natural-language modifiers such as "for tonight", "under 2 hours", "funny", or "include Netflix" become temporary constraints.

## Movie GM 2.0A

The 2.0A foundation keeps the existing Discover -> Normalize -> Filter -> Verify -> Rank -> Act architecture and adds four durable concepts:

1. **Taste profile**: explicit preferred/disliked genres, themes, and runtime preferences.
2. **Watch history**: watched titles and household feedback can be stored without coupling the ranking core to a provider.
3. **Explainability**: every ranked result carries quality, personal-fit, combined score, confidence, availability confidence, and human-readable reasons.
4. **Availability confidence**: verified offers can distinguish direct, recent, multi-source, indirect, stale, and unknown evidence. Unverified offers are never treated as accessible.

The ranking layer remains deterministic and provider-agnostic. It does not fetch the web itself.

## Movie GM 2.0B foundation

The 2.0B foundation now includes the first explicit household decision layer:

- A TasteProfile can directly influence personal fit using genres, title themes, and runtime.
- WatchRecord history can suppress movies already watched.
- Title matching is normalized so capitalization and repeated whitespace do not create duplicate history entries.
- Watched suppression can be explicitly disabled for rewatch searches.
- Personal fit defaults to a neutral 50/100 when no explicit preference has been supplied.
- household_fit scores individual viewers, calculates weighted household fit, and exposes disagreement rather than hiding it.
- breakdown returns separate quality, taste, household, and availability components plus a final decision score.
- learn_taste_from_history learns only from explicit loved/liked/disliked feedback.
- All of these remain provider-neutral and deterministic.

## Movie GM recommendation orchestration

movie_gm_recommender.py now provides the explicit decision pipeline after normalized provider evidence exists:

**Discover -> Verify -> Content/Kids Gate -> Quality -> Taste -> Household Fit -> Availability -> Decision**

Supported modes:

- **Everyone**: current accessible household catalog.
- **Kids**: strict kids suitability gate followed by age-aware household ranking.
- **Tonight**: current titles only, with an optional runtime ceiling. Upcoming titles remain separate.
- **Hidden Gems**: requires a strong quality/confidence signal while favoring titles with a smaller IMDb vote footprint. Missing vote volume is never treated as a hidden-gem signal.

Each recommendation carries a structured ScoreBreakdown, HouseholdFit, and human-readable why reasons. The orchestration layer does not perform network calls or persistence.

## Access profile

The default household profile treats Prime Video, Max, Apple TV+, Hulu, Peacock, and YouTube TV as accessible because the household already pays for them. Netflix is surfaced as an optional service but is not accessible by default. This is configurable.

## Free and availability semantics

- Ad-supported free offers qualify.
- Included household subscriptions count as zero additional payment.
- Rental/purchase-only offers do not qualify as accessible.
- Provider failures are UNAVAILABLE, never NO_MATCH.
- Missing evidence remains unknown.
- Upcoming titles are separate from Available Now and are never treated as watchable today.
- No arbitrary top-N discovery cap.

## Kids Mode

Kids Mode is a hard suitability gate followed by age-specific ranking.

- G/PG may pass with explicit eligibility evidence.
- PG-13 requires strong kid-friendly evidence plus an explicit rationale.
- R/NC-17 and adult-content evidence fail.
- Unknown or unsupported classifications fail closed.
- Each child gets an independent fit score and mixed-age mismatch is penalized.

## Stable implementation rule

Provider adapters discover and normalize evidence. Movie GM decides using that normalized evidence. The ranking core must not make network calls, guess missing data, or turn an unverified offer into a confirmed result.


## Live availability source adapter

`tmdb_movie_adapter.py` implements the first real external source adapter.

- Uses the official TMDB API with `TMDB_READ_ACCESS_TOKEN`.
- Uses the US watch-provider data returned by TMDB, which is powered by JustWatch.
- Traverses the complete result pagination returned by TMDB rather than applying an arbitrary top-N catalog cap.
- Converts ad-supported/free offers and subscription offers into normalized `FreeOffer` records.
- Rental and purchase-only offers are deliberately excluded from accessible offers.
- Records provider name, source, checked timestamp, verification state, and availability confidence.
- Maps TMDB vote average/count into separate TMDB quality evidence. It does not pretend TMDB scores are IMDb scores.
- Missing credentials fail closed.
- Provider/API failures remain `UNAVAILABLE`.

TMDB requires an API credential. The repository must never contain the token. TMDB's developer documentation states that the API is free for non-commercial use subject to its terms and attribution requirements; the watch-provider endpoint is powered by JustWatch and requires JustWatch attribution. The product must therefore retain the required attribution in its eventual UI/About surface.
