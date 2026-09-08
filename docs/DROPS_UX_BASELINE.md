# Drops UX Baseline

Status: Approved product direction
Date: September 8, 2026

## Purpose

Drops is an exact-product finder and watcher. The user already knows what product they want; Universal Watcher searches supported sources for an offer that meets the user's availability, price, variant, and fulfillment criteria, then optionally keeps watching the exact same search.

## V1 search flow

### 1. What do you want?

Accept one of:

- product name
- model number
- UPC / SKU / other reliable identifier
- product URL

The system should resolve the input to a specific product and show the matched product before the user proceeds when there is ambiguity.

Primary actions:

- This is it
- Not the right product

### 2. What counts as a match?

Supported criteria should include:

- in stock
- optional maximum price
- exact variant attributes when exposed by the source, such as color, size, model, capacity, or edition
- shipping eligibility
- local pickup eligibility
- pickup location / ZIP / city / current location when local pickup is requested

### 3. Where should we look?

The user can choose:

- any supported retailer
- selected supported retailers

Do not imply universal retailer coverage. Only supported legitimate data sources should be included.

Primary search action: Find It

## Results baseline

Results should be offer-first, not retailer-first.

Each result should prioritize:

- retailer / seller
- verified current price
- stock state
- exact-product / variant match state
- shipping availability
- pickup availability and distance when known
- last verified time
- direct View Product action

Clearly show why an offer qualifies or fails the user's criteria.

A preferred / best qualifying result may be highlighted when ranking evidence is strong.

## No-match behavior

When nothing qualifies, state that directly and summarize useful coverage, for example:

- number of supported sources checked
- number that had the product
- number that met all conditions

Primary continuation action: Keep Watching

## Watch behavior

Keep Watching saves the exact current Drops search and criteria. The user should not have to re-enter the product or filters.

Potential watch triggers include:

- product comes back in stock
- price drops to or below the target
- requested size/color/model/variant becomes available
- local pickup becomes available
- a new supported source offers a qualifying match

## Product rules

- Do not turn Drops V1 into a generic product recommendation engine.
- Do not promise every retailer.
- Do not build automatic checkout or purchasing bots.
- Use supported, legitimate, stable data sources only.
- Preserve the shared Universal Watcher pattern: Discover -> Normalize -> Filter -> Verify -> Rank -> Result -> optionally Watch.
