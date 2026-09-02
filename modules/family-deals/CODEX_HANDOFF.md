# HUNT Family Deals — Current Codex Handoff

**Date:** September 1, 2026  
**Current baseline:** HUNT v5.0 Fast Filters + Semantic Verifier  
**Primary development machine:** macOS 26.6.2  

## Start here

This folder is the current source of truth for the HUNT Family Deals module. Read this file completely before changing code.

Then:

1. Read `README.txt`, `server.py`, `index.html`, and `tests/test_strict_parser.py`.
2. Inspect everything in `reference/`, especially the V3 false-positive screenshots and the three V4.1 live screenshots.
3. Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

4. Initialize Git if needed and create a clean baseline commit before substantive changes.
5. Do not redesign the UI from scratch. The current visual direction is approved enough to preserve while functionality is improved.

## How to run on the user's Mac

Preferred:

```bash
python3 server.py
```

Or double-click `start_hunt.command`.

The first time macOS sees the `.command` file, Gatekeeper may block it because it is unsigned. The user successfully resolved this with **System Settings → Privacy & Security → Open Anyway**. Do not treat that warning as an application crash.

HUNT starts on `127.0.0.1:8765` and tries ports 8766–8774 if necessary.

The implementation currently uses Python standard-library components, plus browser-side JavaScript in `index.html`.

---

# 1. Product goal

HUNT is intended to become a personal internet agent. The current Family Deals module should answer a constrained request such as:

> Find family dinner deals within 7 miles of West Hills, under $50, for 4 people, open tonight, optionally limited by restaurant type and cuisine.

The system should behave like an agent that does the scavenger hunt for the user, not like a normal keyword search.

It must:

1. Discover the restaurant universe in the selected radius.
2. Apply user filters.
3. Resolve reliable restaurant sources.
4. Find actual meal/package offers.
5. Bind each price to the correct offer.
6. Prove serving capacity.
7. Respect budget and hours requirements.
8. Return only defensible results.
9. Show coverage numbers so the user can see what was actually searched.

Correctness is more important than returning many results.

---

# 2. Full-radius discovery is a hard requirement

There must be **NO arbitrary top-N restaurant cap**.

The user's live West Hills, CA / 7-mile run produced:

- **697 restaurants discovered**

This successfully proved that the old 10-restaurant limitation is gone.

Preserve full-radius discovery even while optimizing speed. Never solve performance by silently checking only the first 10, 20, 50, etc.

Important nuance: the current discovery source is OpenStreetMap/Overpass. A source-complete OSM scan is not proof that every restaurant in the real world is represented. Longer-term HUNT should combine additional discovery sources and deduplicate them. Do not overclaim completeness.

See `reference/full-radius-result-*.png`.

---

# 3. V3 live verifier and the false-positive failure

A V3 live run produced approximately:

- 697 restaurants discovered
- 325 official sources resolved
- 301 unique official web sources checked
- 29 sources blocked/unreadable
- 372 restaurants without a resolvable official source
- 9 supposed verified matches

Those 9 were not trustworthy. The user noticed that the verifier was binding unrelated dollar amounts to nearby family-related language.

Examples from `reference/v3-false-positive-*.png`:

- **Michael's Pizza:** `$4.00` was a delivery charge. The 6-foot sub itself was `$99.99`.
- **Big Z Pizza Family Restaurant:** a discounted item price was treated as a family-dinner total.
- **California Chicken Cafe:** `$25` broccoli pasta salad feeding 10–12 was a side/tray, not a complete dinner.
- **Pizza Hut:** `$7` value-menu language appeared near family-meal FAQ copy but was not the family-meal price.
- **Einstein Bros.:** `$2` came from unrelated pricing language.
- **Munch Box:** `$5` came from coupon/review-like text.
- **Dave & Buster's:** `$5 Bites` promotional language was treated as a family-meal price even though the page itself listed excluded locations.
- **Olive Garden:** a per-person/starting catering price was surfaced as though it were a package total.

This was a core correctness failure, not a display issue.

---

# 4. Strict price-to-meal binding rule

V4/V4.1 introduced a much stricter verifier.

A price cannot qualify merely because it appears near words such as `family`, `meal`, or `package`.

HUNT should reject or downgrade:

- delivery/service/convenience fees
- coupons and discounts
- savings/rewards language
- approximate / “starting at” / “as low as” prices when no exact total is proven
- unavailable or location-excluded promotions
- reviews/testimonials
- unrelated FAQ prices
- side dishes or trays that are not a complete meal
- per-person prices incorrectly treated as package totals
- incidental item prices adjacent to family-related text

A result should be called fully verified only when the evidence proves that the displayed total belongs to the actual meal/package being recommended.

---

# 5. Family-size rule is locked

The user clarified this explicitly and likes this definition:

**Family-size means serves 4 through 10.**

The selected number of people is the minimum capacity the meal must cover, not an exact-match requirement.

For a party of 4:

- serves 4 → qualifies if all other rules pass
- serves 5 → qualifies
- serves 6 → qualifies
- serves 8 → qualifies
- serves 10 → qualifies
- serves 4–6 → qualifies
- serves 2–3 → does not qualify
- serves 12 → currently treat as catering/large-group rather than a normal family-size package

Do not regress this to exact `serves 4` matching.

---

# 6. V4.1 LIVE RESULT — important current evidence

The user **did live-test V4.1 on the Mac**. Older handoffs saying it was untested are obsolete.

Acceptance settings:

- Near: West Hills, CA
- Radius: 7 miles
- Maximum total: $50
- People: 4
- Open tonight only: ON

V4.1 reported:

- **697 restaurants discovered**
- **325 official sources resolved**
- **301 unique official web sources checked**
- **30 sources blocked/unreadable**
- **372 restaurants still lacking a resolvable official source**
- **74 misleading/irrelevant price candidates rejected by the strict parser**
- **0 fully verified matches**

See:

- `reference/v4.1-live-top.png`
- `reference/v4.1-live-middle.png`
- `reference/v4.1-live-bottom.png`

This run proved that the strict parser did a much better job rejecting the original V3 price mistakes.

However, it exposed the next semantic problem.

---

# 7. Chuck E. Cheese semantic false positive

V4.1 showed two Chuck E. Cheese entries under:

> MEAL + PARTY SIZE VERIFIED · HOURS STILL NEED CONFIRMATION

The parser saw language roughly like:

- birthday / kid's birthday
- `$99.99 for 6 Kids`
- `$49.99 Ultimate summer family deal`

and concluded that `$49` / serves 6 was a family meal.

That is semantically wrong for the user's intent. A birthday/arcade/event package is **not a family dinner deal**, even if the words `family`, `package`, a price, and a headcount all occur together.

V5.0 therefore adds event/entertainment rejection for contexts such as:

- birthday party
- party room
- party host
- reserved table
- arcade/games/play points
- birthday child / party guests
- entertainment/event-space language

A genuine **food-oriented take-home party pack** may still qualify. Do not globally ban the words `party` or `party pack`; distinguish food packages from entertainment/event packages.

Two new regression tests cover this distinction.

---

# 8. Hours/open-tonight remains a separate unresolved problem

The V4.1 run had **0 fully verified results** partly because `Open tonight only` was ON and many candidates had:

> Hours need confirmation

Do not weaken the deal verifier just to increase match count.

Instead, treat hours as its own evidence layer.

The desired outcome is:

- meal/package proven
- correct total proven
- serving capacity proven
- restaurant/location identity proven
- dinner/open-tonight status proven

If the first three are proven but hours are not, it can be shown as an explicitly unverified-hours candidate, but it must not be called a fully verified match when `Open tonight only` is enabled.

Potential future work:

- use structured `opening_hours` data when available
- official location-page hours
- chain location finder data
- distinguish corporate-site hours from the specific local location
- avoid guessing from generic Google-like snippets or stale data unless an evidence tier is clearly labeled

---

# 9. Restaurant type filters approved by the user

The user explicitly approved these categories:

- **Any**
- **Independent + local**
- **Independent only**
- **Chains only**

There should also be an internal **Unknown** classification rather than guessing.

Desired product semantics:

### Independent
Generally one location.

### Local group
Roughly 2–5 locations, primarily in the same local area.

### Chain
Generally 6+ locations, multi-market/state presence, or clear official evidence of a franchise/location network.

### Unknown
Evidence is insufficient to classify confidently.

`Independent + local` should keep Unknown restaurants included rather than silently hiding them because classification evidence is incomplete.

The current V5 browser-side classifier uses conservative heuristics including known chains, structured brand data, and repeated same-name listings in the radius. Treat this as a useful first pass, **not the final authority**.

Longer-term classification should prefer stronger evidence such as official location counts/network evidence before labeling an ambiguous restaurant a chain.

---

# 10. Cuisine filters approved by the user

Cuisine should be a **multi-select**, not a single-choice filter.

Current V5 groups:

- Pizza / Italian
- Mexican / Latin
- Asian
- American
- BBQ
- Mediterranean
- Indian
- Seafood
- Other / unknown
- Any cuisine

The user likes the idea of being able to combine cuisines, e.g. Italian + Mexican + BBQ.

Cuisine filtering should happen before expensive website crawling, but after the full-radius discovery count is established.

---

# 11. Performance is now a major product requirement

The user described V4.1 as:

> “very very very slow”

The radius discovery itself is not the main bottleneck. The expensive part is resolving and crawling hundreds of official websites and potentially several pages per site.

The user accepts that a broad search has work to do, but the product needs to feel materially faster.

**Do not improve speed by reducing geographic coverage or reintroducing a top-N cap.**

Speed should come from architecture:

- pre-crawl filtering
- concurrency
- caching
- source/domain deduplication
- adaptive early stopping
- avoiding repeated page loads
- avoiding serial source resolution
- reusing evidence between nearby searches

---

# 12. V5.0 performance changes already implemented

The current baseline implements these speed changes:

1. **Full radius is still discovered first.**
2. Restaurant type and cuisine filters are applied **before website verification**.
3. Structured/Wikidata source resolution runs concurrently.
4. Official websites are checked with up to **24 workers** instead of 12.
5. Maximum crawl depth is **3 relevant pages per source** instead of 4.
6. Adaptive early stop once sufficient verified meal evidence is found.
7. Official-source evidence cache under `~/.hunt_cache` for approximately **6 hours**.
8. Wikidata homepage/source resolution cache for approximately **7 days**.
9. Browser-side restaurant-radius discovery cache for approximately **30 minutes**.
10. Source evidence can be reused across budget changes for the same party size.
11. UI now reports cached source count and elapsed verification time.

The intent is that the first broad search may still take time, while repeat searches and filtered searches become much faster.

**Important: these V5 speed changes have NOT yet been live-benchmarked by the user.** The user decided to move back to Codex immediately after V5 was packaged.

Therefore, Codex's first task should be to measure the actual V5 run rather than assume the optimizations worked.

---

# 13. Current automated test status

As packaged for this handoff:

```text
13 tests run
13 passing
```

Run with:

```bash
python3 -m unittest discover -s tests -v
```

The suite includes regression coverage for:

- delivery fee != meal price
- family restaurant name does not make a discount a family deal
- unrelated FAQ price rejection
- per-person price conversion logic
- real family meal for 4
- side-dish rejection
- starting-price rejection
- serves 6 accepted for family of 4
- serves 10 accepted for family of 4
- serving range covering party
- package entirely above family range rejected
- birthday/event package rejected
- take-home food party pack can still qualify

Tests are necessary but not sufficient. Every meaningful parser failure found in live evidence should get its own regression test before fixing the parser.

---

# 14. Immediate Codex priorities, in order

## Priority 1 — Baseline and benchmark V5 on Mac

Run:

- West Hills, CA
- 7 miles
- $50 maximum
- 4 people
- Open tonight only ON

Test at least:

1. `Any` restaurant type + `Any cuisine`
2. `Independent + local` + `Any cuisine`
3. Repeat one identical search to measure cache benefit

Capture:

- total restaurants discovered
- restaurants surviving filters
- official sources resolved
- unique sources checked
- cached sources reused
- blocked/unreadable
- unresolved sources
- rejected misleading candidates
- fully verified matches
- elapsed seconds

Do not make further speed changes until the bottleneck is measured.

## Priority 2 — Validate semantic correctness

Inspect every result that V5 calls fully verified or meal+party-size verified.

Specifically confirm that Chuck E. Cheese birthday/event packages are gone.

For every false positive:

1. save the exact source/evidence text
2. write a regression test
3. diagnose why it passed
4. make the smallest safe logic change
5. rerun the entire suite

## Priority 3 — Improve hours verification

Once meal semantics are trustworthy, improve open-tonight confirmation as a separate layer. Do not conflate missing hours with meal invalidity.

## Priority 4 — Improve official-source coverage

The prior broad run left about **372 of 697** restaurants without a resolvable official source. This is likely the next large coverage bottleneck.

Explore higher-quality source resolution without weakening evidence standards.

Potential areas:

- better extraction of website fields from OSM/structured records
- restaurant name + city/location resolution
- official location finders
- chain location pages instead of generic corporate roots
- structured search/provider integration where permitted
- JavaScript menu/order systems
- PDF/image menus when reliable binding is possible
- respectful blocked-site fallbacks, not anti-bot bypasses

If third-party prices are ever used, they must be a separately labeled evidence tier. Do not present third-party data as official-source verification.

---

# 15. Suggested architecture as the project grows

Keep these concerns separable and testable:

1. restaurant discovery
2. distance/radius filter
3. restaurant deduplication
4. restaurant-type classification
5. cuisine classification
6. official-source resolution
7. page retrieval/caching
8. candidate meal extraction
9. semantic meal-vs-event classification
10. price-to-item binding
11. serving-capacity parsing
12. hours/open-tonight verification
13. evidence/confidence tiering
14. ranking
15. UI presentation

`server.py` is still manageable, but splitting it is acceptable if done carefully with tests and a recovery commit. Avoid a rewrite merely for cleanliness.

---

# 16. UI direction

Preserve the existing HUNT look and layout. The user did not ask for a redesign during this phase.

The UI should make coverage transparent rather than acting like a black box.

Useful visible metrics include:

- restaurants discovered
- restaurants surviving filters
- sources resolved
- sources checked
- cached sources reused
- blocked/unreadable sources
- unresolved official sources
- misleading candidates rejected
- fully verified matches
- elapsed verification time

Do not fill the page with technical clutter, but retain enough proof that the user can see HUNT searched broadly.

---

# 17. Working style expected by the user

- Make changes directly. Do not ask the user to manually patch code.
- Preserve working behavior and make recovery points before risky changes.
- Diagnose real observed failures before rewriting logic.
- Explain technical findings in plain English.
- Favor defensible results over inflated match counts.
- Do not claim source completeness that HUNT cannot prove.
- Do not casually change the current UI direction.
- Do not reintroduce arbitrary result caps as a performance shortcut.

---

# 18. Acceptance standard for a “verified” result

A skeptical reviewer should be able to open the evidence source and answer YES to all relevant questions:

1. Is this an actual food meal/package rather than a fee, coupon, side item, birthday package, arcade package, or unrelated promotion?
2. Does the displayed price belong to that exact meal/package?
3. Can the package feed at least the user's requested party size?
4. Is the serving capacity within the current family-size 4–10 definition?
5. Is the effective total within the user's budget?
6. Is the offer applicable to the relevant restaurant/location rather than excluded or generic to another market?
7. If `Open tonight only` is ON, is dinner availability/open status supported by evidence rather than guessed?

If HUNT cannot prove one of these, it should downgrade or exclude the result rather than call it fully verified.

---

# 19. Current project files

Key files:

- `server.py` — discovery support, official-source resolution, crawling, caching, strict verifier, jobs/API
- `index.html` — current UI, full-radius discovery, restaurant/cuisine filters, client-side discovery cache, progress/result rendering
- `tests/test_strict_parser.py` — strict verifier regression suite
- `start_hunt.command` — Mac launcher
- `start_hunt.bat` — Windows launcher
- `README.txt` — run instructions and V5 summary
- `reference/` — visual evidence from prior live tests

---

# 20. First message to act on

After reading this handoff, the recommended Codex action is:

> Inspect the current V5 source and reference screenshots, run all tests, create a Git baseline/recovery commit if needed, then benchmark the real West Hills 7-mile / $50 / 4-person search on macOS. Do not redesign the UI and do not weaken verification. Measure the discovery/filter/source/cache/elapsed numbers first. Then inspect every claimed match against its source, add regression tests for any false positive, and only afterward optimize the measured bottleneck or improve hours/source coverage.
