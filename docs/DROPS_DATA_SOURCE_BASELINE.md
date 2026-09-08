# Drops Data Source Baseline

Status: Approved architecture direction
Date: September 8, 2026

## Core strategy

Drops should not depend on scraping every retailer or on obtaining approval from every retailer before the module can work.

V1 should use a layered source strategy:

1. **Broad shopping discovery source** to locate the exact product across multiple sellers.
2. **Direct retailer integrations** where legitimate, stable access exists and provides stronger verification.
3. **Future approved sources** added incrementally without changing the core Drops model.

The module must remain useful even if an individual retailer never grants API access.

## Initial V1 source plan

### Broad discovery

Use a commercial shopping-data provider such as DataForSEO Merchant / Google Shopping data as the broad seller-discovery layer.

Its role is discovery and normalized offer collection across many sellers, including price and availability signals when supplied by the source.

### First direct retailer

Best Buy is the preferred first direct-retailer integration because its official developer APIs can provide product/catalog, pricing, availability, store, and local pickup/store information where supported.

### Future sources

Amazon Creators API and eBay Browse / Buy APIs are potential later integrations only after required access and production approval are actually obtained.

Do not make either Amazon or eBay a V1 dependency.

Walmart direct APIs are not a V1 dependency unless a suitable legitimate consumer-shopping access path becomes available.

## Source adapter architecture

Each provider should be isolated behind a source adapter rather than embedded throughout the Drops engine.

Suggested shape:

```text
drops/
    resolver.py
    normalizer.py
    verifier.py
    watcher.py

    sources/
        dataforseo.py
        bestbuy.py
        amazon.py       # later
        ebay.py         # later
        ...
```

Each source adapter translates provider-specific data into the same module-neutral Drops offer model.

## Normalized offer model

At minimum, normalized offers should be able to represent:

- canonical product identity
- retailer / seller
- source name
- product URL
- price
- currency
- stock state
- exact variant attributes when known
- shipping availability when known
- local pickup availability when known
- pickup/store location when known
- last verified timestamp
- evidence/source confidence

## Evidence rule

**Unknown is not the same as No.**

If a source explicitly verifies stock, price, variant, shipping, or pickup, Drops may display that state as verified.

If the source does not expose a field, the result must say that it is unknown / not verified rather than inferring a negative or positive answer.

Examples:

- `In stock: true` -> In Stock
- inventory field absent -> Stock Not Verified
- pickup field absent -> Pickup Not Verified

Do not convert missing evidence into a confident claim.

## Ranking and verification

The verifier should apply the user's exact criteria after normalization.

The ranker should prefer stronger verified evidence and better user matches rather than simply the cheapest raw listing.

Direct retailer evidence may outrank broad discovery evidence for the same retailer/product when it is newer or more authoritative.

## Policy / provider isolation

Provider-specific legal, attribution, caching, storage, display, and rate-limit requirements should live with or alongside each adapter.

The shared engine must not assume every source allows identical caching, storage, display, refresh cadence, or ranking behavior.

## V1 boundaries

- No automatic checkout or purchasing bots.
- No hostile anti-bot bypasses.
- No promise of every retailer on the internet.
- Do not depend on a single restricted provider for the module to function.
- Add sources only when access is legitimate and stable enough to support the product honestly.

## Shared Universal Watcher fit

Drops uses the common platform pattern:

Discover -> Normalize -> Filter -> Verify -> Rank -> Result -> optionally Watch

Broad discovery increases coverage; direct retailer adapters strengthen evidence over time without requiring a rewrite of the module.
