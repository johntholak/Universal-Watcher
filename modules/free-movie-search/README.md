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

Kids Mode is a hard suitability gate followed by age-specific ranking. The current family search uses ages 6 and 9.

- G/PG may pass with explicit eligibility evidence.
- PG-13 requires strong kid-friendly evidence plus an explicit rationale.
- R/NC-17 and adult-content evidence fail.
- Unknown or unsupported classifications fail closed.
- Each child gets an independent fit score and mixed-age mismatch is penalized.

## Next planned Movie GM layers

2.0B:
- persistent household preference storage
- watched/rejected suppression
- "why this movie?" UI breakdown
- Tonight mode
- hidden-gem discovery
- household disagreement scoring
- feedback loop that learns from watched/rated titles

The architecture intentionally keeps these as separate layers rather than one opaque mega-score.
