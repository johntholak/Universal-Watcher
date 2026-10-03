# Free Movie Search V1

This module extends Universal Watcher with a free-streaming movie discovery engine.

Goal: discover movies legally available at no subscription cost in the U.S., verify the free offer and provider, normalize ratings, and rank the full qualifying set by objective movie quality plus configurable personal-fit signals.

The engine follows the Universal Watcher contract:

Discover -> Normalize -> Filter -> Verify -> Rank -> Act

## V1 rules

- Free means a current legal streaming offer with no rental, purchase, or subscription payment required.
- Ad-supported free offers qualify.
- Library-card services such as Kanopy/Hoopla may be represented as a separate access class and are not silently treated as universally free.
- A provider failure is UNAVAILABLE, never NO_MATCH.
- Missing rating evidence is labeled unknown rather than guessed.
- Rating volume matters. A high score from a tiny vote count does not outrank a well-supported score simply because the raw number is higher.
- Objective quality and personal fit remain separate fields so the UI can explain why a movie ranked where it did.
- Availability must include source/provenance and checked timestamp.
- No arbitrary top-N discovery cap. UI pagination may be separate from search coverage.

## Planned inputs

- free-only
- genres
- minimum IMDb rating
- minimum rating votes
- release-year range
- runtime range
- age rating / family suitability
- preferred providers
- excluded providers
- personal taste weights

## Planned output

Each result exposes title/year/runtime, free provider(s), direct watch destination when available, IMDb / Rotten Tomatoes / Metacritic evidence, vote/review volume, objective quality score, personal-fit score, combined recommendation score, confidence, evidence timestamps, and an explanation of major ranking factors.

## Provider strategy

Use legal, public/authorized sources first. JustWatch is the initial discovery source because its U.S. catalog explicitly supports a Free filter and reports free offers. Provider confirmation remains a separate verification step.

Do not bypass anti-bot controls. Do not make the engine dependent on scraping a blocked provider.

V1 starts with the deterministic normalization/filter/ranking core and offline fixtures. Live provider adapters are added only after the scoring contract is stable and testable.
