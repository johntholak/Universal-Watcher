# PROJECT_STATUS.md — Universal Watcher

**Status date:** September 2, 2026  
**Overall stage:** Foundation / consolidation  
**Current milestone:** Universal Watcher Web Shell V1 + minimal shared contracts; Movies API/Mac acceptance remains pending

## Status legend

- 🟢 Working / proven core
- 🟡 Active development / usable but incomplete
- 🟠 Early / partial
- ⚪ Planned
- 🚫 Outside this project

## Master module table

| Module | Status | Current baseline | In this repo? | Immediate next step |
|---|---|---|---|---|
| Universal Watcher Core | 🟡 | Minimal watch/result contracts + Family Deals mapping | Yes | Keep live execution gated; add proven adapters after Movies acceptance |
| Universal Watcher Web App | 🟡 | V1 shell + in-memory lifecycle and results/evidence preview | Yes | Wire real adapters after Movies acceptance |
| Family Deals | 🟡 | V5.0 Fast Filters + Semantic Verifier; isolated result adapter mapping | Yes, intact import | Live benchmark V5, validate every claimed match, improve hours/source coverage |
| Seat Watcher | 🟡 reconstructed / live regression in progress | V44.6; AMC key issued and awaiting Thursday production deployment; browser seat capture proven; 23 offline tests | Yes | Retry API after Thursday deployment, then run Odyssey acceptance; Mac browser regression remains useful |
| Ticket Watcher | 🟡 | Bundle V1.11; Ticketmaster live watcher path V1.9 | Yes, intact import | Preserve Ticketmaster; decide approved marketplace expansion path |
| Theater Discovery | 🟠 | Separate-workstream decision made | Placeholder | Build non-AMC providers independently, then normalize into Seat Watcher |
| Drop Watch | ⚪ | Planned | Placeholder | Start only after Universal shell/integration foundation |
| Automated Job Hunter | ⚪ | Planned | Placeholder | After Drop Watch |
| Event Producer Copilot | ⚪ | Planned, deliberately last | Placeholder | Do not lose; build after prior modules |
| Car Search | ⚪ parking lot | Feasibility explored | Parking-lot note | Not active roadmap |
| Restaurant PDF Menu Builder | 🚫 | Separate project | No | Keep separate |

## Big-picture guardrail

Universal Watcher work is intentionally split into two connected lanes:

1. **Module verification:** Movies is the current live proof lane because its
   AMC date and inventory behavior is the highest-risk unfinished area.
2. **Platform foundation:** the shared contracts and web shell are being built
   for Movies, Tickets, Family Deals, and future modules together.

The platform work does not replace or narrow the module roadmap. Once Movies'
API/Mac acceptance gate is complete, proven Family Deals, Ticket Watcher, and
Seat Watcher engines will be connected through adapters, followed by theater
discovery expansion and the later planned modules.

While the Movies gate is waiting on AMC/API and Mac access, isolated adapter
mapping is allowed when it only translates an existing module job record and
does not start live monitoring or alter that module's engine. Family Deals is
the first such mapping; its live benchmark and web execution remain separate
acceptance steps.

---

# 1. Universal Watcher Core

## Current state

The conceptual common engine is:

**Discover → Normalize → Filter → Verify → Rank → Monitor → Alert → Act**

This has not yet been extracted into a shared production package. That is intentional. The real modules should inform the shared interface before a large refactor.

The first narrow contract preview now lives in `core/contracts.py`. It defines
module-neutral watch definitions, evidence, truthful result outcomes, and a
small `run_once` adapter protocol. No existing module is wired to it yet.

## Next

The initial extraction sequence is now:

1. [x] define a small module adapter contract
2. [x] define watch/result models
3. [ ] define job/worker execution model
4. [ ] define server-vs-local-helper boundary
5. [x] avoid premature rewrites

The first contract step is complete. The web shell now exercises the watch
definition boundary through a dependency-free in-memory preview API. A first
isolated Family Deals result adapter mapping is also present, while live
adapter execution remains gated on the Movies API deployment and Mac
acceptance regression.

The shell preview now exercises draft lifecycle transitions (`active`,
`paused`, and `completed`) through the same validation rules. It also exposes
an empty module-neutral results/evidence surface through `GET /api/results`.
These are local preview states only and do not start a watcher or invent a
match; an unavailable source remains distinct from `no_match` in the shared
result contract.

---

# 2. Family Deals

## Baseline

**V5.0 Fast Filters + Semantic Verifier**

The actual V5 source is present in `modules/family-deals/`.

The internal source still uses the legacy `HUNT` name. Preserve it until an intentional rename.

## Proven

- Full-radius restaurant discovery exists.
- The old 10-restaurant cap is gone.
- A West Hills 7-mile live run discovered 697 restaurants.
- Restaurant type filters exist.
- Cuisine multi-select exists.
- Official-source resolution exists.
- Strict price-to-offer binding exists.
- Party-size logic exists.
- Event/birthday-package rejection exists.
- Caching and concurrency optimizations exist.
- 13 automated strict-parser tests were passing at the V5 handoff.
- **Master Repo V1 verification:** all 13 Family Deals tests were rerun successfully after import.

## Major unresolved areas

- V5 speed changes have not yet been properly live-benchmarked by the user.
- Hours/open-tonight verification remains a separate evidence problem.
- Official-source resolution coverage is incomplete.
- A prior broad run left roughly 372 of 697 restaurants without a resolvable official source.
- Every live claimed match still needs skeptical evidence review.

## Hard rule

Never restore an arbitrary top-N restaurant limit to make broad searches feel faster.

---

# 3. Seat Watcher

## Authoritative known state

The post-Codex working state is documented as:

- branch: `main`
- latest known commit: `7a19015` — `Clean duplicate and incomplete theater results`
- baseline before Mac migration: `3a19039` — `Recovery point before macOS migration`

The exact post-Codex Git tree at `7a19015` was not recoverable. Master Repo V2 therefore contains a **reconstructed post-Codex V44 build** made from the user's uploaded Depth/Layering baseline plus the saved August 28 Codex handoff. It is not represented as a byte-for-byte recovery of that commit.

## Proven end-to-end

A live Mac run successfully handled:

- The Odyssey
- IMAX 70MM
- AMC Universal CityWalk
- four adjacent seats
- minimum row 5
- correct seat response parsing
- correct match
- correct AMC purchase/seat page opening

Also proven or covered:

- multiple AMC theaters
- location/radius filtering
- fuzzy movie matching
- future-date selection through AMC's real date control
- format separation including IMAX / IMAX 70MM / plain 70MM
- headless search
- adjacent-seat grouping
- ranking
- browser opens only on useful match
- Mac trackpad scrolling
- runtime theater cleanup
- CityWalk canonical route handling
- nine offline regression tests passing at the handoff

## Remaining

- V44.2 live testing on Sept. 1 proved current-day discovery/seat checking but exposed false-empty future-date discovery and an overly short stopping policy. V44.4 followed AMC's selectable calendar, but the Sept. 2 acceptance evidence still showed skipped real dates and failed inventory capture.
- V44.5 now requires the selected date's showtime results to reach a stable, meaningful state before extraction; waits for tracked seat-response parsing work; accepts AMC's documented `seatName` field without changing grouping logic; and distinguishes captured-no-match from inventory-unavailable throughout aggregation and final messaging.
- Sept. 2 Windows live diagnostic: CityWalk returned four Odyssey IMAX 70MM showtimes for Sept. 2, and all four seat pages produced captured inventory with valid no-group outcomes. Seat capture is restored in this environment.
- The same live diagnostic proved the remaining future-date cause: AMC returns HTTP 403 for its dated React results request (including in visible Chromium), leaving the current-day DOM unchanged. V44.5 now reports this as `SHOWTIME DISCOVERY UNAVAILABLE` and cannot convert it into a zero-showtime/no-seat conclusion.
- V44.5 passes 18 offline regression tests. Run it on the Mac to determine whether AMC permits that environment's dated request; pursue approved Showtime API access as the reliable provider path if it does not.
- V44.6 adds an optional approved AMC Showtime API discovery adapter. It resolves theatre IDs by slug, follows all result pages, applies the existing movie/format/time filters, and passes showtime IDs to the unchanged browser seat engine. It activates only when `AMC_VENDOR_KEY` is configured; otherwise the existing browser discovery path remains active.
- An AMC vendor key was issued and stored only in the ignored module-local `.env` file. AMC's success page says new keys are deployed to production once per week on Thursday; until that deployment, the API returns error 12005, `Unauthorized VendorKey`. V44.6 recognizes that state, reports it once, disables API retries for the remainder of the run, and uses the website fallback. Retry after Thursday's deployment.
- Verify theater cleanup visually.
- Run a controlled live Next Best exhaustion test.
- Stress Specific Date and Date Range after the date-control changes.
- Windows end-to-end regression.
- UI/UX is not considered finished.
- Eventually expose the engine through a module/API adapter instead of rebuilding it.

## Protected

Do not casually rewrite the AMC engine. See `AGENTS.md`.

---

# 4. Ticket Watcher

## Baseline

The actual latest saved bundle, **ticket-watcher-v1.11**, is present in `modules/ticket-watcher/`.

The working continuous Ticketmaster live-browser approach is described internally as Version 1.9. V1.10/V1.11 added StubHub diagnostic work around it.

## Working path

- Ticketmaster API locates the event.
- Fuzzy event matching works.
- Location/radius, date, quantity, and price criteria exist.
- The live watcher reads refreshed Ticketmaster four-ticket inventory through an offscreen browser.
- It can identify fee-inclusive qualifying offers in the tested flow.
- It continuously rechecks.
- It stops/alerts/opens Ticketmaster when a qualifying offer appears.
- **Master Repo V1 verification:** all 12 Ticket Watcher matcher/config tests were rerun successfully after import.

## Important limitation

Ticketmaster's Discovery API alone does not provide complete exact-seat/adjacency/checkout information. Browser inventory work exists specifically because the API is incomplete for that use case.

## StubHub

- Diagnostics were built.
- Listing-related data was captured.
- Automation/access defenses became the blocker.
- Do not turn this into an anti-bot bypass project.
- Prefer approved API access or another permitted integration path.

## Gametime

Discussed as a possible source; no completed connector is claimed.

---

# 5. Theater Discovery

Decision already made:

Build non-AMC theater-provider support independently before merging it into Seat Watcher.

Target direction:

- AMC
- Regal
- Cinemark
- additional providers where feasible

Normalize provider results so Seat Watcher can consume theaters/showtimes without making the core seat logic provider-specific.

No production-ready non-AMC implementation is claimed yet.

---

# 6. Roadmap

## Current sequence

### Milestone A — Source-control reliability
- [x] Master repo exists.
- [x] Configure private shared Git remote.
- [x] Import current Seat Watcher folder.
- [x] Establish baseline commits.
- [x] Confirm all run instructions.

### Milestone B — Universal Watcher Web Shell V1
One web application with initial module entry points and active-watch structure.

Initial integrations should prioritize already-developed modules rather than inventing new ones.

The first static shell foundation is now in `web/`. It is a dependency-free
preview with module entry points, active-watch/activity/results-and-evidence
surfaces, and a local draft flow. It does not start live watchers or alter the
protected Movies engine.

### Milestone C — Module integration
- Family Deals adapter (isolated result mapping started; live execution pending)
- Seat Watcher adapter/local-helper strategy
- Ticket Watcher adapter
- Theater discovery expansion

### Milestone D — Drop Watch
Build using the common platform.

### Milestone E — Automated Job Hunter
Build after Drop Watch.

### Milestone F — Event Producer Copilot
Build last after the watcher system is mature.

## Parking lot

Car Search Aggregator remains a strong possible Universal Watcher module but is not currently an active build commitment.

---

# 7. Repository health / unresolved consolidation items

- [x] Create Master Repo V1 structure
- [x] Import Family Deals V5 bundle
- [x] Import Ticket Watcher V1.11 bundle
- [x] Create authoritative product/status/run documents
- [x] Add reconstructed Seat Watcher post-Codex build (exact lost Git tree still unavailable)
- [x] Initialize local Git repository and stage the V44.6 baseline
- [x] Configure shared private Git remote
- [x] Create baseline commit after reconstructed Seat Watcher live regression
- [ ] Verify all modules run from repo paths
- [x] Begin Universal Watcher web shell


### Movies V44.4 Next Best behavior

- Removed the 14-day Next Best cutoff.
- Next Best learns the latest selectable AMC date from each selected theater's live date selector.
- Empty days inside the schedule do not end the search.
- Search stops after the last selectable AMC date across the selected theaters.
- A 35-day scan ceiling is retained only as a site-malfunction safety guard.
- User-facing module naming continues moving toward `Universal Watcher | Movies`; legacy technical filenames are preserved to avoid a risky rename-only refactor.

### Movies V44.5 live-regression fix

- Date selection is no longer considered complete on the first DOM fingerprint change. The requested option must remain selected while a meaningful result (showtime links or an explicit AMC empty state) stabilizes.
- Seat response handlers are tracked and allowed to finish, with a longer bounded capture window and useful candidate-response diagnostics.
- AMC's documented `seatName` field is accepted as an alias for the existing `name` field; the proven seat decoding, position extraction, filtering, grouping, ranking, and handoff logic remains intact.
- Inventory capture failure is reported as `Seat inventory unavailable` and cannot be summarized as a valid no-seat result.
- Exact next step: run the documented Odyssey / IMAX 70MM / CityWalk NEXT BEST acceptance case on the user's Mac and retain the Activity log. In parallel, request approved AMC Showtime API catalog access; do not attempt to bypass the observed HTTP 403.

### Movies V44.6 approved discovery path

- Added `amc_showtime_api.py`, an isolated catalog client using AMC's documented vendor-key authentication and theatre/date showtime endpoints.
- The adapter is optional and reads `AMC_VENDOR_KEY` from the environment or the ignored module-local `.env` file.
- API discovery reuses existing movie similarity, format classification, time filtering, showtime normalization, and browser seat capture.
- No AMC key is bundled, and the browser fallback remains intact.
- Local uncommitted user data: `modules/seat-watcher/.env` contains the issued key and is intentionally Git-ignored. Never commit or quote it.
