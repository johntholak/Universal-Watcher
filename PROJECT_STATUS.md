# PROJECT_STATUS.md — Universal Watcher

**Status date:** September 26, 2026
**Overall stage:** Foundation / consolidation  
**Current milestone:** Family Deals UI, offline Search/Watch API, guarded dispatch and GitHub batch runner are built; cloud execution is not deployed

## September 26 Watch criteria-version checkpoint

- Watch criteria can now be edited by completing a new Family Deals Search, then copying that Search's exact versioned payload. Edits are refused while the Watch has a pending/running job; previous criteria snapshots remain available, and meaningful run history records the version it checked.
- The fourth ordered D1 migration adds criteria versions and backfills existing Watches. Offline tests verify the edit boundary and that subsequent claims run the new criteria. No provider request or cloud deployment occurred.

**NEXT TASK:** Implement bounded worker-failure/retry handling and source-aware capacity safeguards, then run controlled V5 browser acceptance and verify actual account quotas before deployment.

## September 26 free-capacity state checkpoint

- When the configured daily GitHub run allowance is exhausted, due Family Deals jobs are marked `DELAYED` with `free_capacity`, and their Search/Watch state is visibly delayed. Cron requeues them at the next UTC-day reset; paused/stopped Watches are not resumed by this recovery.
- Temporary dispatch errors remain queued and retain a conservative run reservation because the remote outcome may be ambiguous. Offline tests cover Search and Watch delay/recovery, including expired-lease signals. This is a configured local bound, not visibility into the GitHub account's total free minutes across repositories.

## September 26 exact-criteria Watch checkpoint

- A Watch can be created from a completed Family Deals Search only. It copies the exact stored versioned criteria, schedules a conservative 24-hour next check, and exposes user-scoped list/detail/history and result reads.
- Cron queues at most ten due Watches per tick. Check Now is deduplicated per Watch; paused/stopped Watches cannot be claimed. Pause, resume, keep watching and soft-stop preserve the audit trail. Repeated identical outcomes do not spam history; outcome, candidate and coverage changes do. Dispatch now also wakes a runner for an expired lease, so crashed claims are not stranded.
- Watch job completion preserves uncertainty: partial V5 candidates do not set `FOUND`; only a defensible verified match can. A new ordered migration adds Watch coverage and the one-active-job index. Offline SQLite and API tests pass. No provider, GitHub Actions or Cloudflare resource was invoked.
- Criteria editing, notifications, a complete free-capacity delay/recovery state machine and live browser acceptance are still outstanding. The Watch cadence is currently fixed at 24 hours, not user-configurable.

## September 26 guarded dispatch checkpoint

- Added an opt-in GitHub workflow signal after queued Search creation and on a Cloudflare scheduled tick. A one-row D1 gate reserves a daily run before the network call, limits dispatch to one per 15 minutes, and keeps ambiguous failures charged against the configured allowance. The payload contains only the branch ref, never criteria.
- `DISPATCH_ENABLED` defaults off; an explicit daily run limit and a GitHub dispatch token are required. The optional Cron template has a D1 placeholder. This bound cannot account for Actions minutes consumed by other repositories, so free-account capacity and failure policy still need review before activation.
- Offline tests exercise the dispatch payload, cooldown, daily cap, disabled state, failure reservation and schema. No GitHub workflow was triggered or Cloudflare resource deployed.

## September 26 V5 batch runner checkpoint

- Added a manual-only GitHub Actions workflow and bounded Python runner. It claims only Family Deals jobs, one at a time (up to ten per invocation), maintains the lease, runs V5 in headless Chromium, sends five-result chunks, and finalizes each job. Workflow dispatch carries no criteria or credentials.
- The bridge invokes the preserved V5 page for geocoding, complete-radius Overpass discovery, deduplication, restaurant filters and official-source verification. It expands the old slider bounds to preserve exact radius and budget. The verifier now reports restaurant-level checked, unavailable and unresolved counts even when restaurants share a source.
- V5 candidates are labeled `PARTIAL` because a chain-wide official source does not prove applicability at the specific location and V5 does not expose a separate deal name. Missing coverage or an unmappable candidate cannot become `NO_MATCH`.
- Offline bridge/runner and coverage tests pass. The loopback server health route was exercised; headless Chromium execution against live sources, GitHub Actions execution and Cloudflare integration remain unverified. No live provider request or deployment occurred.

## September 26 result intake checkpoint

- Added bounded result chunks with stable IDs, payload digests, compact evidence and transactional insert. Repeated chunks do not duplicate results; conflicting payloads are rejected. A five-result chunk size is an invocation bound, not an overall result cap.
- A Family Deals `MATCH` must carry a defensible total in cents within budget, capacity for the selected party, restaurant/deal identity and explicit meal, price, capacity and location evidence flags. Dinner hours are required when selected.
- Added idempotent one-time Search completion, truthful coverage checks, and user-scoped paginated result/detail reads. A partial scan cannot finalize as `NO_MATCH`.
- Tested against in-memory SQLite with 12 results across three chunks, duplicate delivery, conflicting payload, false negative rejection and pagination. No engine, provider, GitHub Actions or Cloudflare resource was invoked.

Integration finding: V5's browser JavaScript performs Nominatim geocoding,
Overpass full-radius discovery, deduplication, restaurant classification and
cuisine/type filtering. Its Python `run_verification_job` receives the already
discovered restaurant list; calling that function alone would silently skip
the essential discovery stage. The new GitHub runner executes that upstream
flow and reports discovery failure as unavailable. The old V5
browser sliders cap radius at 30 miles and budget at $100, while the new web
criteria do not use those caps; the headless bridge applies exact criteria
without clamping them. V5 currently selects the best candidate per restaurant
and does not expose a separate deal-name field, so the adapter must preserve
evidence and avoid inventing an offer name. These are integration gaps, not
reasons to reduce radius coverage or loosen verification.

## September 26 job lease checkpoint

- Added a separate worker-secret boundary for internal calls, atomic bounded D1 job claims (up to ten), expired-lease reclamation, and heartbeat renewal tied to the current `claim_id`.
- Claims include exact stored criteria only after authentication. A stale or mismatched heartbeat returns conflict. Offline tests verify authentication, bounded claiming and renewal; no GitHub runner is configured.

The result intake checkpoint is recorded above; the next gate is real worker execution and dispatch.

## September 26 first Worker slice

- Added strict Family Deals criteria validation, including exact cents, party size 4–10, cuisine and restaurant type, without an arbitrary radius or restaurant count cap.
- Added an offline Cloudflare Worker module for private-beta signed cookie issuance, same-origin/CSRF checks, a D1-backed queued one-time Family Deals Search and user-scoped Search retrieval. Search responses explicitly report `dispatch: not_connected`.
- No GitHub dispatch, claim, Watch scheduling, result submission, frontend wiring, deployment, or live provider call exists yet. Do not present a queued Search as an active check.
- Node offline tests cover validation, session rejection, CSRF and queuing. The preserved V5 engine remains untouched.

The claim/lease checkpoint is recorded above; result submission remains the next gate.

## September 26 API/D1 contract checkpoint

- Added `docs/API_V1_CONTRACT.md` for public and internal routes, exact versioned criteria, truthful results, security boundaries and dispatch behavior. It defines a contract, not a running endpoint.
- Added an unapplied D1 migration for users, searches, Watches, leased jobs, meaningful Watch events, results/evidence, provider state and deduplicated in-app notifications, with due/user/status indexes.
- Added SQLite migration integrity tests to the offline suite. No Cloudflare resources were created, no credentials were handled, and no remote migrations ran.

The first Worker slice is recorded above; no browser or worker execution is connected yet.

## September 26 Family Deals web checkpoint

- The September 25 reconciliation is now published on GitHub as `1fab91b234d12b3e43f0b427e758997d75f8f267` (same tree as the previously tested local commit `e7b1040`). The checkout is aligned with remote `main`.
- Replaced the Family Deals placeholder with responsive location/current-location, unrestricted restaurant-count radius, party size 4–10, maximum total price, cuisine multi-select, restaurant type, and dinner-hours controls in the approved visual system.
- The search summary updates live. The local preview honestly reports that no source was checked; exact versioned criteria can be saved as an in-memory draft. It does not claim a verified deal or running Watch. The V5 engine and isolated adapter are unchanged.
- The next layer must render real deal-first cards only from verified normalized results, with coverage and uncertain sources kept distinct. The preview cannot generate sample matches.

The contract/schema checkpoint is recorded above; no browser route is connected to it yet.

## September 25 reconciliation checkpoint

- `run_v44.command` now launches `seat_watcher_premium.py`; all four Movies launch scripts are covered by an offline integrity regression. Engines are unchanged.
- Cloudflare free site/Worker/Cron/D1 and standard GitHub Actions form the approved future runtime. The local web preview remains in-memory; no cloud execution or persistence is deployed. See `docs/PRODUCTION_ARCHITECTURE.md`.
- New AMC catalog key obtained September 25 but not validated. Old-key recovery is closed. Catalog authorization does not imply seat inventory authorization. No live provider request was made for this checkpoint.
- The September 8 controlled CityWalk map comparison supports only the stated CityWalk case, not Burbank or general reliability.

## September 8 Home and Movies web checkpoint

- Replaced the generic light shell with the approved dark navy, purple, blue,
  and green layered visual system, including responsive top/side navigation.
- Home now follows the approved two-module hierarchy: Movies and Family Deals
  only. Active Watches and Recent Results remain hidden until records exist.
- Movies now exposes the approved five-step workflow: movie discovery/title,
  location/radius/theater selection, all three date modes and time bounds, seat
  count/minimum row, formats, ranking preferences, and advanced exclusions.
- The live summary updates from the configured search, and Save as Watch sends
  the exact Movies criteria through the existing in-memory watch contract.
- All provider-facing actions are explicitly offline-preview behavior. Search
  reports the AMC-blocked source as unavailable rather than inventing results or
  treating it as no match. No AMC request, browser engine, or module code changed.
- Rendered Home and Movies checks passed in the local browser; exact-criteria
  Watch creation was exercised with no browser console errors.
- Offline verification: **108 tests passed** (core 6, web 12, adapters 12,
  Family Deals 19, Tickets 12, Movies 47), plus repository structure checks.

The reconciliation gate is complete; the current single NEXT TASK is above.

## September 8 recovery checkpoint

Recovered clean `main` at `6a9a9982fb97879ec6088dd982b640d40d0e05c4` and
inspected history, all four authoritative docs, module status, web/core/adapters,
and the six UX/product/design baselines. See `docs/RECOVERY_CHECKPOINT.md` for
the implementation gap matrix, verification, and resume sequence.

- Movies and Family Deals are the only active user-facing modules. Tickets is
  shelved: hidden from shell navigation/cards/draft choices and `/api/modules`;
  new Ticket drafts are rejected. Engine, contracts, adapter, and tests survive.
- Drops remains documented future scope only; placeholder module cards removed.
- Restored the exact original visual mockup as a valid PNG. The committed JPEG
  was unreadable. The PNG is the target, not loose inspiration.
- The former light-themed generic shell was superseded by the September 8 Home
  and Movies web checkpoint above. Family Deals and full Watches UX remain.
- No provider calls, browser launches, engine rewrites, or live acceptance claims.
- Verification: **105 offline tests passed** (core 5, web 10, adapters 12,
  Family Deals 19, Tickets 12, Movies 47), plus structure and JavaScript syntax
  checks. Recovery used Python 3.12.14 with the pinned dependency versions;
  fresh Python 3.14 setup and rendered-browser acceptance remain unverified.
- This fresh clone contains no recovered credentials or pre-existing user edits.
  Historical `.env` statements below refer to the original machine, not this clone.

## September 4 AMC reliability pass — V44.7

- The existing catalog key began succeeding later in the session; this supersedes
  the earlier 14:15 UTC rejection below. No credential or permission changes.
- Official catalog: 523 records across three pages; seven open AMC locations
  within ten miles of CityWalk. Find theaters now prefers these official IDs,
  coordinates and URLs, with a labeled map fallback; no arbitrary result cap.
- API discovery matched **32/32 browser-observed showtimes** across three LA
  theaters, seven theater/date combinations, and dates through September 20.
  This limited sample is not proof of nationwide or end-to-end >90% reliability.
- Live seat comparison exposed a real fallback-decoder bug: unnamed layout gaps
  could supply the next seat's availability/coordinates, and seat types were lost.
  A reported Burbank D1–D4 group included wheelchair spaces/companion positions.
- V44.7 adds whole-object decoding ahead of the existing fallbacks and requires
  agreement with the displayed seat map. Ordinary-seat matches exclude accessible
  spaces/companions. Unknown/partial/conflicting inventory remains unavailable.
  Grouping/ranking, Mac scrolling, Activity, UI and watch filters remain intact.
- API pagination/schema failures and browser date failures no longer silently
  succeed with incomplete/empty results. Authorization messages do not guess an
  activation date. Seat HTTP 403/429 disables further requests for that run;
  diagnostic URLs omit query tokens.
- Live testing stopped after an AMC HTTP 429 and the user's report of no Windows
  administrator rights. No further browser launches on this machine. The final
  decoder/map-gap corrections are **offline-verified only**, not live-accepted.
- Tests: **104 passed**, including **47 Movies tests**. No other module engine,
  machine permissions, credentials, or tracked personal settings changed.
- Full evidence, provider alternatives and >90% acceptance definitions:
  [AMC reliability review](docs/AMC_RELIABILITY_REVIEW.md).

## September 4 portability checkpoint

- Consolidated the September 2 agent guidance into `AGENTS.md`, preserving
  protected module behavior and the current Movies acceptance priority.
  `RUNBOOK.md` now identifies the New Machine Start up reference and includes
  the session-start prompt. Documentation-only reconciliation; no module code,
  runtime configuration, or user data changed. Reviewed document consistency
  and whitespace; the 80-test result below remains the prior code checkpoint.

- GitHub source of truth: `https://github.com/johntholak/Universal-Watcher`, `main`.
- Preserved the existing uncommitted Family Deals hours fix and Ticket adapter.
- Added root setup/test/run entry points, shared dependency manifest with pinned
  transitive constraints, blank module environment templates, and line-ending rules.
- Reconciled the four authoritative docs with current code and documented the
  clone/setup/configure/test/run/pull/push workflow and local-state limitations.
- Windows Python 3.14.7 clean-environment installation and Chromium setup passed.
- Root launcher served HTTP 200 from another working directory; blank Chromium
  launch and Tk initialization passed. Tracked/proposed files and local Git
  history passed checks for known local credentials, common token/private-key
  patterns, and user-specific absolute paths; no detected secrets were committed.
- All 80 offline tests passed: core 5, web 9, adapters 12, Family Deals 19,
  Tickets 12, Movies 23. These do not establish live provider acceptance.
- September 4, 14:15 UTC (07:15 PDT): a catalog-only Windows probe using the
  existing AMC client and configured key still received HTTP 403 / error 12005
  (`Unauthorized VendorKey`) on theatre discovery. No dated showtime requests,
  seat requests, or browser fallback ran. Authorization remains unconfirmed;
  the announced Thursday deployment schedule is not proof of activation or
  an explanation for the continuing rejection. Credentials were not displayed.
- macOS/Linux fresh setup and live GUI/browser acceptance remain unverified.
- Credentials remain ignored on the original machine and must be configured
  securely on a new machine; Git does not synchronize runtime state.

**LIVE ACCEPTANCE GATE:** On the Mac, after AMC access/rate limits permit, run one small
V44.7 catalog-plus-seat comparison using the original Odyssey / IMAX 70MM /
CityWalk case and Burbank's ordinary-seat case. Verify the final structured
decoder and full-map agreement before expanding to the documented >90%
acceptance set and NEXT BEST/scrolling/Activity/handoff regression. Do not
launch more browsers or require admin access on this Windows machine. Keep
live web adapters gated until that acceptance passes.

## Status legend

- 🟢 Working / proven core
- 🟡 Active development / usable but incomplete
- 🟠 Early / partial
- ⚪ Planned
- 🚫 Outside this project

## Master module table

| Module | Status | Current baseline | In this repo? | Immediate next step |
|---|---|---|---|---|
| Universal Watcher Core | 🟡 | Minimal watch/result contracts + Family Deals and Ticket mappings | Yes | Keep live execution gated; add execution boundary after Movies acceptance |
| Universal Watcher Web App | 🟡 | Approved dark Home and offline Movies search/Watch flow | Yes | Build Family Deals, then complete shared Watches; live execution gated |
| Family Deals | 🟡 | V5.0 Fast Filters + Semantic Verifier; V5.0.1 conservative hours parsing; isolated result adapter mapping | Yes, intact import | Live benchmark V5, validate every claimed match, improve hours/source coverage |
| Seat Watcher | 🟡 reconstructed / live regression in progress | V44.7; catalog authorized; 32/32 sampled showtimes; final seat fixes offline-only; 47 Movies tests | Yes | Mac seat-map comparison, then broader reliability/NEXT BEST acceptance |
| Ticket Watcher | Shelved / hidden | Bundle V1.11; Ticketmaster V1.9 path and isolated mapping preserved | Yes | Preserve only; reactivation requires a new decision |
| Theater Discovery | 🟠 | Separate-workstream decision made | Placeholder | Build non-AMC providers independently, then normalize into Seat Watcher |
| Drop Watch | ⚪ | Planned | Placeholder | Start only after Universal shell/integration foundation |
| Automated Job Hunter | 🚫 | Separate product | No user-facing module | Maintain in its own project/repository |
| Event Producer Copilot | ⚪ | Planned, deliberately last | Placeholder | Do not lose; build after prior modules |
| Car Search | ⚪ parking lot | Feasibility explored | Parking-lot note | Not active roadmap |
| Restaurant PDF Menu Builder | 🚫 | Separate project | No | Keep separate |

## Big-picture guardrail

Universal Watcher work is intentionally split into two connected lanes:

1. **Module verification:** Movies is the current live proof lane because its
   AMC date and inventory behavior is the highest-risk unfinished area.
2. **Platform foundation:** the shared contracts and web shell are being built
   for the active Movies and Family Deals product, with preserved contracts
   that can support later approved modules.

After Movies API/Mac acceptance, connect proven Movies and Family Deals engines
through adapters. Tickets remains shelved even after that gate passes. Theater
discovery and later modules remain roadmap work, not competing priorities.

While the Movies gate is waiting on AMC/API and Mac access, isolated adapter
mapping is allowed when it only translates an existing module job record and
does not start live monitoring or alter that module's engine. Family Deals and
Ticket Watcher now have these mappings; their live benchmarks and web
execution remain separate acceptance steps.

---

# 1. Universal Watcher Core

## Current state

The conceptual common engine is:

**Discover → Normalize → Filter → Verify → Rank → Monitor → Alert → Act**

This has not yet been extracted into a shared production package. That is intentional. The real modules should inform the shared interface before a large refactor.

The first narrow contract preview now lives in `core/contracts.py`. It defines
module-neutral watch definitions, evidence, truthful result outcomes, and a
small `run_once` adapter protocol. Family Deals and Ticket Watcher now have
offline mappings into it; no live module is wired to it yet.

## Next

The initial extraction sequence is now:

1. [x] define a small module adapter contract
2. [x] define watch/result models
3. [ ] define job/worker execution model
4. [ ] define server-vs-local-helper boundary
5. [x] avoid premature rewrites

The first contract step is complete. The web shell now exercises the watch
definition boundary through a dependency-free in-memory preview API. Family
Deals and Ticket Watcher both have isolated result adapter mappings, while
live adapter execution remains gated on Movies seat reliability and Mac
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
- The current suite has 19 tests, including conservative dinner-hours parsing.
- **Master Repo V1 verification:** all 19 Family Deals tests pass in the current repository.
- **Universal Watcher adapter verification:** Family Deals and Ticket Watcher
  mappings pass their offline contract tests; this does not claim that either
  live module meets the final product specification.

## Major unresolved areas

- V5 speed changes have not yet been properly live-benchmarked by the user.
- Hours/open-tonight verification remains a separate evidence problem.
- Official-source resolution coverage is incomplete.
- A prior broad run left roughly 372 of 697 restaurants without a resolvable official source.
- Every live claimed match still needs skeptical evidence review.
- The Universal Watcher adapter is plumbing only; it does not make the V5
  engine live or imply that Family Deals already meets the final product
  specification.

## Hard rule

Never restore an arbitrary top-N restaurant limit to make broad searches feel faster.

## Exact next Family Deals step

On the Mac, run the documented West Hills / 7-mile / $50 / 4-person / open
tonight benchmark for Any restaurants, Independent + local, and one repeated
search. Capture the coverage and elapsed-time numbers, then inspect every
claimed match against its evidence source. Do not make another parser or speed
change until that live evidence identifies the next failure or bottleneck.

---

# 3. Seat Watcher

## Historical source provenance

The post-Codex working state is documented as:

- branch: `main`
- lost original-source commit: `7a19015` — `Clean duplicate and incomplete theater results`
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

## Historical progression and remaining acceptance

The dated V44.2–V44.6 observations below are historical; the V44.7 September 4
section above supersedes authorization and capture-only conclusions. The final
seat reader still needs Mac acceptance.

- V44.2 live testing on Sept. 1 proved current-day discovery/seat checking but exposed false-empty future-date discovery and an overly short stopping policy. V44.4 followed AMC's selectable calendar, but the Sept. 2 acceptance evidence still showed skipped real dates and failed inventory capture.
- V44.5 now requires the selected date's showtime results to reach a stable, meaningful state before extraction; waits for tracked seat-response parsing work; accepts AMC's documented `seatName` field without changing grouping logic; and distinguishes captured-no-match from inventory-unavailable throughout aggregation and final messaging.
- Sept. 2 Windows live diagnostic: CityWalk returned four Odyssey IMAX 70MM showtimes for Sept. 2, and all four seat pages produced captured inventory with valid no-group outcomes. Seat capture is restored in this environment.
- The same live diagnostic proved the remaining future-date cause: AMC returns HTTP 403 for its dated React results request (including in visible Chromium), leaving the current-day DOM unchanged. V44.5 now reports this as `SHOWTIME DISCOVERY UNAVAILABLE` and cannot convert it into a zero-showtime/no-seat conclusion.
- V44.5 passes 18 offline regression tests. Run it on the Mac to determine whether AMC permits that environment's dated request; pursue approved Showtime API access as the reliable provider path if it does not.
- V44.6 adds an optional approved AMC Showtime API discovery adapter. It resolves theatre IDs by slug, follows all result pages, applies the existing movie/format/time filters, and passes showtime IDs to the unchanged browser seat engine. It activates only when `AMC_VENDOR_KEY` is configured; otherwise the existing browser discovery path remains active.
- An AMC vendor key was issued and stored only in the ignored module-local `.env` file. The September 2 success-page observation described Thursday production deployments, but the September 4 catalog probe still returned HTTP 403 / error 12005, `Unauthorized VendorKey`. The reason for continuing rejection is not established. V44.6 recognizes that state, reports it once, disables API retries for the remainder of a normal run, and uses the website fallback. Confirm authorization with AMC; do not assume the key is active or bypass the rejection.
- Verify theater cleanup visually.
- Run a controlled live Next Best exhaustion test.
- Stress Specific Date and Date Range after the date-control changes.
- Windows end-to-end regression.
- UI/UX is not considered finished.
- Eventually expose the engine through a module/API adapter instead of rebuilding it.

## Protected

Do not casually rewrite the AMC engine. See `AGENTS.md`.

---

# 4. Ticket Watcher — shelved / hidden

Preserve the following historical capability baseline. No current marketplace
expansion or live web integration is authorized by this roadmap.

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
- [x] Document root setup/run workflow; fresh Mac/Linux acceptance remains pending.

### Milestone B — Universal Watcher Web Shell V1
One web application with initial module entry points and active-watch structure.

Initial integrations should prioritize already-developed modules rather than inventing new ones.

The first static shell foundation is now in `web/`. It is a dependency-free
preview with module entry points, active-watch/activity/results-and-evidence
surfaces, and a local draft flow. It does not start live watchers or alter the
protected Movies engine.

### Milestone C — Module integration
- Family Deals adapter (isolated result mapping started; live execution pending)
- Ticket Watcher mapping preserved; integration shelved until explicitly reactivated
- Seat Watcher adapter/local-helper strategy
- Theater discovery expansion

### Milestone D — Drop Watch
Build using the common platform.

### Milestone E — Event Producer Copilot
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
- Historical original-machine local data: `modules/seat-watcher/.env` held the issued key and was intentionally Git-ignored. This does not establish its presence on a new clone. Never commit or quote credentials.
