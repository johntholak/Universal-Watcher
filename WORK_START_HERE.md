# WORK_START_HERE.md — Universal Watcher

## Purpose

This repository is the authoritative working package for **Universal Watcher**.

Universal Watcher is one product with simple user-facing modules such as:

- Movies
- Tickets
- Family Deals
- Drops
- Jobs
- Event Copilot later

Do not use **HUNT** as a new user-facing product/module name. Legacy internal names may remain until those files are naturally touched. Do not perform a risky rename-only rewrite.

The separate restaurant PDF menu project is **not** part of Universal Watcher.

---

## Required read order

Before making changes, read:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`
5. this file

Preserve proven module engines. Prefer narrow fixes, tests, and adapters over rewrites.

---

# CURRENT PRIORITY: MOVIES

Do not alter another module's proven engine while Movies is pending. An
isolated adapter or contract-mapping slice may be prepared when it only
translates existing module output and does not start live monitoring.

This priority is a verification lane, not a change to the product scope. The
Universal Watcher core and web-shell work may continue when it is module-
neutral and does not disturb the protected Movies engine. The end state still
includes working Movies, Tickets, Family Deals, theater discovery, and later
planned modules behind one control center.

The current Movies implementation is the reconstructed AMC Seat Watcher V44.7 inside:

`modules/seat-watcher/`

The reconstructed build is not the byte-for-byte lost post-Codex commit `7a19015`, but it was rebuilt from the older V44 baseline plus the detailed August 28 Codex handoff.

## What is working now

Confirmed on the user's Mac:

- App installs and launches.
- Two-finger Mac trackpad scrolling works correctly.
- Movie discovery works.
- Theater discovery works.
- AMC Universal CityWalk can be selected.
- Activity logging populates.
- NEXT BEST advances through future calendar days.
- The user can search for The Odyssey / IMAX 70MM at Universal CityWalk.
- Time filtering is active.

## Latest live acceptance run

Acceptance criteria used:

- Movie: **The Odyssey**
- Format: **IMAX 70MM**
- Theater: **AMC Universal CityWalk 19**
- Date mode: **NEXT BEST**
- Seats: **4 together**
- Minimum row: **5 or later**
- User-selected time window filters remain part of the search.

The latest run scanned from September 2, 2026 through October 6, 2026.

It found IMAX 70MM showtimes on some dates, including September 2, 3, 6, 8, 12, 14, 16, and 20, but returned zero qualifying showtimes on many intervening dates.

That pattern is believed to be incorrect. External verification showed real CityWalk Odyssey IMAX 70MM showings on dates the watcher skipped.

The latest run also repeatedly reported:

`No seat inventory captured`

for showtimes it did discover.

This must NOT be treated as equivalent to:

`No qualifying seats found`

---

# CURRENT MOVIES LIVE-VERIFICATION TARGET

V44.7 supersedes the earlier capture-only assessment. The existing AMC catalog
key began succeeding later on September 4, after the 14:15 UTC rejection.
Official discovery matched 32/32 independently observed showtimes across three
LA theaters and sampled dates through September 20. Find theaters now uses
the complete official catalog with accurate IDs/URLs and radius filtering;
map results are an explicitly unverified fallback.

Seat-map comparison exposed a fallback-decoder bug: unnamed layout gaps could
supply the following seat's availability/coordinates and seat types were lost.
A reported ordinary four-seat group included wheelchair spaces/companions.
The new structured decoding step and displayed-map cross-check are tested
offline; grouping/ranking and UI behavior are preserved. No missing or
disagreeing inventory may be reported as a valid no-match.

Final live seat verification is pending. AMC rate-limited repeated Windows
seat checks, and the user reports no administrator rights on this machine:
do not launch more browsers here or request permission/security workarounds.
Use the Mac for the remaining bounded acceptance when access is available.
See `docs/AMC_RELIABILITY_REVIEW.md` and the single NEXT TASK in
`PROJECT_STATUS.md`. The broader >90% target has not been established.

## 1. Future-date/showtime discovery was unreliable

The watcher is advancing through dates, but it is skipping real future showtimes on some dates.

Do not change the overall NEXT BEST concept.

Desired behavior:

- Search the movie the user requested.
- Search the requested format.
- Search the selected theaters.
- Apply the requested time window.
- Check every relevant AMC-selectable future date.
- Continue through gaps.
- Stop when AMC genuinely exposes no later useful date, with a roughly 30–35 day malfunction guard only as a fallback.
- Do not use an arbitrary short day cap.
- Do not stop after several empty dates.

V44.5 waits for the requested date to remain selected while showtime links or an explicit AMC empty state stabilize. The live run must confirm that this closes the observed gaps.

Potentially useful avenue:

AMC has an official developer platform / Showtime API. Investigate whether approved/public showtime data can reliably replace the browser-based date/showtime discovery layer while preserving the existing seat inventory engine. Do not assume API access exists until verified.

## 2. Seat inventory capture was failing

For real discovered showtimes the watcher repeatedly logs:

`No seat inventory captured`

This is a technical failure state, not a valid negative seat result.

Required behavior:

- `inventory captured + no matching group` -> valid `No qualifying seats found`
- `inventory could not be captured` -> `Seat inventory unavailable` / retry / diagnostic state
- never silently convert capture failure into a no-seat conclusion.

V44.5 tracks asynchronous response parsing through a bounded capture window, accepts AMC's documented `seatName` field as an alias, emits response diagnostics on failure, and preserves the hard-won parsing/grouping logic.

---

# NEXT TASK

Follow the global NEXT TASK and live-test V44.7 on the Mac to verify that it:

1. make AMC future date/showtime discovery reliable
2. restore reliable seat-inventory capture
3. distinguish inventory-unavailable from no-matching-seats
4. preserve working Mac scrolling and Activity logging
5. preserve movie/theater/format/time/seat filters
6. validate the structured decoder/map guard while preserving grouping/ranking
7. add focused offline regression coverage
8. produce a clear live diagnostic log for the same Odyssey acceptance case

Do not redesign the UI.
Do not alter another module's proven engine as part of Movies verification.
Module-neutral platform work and isolated adapter mappings may continue while
the Movies gate is pending. Do not perform broad architecture cleanup.

---

# ACCEPTANCE TEST

After the next fix, run:

- The Odyssey
- IMAX 70MM
- AMC Universal CityWalk 19
- NEXT BEST
- 4 seats together
- row 5 or later
- user's configured time window

The live run should prove:

1. real future showtimes are not skipped
2. each discovered showtime reaches a truthful inventory state
3. inventory-capture failure is explicitly reported if it occurs
4. if a valid qualifying seat group exists, the correct AMC purchase/seat page opens
5. if no valid group exists, the result is based on successfully captured seat inventory, not on a capture error

---

# PRODUCT DIRECTION AFTER MOVIES IS VERIFIED

The repository and private Git remote are now stable. A dependency-free
Universal Watcher web-shell preview has also been started in `web/`; it is
only a local draft/navigation/results surface and does not count Movies as
verified. Its Matches & evidence area stays empty until a module adapter
publishes a normalized result with evidence.
Keep the Movies API/Mac acceptance work as the next live verification step;
module-neutral platform work can continue in parallel while that gate is
pending. The next platform integration step is wiring proven module engines
through adapters, after Movies is trustworthy.

After Movies is trustworthy:

1. Freeze a master Git baseline.
2. Configure one private Git remote.
3. Use clone/pull/push as the cross-computer source of truth.
4. Integrate proven modules through adapters rather than rewriting engines.
5. Continue roadmap:
   - Drop Watch
   - Automated Job Hunter
   - Event Producer Copilot last

The overall product name is **Universal Watcher**.
