# Free Movie Search V1

This module extends Universal Watcher with a free-streaming movie discovery engine.

Goal: discover movies legally available at no subscription cost in the U.S., verify the free offer and provider, normalize ratings and content evidence, and rank the full qualifying set by objective movie quality plus configurable personal-fit signals.

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

## Kids Movie Mode

Kids mode is a hard suitability gate followed by age-specific ranking.

- Default target ages are supplied by the caller. The current family search uses ages 6 and 9.
- Each child gets an independent age-fit score.
- Mixed-age fit is calculated from the child scores and includes a mismatch penalty, so a movie that works for only one child does not look artificially strong.
- G and PG can pass when explicit kids-eligibility evidence is present.
- PG-13 can pass only when strong family/kid-friendly evidence and an explicit PG-13 rationale are present.
- R and NC-17 always fail.
- Adult-content evidence always fails.
- Scary, violence, and language evidence can reduce the age-specific score, with stronger penalties for the younger child.
- Unknown or unsupported classifications fail closed.
- The content-review layer must populate kids_eligible, pg13_kid_friendly, pg13_reason, and age_fit_by_age; the ranking layer does not invent missing suitability evidence.

kids_movie_rules.py contains the deterministic content-evidence-to-age-fit rules. It is intentionally conservative and provider-agnostic.

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
- kids mode
- child ages

## Planned output

Each result exposes title/year/runtime, free provider(s), direct watch destination when available, IMDb / Rotten Tomatoes / Metacritic evidence, vote/review volume, objective quality score, personal-fit score, combined recommendation score, confidence, evidence timestamps, age-specific fit, and an explanation of major ranking factors.

## Provider strategy

Use legal, public/authorized sources first. JustWatch is the initial discovery source because its U.S. catalog explicitly supports a Free filter and reports free offers. Provider confirmation remains a separate verification step.

Do not bypass anti-bot controls. Do not make the engine dependent on scraping a blocked provider.

V1 starts with the deterministic normalization/filter/ranking core and offline fixtures. Live provider adapters are added only after the scoring contract is stable and testable.
