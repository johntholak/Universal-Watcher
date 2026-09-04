# Build Status

**Build label:** Seat Watcher V44 Reconstructed Post-Codex  
**Created:** September 1, 2026

This build starts from the user's uploaded V44 Depth/Layering source and
reconstructs the later August 28 Codex changes from the saved handoff.

It is deliberately **not** labeled as exact Git commit `7a19015`, because the
byte-for-byte source tree for that commit was not recoverable.

## Offline verification

- Python source syntax: passed
- Regression tests: 9/9 passed
- Sensitive V44 seat-response parsing/grouping logic: preserved from baseline

## Live verification still required on the Mac

The original handoff reported a successful Odyssey / IMAX 70MM /
Universal CityWalk live test for the lost post-Codex tree. This reconstructed
copy has not been live-tested against AMC from this build environment.


## V44.2 reconstruction fixes after first Mac live attempt

- Corrected Tk 9 TouchpadScroll decoding: vertical delta is the low signed 16-bit half.
- Removed the extra custom MouseWheel binding to avoid double scroll behavior.
- Activity panel opens automatically when a watch starts.
- Live activity is mirrored into the visible result summary while searching.
- Next Best date counters now update the cycle metric.
- Seat checks now log whether inventory was captured and whether an adjacent group was found.
- A no-match completion no longer collapses into the ambiguous word `Finished`.
- Browser-open failures after a seat match are surfaced explicitly.
- Removed remaining user-facing `hunt` wording from the Movies/Seat Watcher UI.


## V44.4 Next Best schedule-range correction

The Sept. 1, 2026 Mac test proved current-day CityWalk discovery and seat checking, but also showed that an arbitrary bounded horizon is the wrong product behavior for NEXT BEST. V44.4 waits for hydrated date options, tolerates changed option value formats/labels, verifies result refresh with showtime hrefs as well as text, and advances through AMC's live selectable calendar until the final listed date. A 35-day ceiling exists only as a malfunction guard. Fresh Mac live verification is still required.

## V44.5 discovery and inventory-state correction

- Waits for the selected date's rendered showtime state to stabilize instead of accepting the first DOM change.
- Tracks asynchronous seat-response body/parsing tasks and uses a bounded 10-second capture window.
- Supports AMC's documented `seatName` identifier as an alias while preserving the existing parser and grouping behavior.
- Separates `match`, `captured_no_match`, and `unavailable` inventory outcomes through aggregation and final messaging.
- Emits candidate response details when capture fails so the next Mac run is diagnostic.
- Python syntax and all 18 offline regression tests pass on September 2, 2026.

## September 2 Windows live diagnostic

- CityWalk discovery returned four Odyssey IMAX 70MM showtimes for September 2.
- Seat inventory was captured for all four; each produced a valid captured-inventory no-group result.
- AMC's dated React-results request returned HTTP 403 for September 3 and September 4 in both headless and visible Chromium.
- The engine now records and reports that condition as showtime discovery unavailable. It does not count the blocked response as an empty schedule or valid no-seat result.
- `live_amc_diagnostic.py` provides a repeatable, UI-free evidence run.

Live verification remains required using the exact Odyssey / IMAX 70MM / Universal CityWalk NEXT BEST acceptance case in `WORK_START_HERE.md`.

## V44.6 optional approved Showtime API adapter

- Resolves AMC theatre IDs from existing theatre slugs.
- Retrieves every paginated showtime record for each requested date.
- Normalizes API results through the existing movie, format, and time criteria.
- Feeds resulting showtime IDs into the preserved browser seat inventory engine.
- Activates only when an approved `AMC_VENDOR_KEY` is present in the environment or ignored local `.env` file.
- No new third-party dependency and no bundled credential.
- AMC has issued a vendor key, stored only in the ignored local `.env`. The success page says new keys are deployed to production once per week on Thursday; until then AMC returns error 12005 (`Unauthorized VendorKey`). The app reports this pending-deployment state once and stops repeated API attempts during that run.

## September 4 catalog authorization recheck

- At 14:15 UTC (07:15 PDT), the existing client still received HTTP 403 / error
  12005 (`Unauthorized VendorKey`) when resolving the CityWalk theatre through
  the catalog. The key was loaded locally and was not displayed.
- The announced deployment schedule does not prove activation; the continuing
  rejection's cause remains unknown and needs AMC confirmation.
- This was a catalog-only Windows check. It stopped on the first rejection;
  no dated-showtime request, seat check, or browser fallback ran.
- No engine code changed. Mac acceptance and live web integration remain pending.

## V44.7 September 4 reliability pass (current)

This section supersedes the earlier authorization and capture-only claims.

- The same catalog key now succeeds; 32/32 independently browser-observed
  showtimes matched the API in seven theater/date cases across three LA theaters.
- Find theaters now uses the complete approved catalog (523 records in the live
  sample), retaining official identities/URLs and full-radius filtering. Maps
  remain a clearly unverified fallback. Pagination fails closed if incomplete.
- Live map comparison found the fallback decoder spanning unnamed gap objects
  into a real seat and dropping seat types. D1–D4 at Burbank included two
  wheelchair spaces and a companion position, invalidating that ordinary match.
- Structured per-object decoding now precedes the preserved encoding/fallback
  paths. A separate map verifier requires complete agreement; unnamed layout
  placeholders are not physical seats. Ordinary-seat groups exclude wheelchair
  and companion positions. Accessibility-specific matching is not implemented.
- All browser discovery failures feed the unavailable counter. Seat HTTP 403/429
  disables further requests in that run; diagnostic routes omit query tokens.
- Existing adjacency/ranking, Tk boundaries, scrolling, Activity, date progression,
  format/movie/time filters and handoff code were not rewritten.
- 47 Movies offline tests pass; root suite 104. Final decoder/map-gap fixes need
  live Mac validation: repeated Windows probes encountered an AMC 429, and the
  user reports no administrator access. No further Windows browser testing.
- See `docs/AMC_RELIABILITY_REVIEW.md` at the repository root for the evidence
  set, chronology, provider decision and acceptance thresholds. No overall >90%
  accuracy or final live seating success is claimed.
