# RUNBOOK.md — Universal Watcher

This file answers one question: **How do I safely pick this project up on any computer?**

## New machine: start here

This is the repository's **New Machine Start up** reference. After setup, open
the repository folder in your coding agent and give it this instruction:

> Read AGENTS.md, PRODUCT_VISION.md, PROJECT_STATUS.md, and RUNBOOK.md in that
> order. Inspect the current repository state and relevant module status.
> Tell me the current milestone and next task, then help me continue.

Agent rules live in [AGENTS.md](AGENTS.md); current priorities live in
[PROJECT_STATUS.md](PROJECT_STATUS.md). These committed documents travel with
the repository, so a previous chat or a separate startup task is not required.

The authoritative repository is https://github.com/johntholak/Universal-Watcher
(branch `main`). Install Git and Python **3.14 with Tk support** first. Authenticate
with GitHub using your own account; access to the repository is required.

```sh
git clone https://github.com/johntholak/Universal-Watcher.git
cd Universal-Watcher
python manage.py setup --browsers
```

On Windows, use `py -3.14` in place of `python` if needed. On macOS/Linux use
`python3.14`. No virtual-environment activation is required. Setup creates a
repository-local `.venv`, installs the pinned dependency set and Chromium,
and creates missing module `.env` files without overwriting existing ones.
Use `python manage.py setup` to omit Chromium for the web preview, Family
Deals, offline tests, and ticket demo. Live Movies/Tickets require Chromium.

Configure only the modules you need:

| File | Setting | Required for |
|---|---|---|
| `modules/seat-watcher/.env` | `AMC_VENDOR_KEY` | Optional approved AMC catalog access; blank uses browser discovery |
| `modules/ticket-watcher/.env` | `TICKETMASTER_API_KEY` | Live Ticketmaster event discovery; not needed for demo |

Retrieve keys from your password manager or securely from your existing
machine. Git deliberately does not transfer them. There is no root `.env`:
the existing engines read their module-local files. Environment variables
take precedence. Blank templates contain no usable credentials.

Then verify and launch:

```sh
python manage.py test
python manage.py run
```

Open http://127.0.0.1:8080. This is the **web preview**, with in-memory drafts;
it does not start live watchers and its state does not follow you to another
machine. Stop a running server with Ctrl+C.

| Command | Application |
|---|---|
| `python manage.py run` | Web preview on port 8080 |
| `python manage.py run family-deals` | Family Deals, port 8765 (up to 8774 if busy) |
| `python manage.py run movies` | Movies desktop interface; requires a graphical session and Tk |
| `python manage.py run tickets-demo` | One offline ticket demo cycle |
| `python manage.py run tickets` | Existing live Ticketmaster watcher |

Commands resolve paths relative to `manage.py`; launchers do not depend on a
particular username, drive, or clone-folder name. Existing module launchers
remain available, but may use their own separate module virtual environments.
Use the root commands above for the shared environment.

Windows/Python 3.14.7 setup and offline tests are verified. The same Python
launcher supports macOS/Linux, but fresh installation and live GUI/browser
acceptance on those systems remain unverified. On Linux, install your
distribution's Python Tk and Playwright system libraries if missing; a desktop
session is required for Movies. Do not copy `.venv` between machines.

## Each work session and switching machines

Before starting, run `git status`, then `git pull --ff-only` on a clean working
tree. If you have local work, commit it or deliberately stash it before pulling;
never discard it to force a pull. Rerun setup when dependency files change.
Read `AGENTS.md`, `PRODUCT_VISION.md`, `PROJECT_STATUS.md`, and `RUNBOOK.md`.

Before leaving:

```sh
python manage.py test
git status
git diff
# Update PROJECT_STATUS.md with the result and one NEXT TASK.
git add <reviewed-files>
git diff --cached
git commit -m "Describe the completed checkpoint"
git push origin main
git status -sb
```

Stage explicit reviewed files, especially when settings or diagnostics changed.
If a push is rejected, fetch and reconcile the other machine's commits; never
force-push over them. A successful push is the handoff, not closing the app.
On another machine, clone once; thereafter pull in that same clone.

The repository preserves source, docs, and committed configuration. Local
credentials, browser sessions, logs, caches, virtual environments, and preview
drafts are not synchronized. Family Deals caches under `~/.hunt_cache`;
it can rebuild that cache. Review changes to tracked Movies `settings.json`
and Tickets `watch.json` before committing personal preferences.

## 1. Every work session

Before coding:

```text
Read AGENTS.md
Read PRODUCT_VISION.md
Read PROJECT_STATUS.md
Read RUNBOOK.md
```

If a shared Git remote has been configured:

```bash
git pull --ff-only
git status
```

Then read the relevant module handoff/status file.

Do not start from an old ZIP if the Git repository exists.

---

# 2. Current repository setup status

Master Repo V1 contains actual source for:

- `modules/family-deals`
- `modules/ticket-watcher`

Master Repo V4 contains a reconstructed post-Codex Seat Watcher with the first Mac live-feedback fixes in:

```text
modules/seat-watcher/
```

It was reconstructed from the uploaded V44 Depth/Layering baseline using the saved August 28 Codex handoff. It is not a byte-for-byte recovery of lost commit `7a19015`.

A local Git repository is initialized, the reconstructed V44.6 baseline is
committed, and the shared GitHub remote is configured as `origin`. The current
remote baseline is the `main` branch. Before changing files on another
computer, pull first and confirm a clean status.

## Shared contract preview

The first small control-plane contract layer is in:

```text
core/contracts.py
```

Verify it from the repository root:

```text
python -m unittest discover -s core -p "test_*.py" -v
```

These contracts are not connected to live modules yet. Keep the existing
Movies, Tickets, and Family Deals engines behind adapters until Movies seating
reliability and Mac acceptance regression are complete. Catalog access now works.

---

# 3. Family Deals

Path:

```text
modules/family-deals/
```

## Mac

Preferred:

```bash
cd modules/family-deals
python3 server.py
```

Or double-click:

```text
start_hunt.command
```

The application normally starts on:

```text
http://127.0.0.1:8765
```

If occupied, it may try ports 8766 through 8774.

Tests:

```bash
cd modules/family-deals
python3 -m unittest discover -s tests -v
```

Expected V5 handoff baseline: 13 passing tests. The current repository adds
six hours-evidence regression tests, for 19 passing Family Deals tests.

Next live benchmark on the Mac:

- West Hills, CA
- 7 miles
- $50 maximum total
- 4 people
- Open tonight enabled
- Run Any restaurant type / Any cuisine, then Independent + local / Any
  cuisine, then repeat one identical search to measure cache benefit

Save the coverage counts, elapsed times, and evidence for every claimed match.

## Windows

Use:

```text
start_hunt.bat
```

or run `python server.py` from the module folder.

## Notes

`HUNT` remains in filenames/UI as legacy internal naming. Do not perform a broad rename during functional work.

---

# 4. Seat Watcher

Path after import:

```text
modules/seat-watcher/
```

## Current Mac launch

For the **first run of the reconstructed build**, double-click:

```text
setup_and_run_v44.command
```

That creates the local `.venv`, installs dependencies and Playwright Chromium, runs the current offline tests, and launches the app.

After setup, normal launches can use:

```text
run_v44.command
```

Equivalent from its project directory:

```bash
.venv/bin/python seat_watcher_premium.py
```

Tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Known verified environment at handoff:

- Python 3.14.7
- Tk 9.0
- CustomTkinter 6.0.0
- Playwright 1.62.0
- Playwright Chromium

If the `.venv` must be rebuilt:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

## Windows

Existing launchers in the current project:

```text
run_v44.bat
setup_and_run_v44.bat
```

The newest Mac-era fixes still need a fresh Windows regression.

## V44.7 live-regression and approved API note

A Sept. 1 live test of V44.2 showed one valid current-day Odyssey IMAX 70MM showtime, and later acceptance evidence showed skipped future showtimes plus repeated inventory-capture failures. V44.5 waits for the requested AMC date's results to stabilize before extracting them, tracks asynchronous seat-response parsing to completion, accepts AMC's documented `seatName` seat identifier, and keeps capture failures separate from valid captured-inventory negatives. NEXT BEST still follows AMC's selectable calendar to its final listed date, with a 35-day malfunction guard only.

The official AMC Showtime API is not enabled by default: it requires an approved API key. AMC states that seating API access needs separate contractual approval. V44.5 therefore preserves the existing browser engine and adds no new credentials or dependencies.

V44.6 includes an optional Showtime API discovery adapter while preserving browser seat capture. After AMC approves catalog access:

1. Copy `modules/seat-watcher/.env.example` to `modules/seat-watcher/.env`.
2. Replace the placeholder with the approved vendor key.
3. Launch normally. Activity will say `Checking via approved AMC Showtime API` when the adapter is active.

The `.env` file is ignored by Git. Never place the real key in documentation, screenshots, Activity logs, or commits.

Current key state: the existing key **began working later on September 4**,
after the earlier 14:15 UTC rejection. A complete catalog returned 523 records;
32/32 independently observed showtimes matched in the limited comparison set.
V44.7 Find theaters uses official IDs/coordinates/URLs before the map fallback.
Never expose the key in chat or logs. Catalog success is not seating API approval.

During normal app runs an authorization rejection is reported once, API attempts are
disabled for the remainder of that run, and the browser fallback remains
available. Do not infer an activation date from that rejection. Mac GUI/browser
acceptance and broader reliability remain unverified.

V44.7 corrects a live-observed escaped-payload issue: unnamed gaps could be read
as part of the next seat, losing availability/position/type information. A small
structured decoding stage precedes the old fallbacks. Before either match or
no-match, the complete displayed seat map must agree with captured inventory.
Layout gaps are excluded; wheelchair and companion positions are not ordinary
seat groups. Accessibility-specific matching remains unimplemented. Missing or
disagreeing evidence is `unavailable`, not a no-seat conclusion.

AMC HTTP 403/429 disables additional seat checks in that engine run. Stop and
wait for permitted access; do not repeatedly restart or bypass the response.
Candidate URL logs omit query tokens. The final corrected reader needs a fresh
live pass; earlier payload-capture counts do not establish seat correctness.

**Current Windows machine:** the user has no administrator rights and requested
that browser launches stop. An AMC 429 was separately observed. Finish offline
here; perform the remaining live tests on the Mac. No elevation, policy changes,
browser installation, or security bypass is needed as part of this checkpoint.

Repeatable diagnostic from the repository root, using the shared environment.
On the Mac, after access is available, begin with one date; do not launch several
diagnostic batches concurrently. The default movie is Odyssey, IMAX 70MM,
four ordinary seats, numeric minimum row 5 and an all-day time window:

```sh
.venv/bin/python modules/seat-watcher/live_amc_diagnostic.py --days 1 --check-seats
```

For a separate Burbank format/ordinary-seat comparison after that succeeds:

```sh
.venv/bin/python modules/seat-watcher/live_amc_diagnostic.py --days 1 --theatre-slug amc-burbank-16 --format ANY --check-seats
```

`--start YYYY-MM-DD`, `--movie`, `--format` and repeated `--theatre-slug` are
supported. Explicit slugs require approved catalog access. `--days` rejects
values outside 1–35 instead of silently truncating them. The diagnostic prints
each result and separate discovery/capture totals; totals are not accuracy.
It does not alert, hold seats, or open a match window. `--headed` requests a
visible test browser only when appropriate on the Mac. Windows equivalent,
if later authorized on a suitable machine: `.venv\Scripts\python.exe`.

Record the selected theater/date/time/format and expected IDs from AMC's normal
page before comparing; inspect every returned group and count unavailable
checks as unsuccessful. See [the reliability review](docs/AMC_RELIABILITY_REVIEW.md)
for the reference sample, known remaining checks and >90% acceptance definition.

Sept. 2 live result: current-day CityWalk discovery returned four Odyssey IMAX 70MM showtimes, and inventory was captured for all four. AMC returned HTTP 403 for its dated React-results request on Sept. 3 and Sept. 4 in both headless and visible Chromium. The engine reports those checks as showtime discovery unavailable. Do not treat them as empty schedules and do not bypass the access response.

## Reconstruction note

The exact source tree for post-Codex commit `7a19015` was not recoverable.
The module in this repository is a careful reconstruction from the user's
uploaded V44 baseline plus the saved Codex handoff.

Remaining live acceptance checklist (the reconstructed baseline is already committed):

1. Run `python manage.py test` (104 tests including 47 Movies tests at this checkpoint).
2. Launch it on the Mac.
3. Repeat a controlled AMC live test.
4. Verify date selection, format classification, CityWalk routing, theater cleanup, seat matching, and browser handoff.
5. Update `PROJECT_STATUS.md` with the live result.
6. Commit the acceptance evidence and updated status without secrets.

---

# 5. Ticket Watcher

Path:

```text
modules/ticket-watcher/
```

The recovered latest bundle is V1.11.

## Windows initial setup

From the module directory:

```bat
python -m venv .venv
.venv\Scripts\activate
copy .env.example .env
```

Add the Ticketmaster developer key to `.env`.

Install requirements / browser setup:

```text
SETUP_BROWSER.bat
```

Configuration:

```text
watch.json
```

Validate configuration:

```bat
python app.py --check-config
```

Safe demo:

```bat
python app.py --demo --once
```

Live Ticketmaster browser capability test:

```text
RUN_HEADLESS_TEST.bat
```

Continuous Ticketmaster live watcher:

```text
START_TICKET_WATCHER.bat
```

Ticketmaster diagnostic:

```text
RUN_TICKETMASTER_DIAGNOSTIC.bat
```

Four-ticket controlled extraction test:

```text
RUN_4_TICKET_TEST.bat
```

StubHub diagnostics:

```text
RUN_STUBHUB_DIAGNOSTIC.bat
RUN_STUBHUB_EVENT_DIAGNOSTIC.bat
```

Tests:

```bat
python -m unittest discover -s tests -v
```

## Mac

The root `manage.py` provides a platform-neutral entry point without changing the Ticketmaster logic. Live browser acceptance on a fresh Mac is still required.

---

# 6. Theater Discovery

Placeholder path:

```text
modules/theater-discovery/
```

No current standalone run command is authoritative yet.

---

# 7. Drop Watch

Placeholder path:

```text
modules/drop-watch/
```

Not built yet.

---

# 8. Automated Job Hunter

Placeholder path:

```text
modules/job-hunter/
```

Not built yet.

---

# 9. Event Producer Copilot

Placeholder path:

```text
modules/event-copilot/
```

Not built yet.

---

# 10. Universal Watcher web app

The first dependency-free shell preview is in:

```text
web/
```

Preferred local preview with the contract boundary, from the repository root:

```text
python web/server.py
```

Open `http://127.0.0.1:8080/`. This preview supports module navigation and
clearly labeled local watch drafts, including start/pause/resume/stop lifecycle
controls. It also has a module-neutral Matches & evidence surface backed by an
empty `GET /api/results` preview endpoint. It does not start Movies, Tickets,
or Family Deals monitoring and must not be treated as a production web app.

For a static-only preview without the local draft API:

```text
python -m http.server 8080 --directory web
```

The browser falls back to local draft behavior when `/api/watches` is not
available.

Verify the shell:

```text
python -m unittest discover -s web -p "test_*.py" -v
```

The shell now speaks to the shared watch/result contracts through the in-memory
preview API, including validated lifecycle transitions and an honest empty
results state. The next step is real adapter wiring after Movies seat reliability
and Mac acceptance regression. Do not change the protected Seat
Watcher engine as part of shell work.

## 11. Isolated module adapter checks

The Family Deals mapping is in `adapters/family_deals.py`. It translates
completed Family Deals V5 job records into shared result/evidence values and
keeps unresolved hours, capacity, or source coverage truthful. It does not
start the Family Deals server or make live requests.

The Ticket Watcher mapping is in `adapters/tickets.py`. It translates existing
Ticket Watcher `Match` records and keeps unknown fees, inventory, adjacency,
and incomplete source coverage visible. It does not start Ticketmaster or
change the working browser watcher.

Verify it from the repository root:

```text
python -m unittest discover -s adapters -p "test_*.py" -v
```

Live adapter execution remains gated until Movies seat reliability and Mac
acceptance regression are complete.

---

# 12. Switching computers safely

The configured GitHub origin uses the workflow above. In brief:

## Before switching away

```bash
git status
# run tests
git add <reviewed-files>
git commit -m "Describe the completed checkpoint"
git push
```

## On the other computer

```bash
git pull --ff-only
git status
```

Then tell Codex:

```text
Read AGENTS.md, PRODUCT_VISION.md, PROJECT_STATUS.md, and RUNBOOK.md before doing anything.
Then tell me the current milestone, the module I am working on, its last known good state, and the next task.
```

This is the intended cure for cross-computer / ChatGPT / Codex drift.

---

# 13. What must never be treated as source of truth

Once Git is configured, do not treat these as authoritative development sources:

- random old ZIPs
- screenshots
- a previous ChatGPT response by itself
- an old Codex sandbox
- a second unpushed folder on another computer
- an older Seat Watcher build from the Library

The repository + Git history + the four top-level documents are the source of truth.


## Movies V44.5 acceptance check

For `NEXT BEST`, Activity should show dates advancing continuously, even across days with zero qualifying showtimes. The run should end only when the latest selectable AMC date has been reached, or at the 35-day safety ceiling if AMC never exposes a reliable endpoint. Any HTTP 403 dated-results response must appear as `SHOWTIME DISCOVERY UNAVAILABLE`, not as zero qualifying showtimes.

Run the exact acceptance case from `WORK_START_HERE.md`. For every discovered showtime, Activity must show either a matched group, a no-group result backed by captured inventory, or `Seat inventory unavailable` with diagnostics. Preserve the Activity log for comparison against AMC's visible schedule.
