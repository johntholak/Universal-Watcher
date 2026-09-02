# RUNBOOK.md — Universal Watcher

This file answers one question: **How do I safely pick this project up on any computer?**

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
git pull
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
Movies, Tickets, and Family Deals engines behind adapters until the Movies API
deployment and Mac acceptance regression are complete.

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

Expected V5 handoff baseline: 13 passing tests.

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

That creates the local `.venv`, installs dependencies and Playwright Chromium, runs the nine offline tests, and launches the app.

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

## V44.6 live-regression and approved API note

A Sept. 1 live test of V44.2 showed one valid current-day Odyssey IMAX 70MM showtime, and later acceptance evidence showed skipped future showtimes plus repeated inventory-capture failures. V44.5 waits for the requested AMC date's results to stabilize before extracting them, tracks asynchronous seat-response parsing to completion, accepts AMC's documented `seatName` seat identifier, and keeps capture failures separate from valid captured-inventory negatives. NEXT BEST still follows AMC's selectable calendar to its final listed date, with a 35-day malfunction guard only.

The official AMC Showtime API is not enabled by default: it requires an approved API key. AMC states that seating API access needs separate contractual approval. V44.5 therefore preserves the existing browser engine and adds no new credentials or dependencies.

V44.6 includes an optional Showtime API discovery adapter while preserving browser seat capture. After AMC approves catalog access:

1. Copy `modules/seat-watcher/.env.example` to `modules/seat-watcher/.env`.
2. Replace the placeholder with the approved vendor key.
3. Launch normally. Activity will say `Checking via approved AMC Showtime API` when the adapter is active.

The `.env` file is ignored by Git. Never place the real key in documentation, screenshots, Activity logs, or commits.

Current key state on September 2: AMC's success page confirms the key was generated and ready to use, but also says new keys are deployed to production once per week on Thursday. The API currently returns error 12005 (`Unauthorized VendorKey`) until that deployment. The app reports the condition once and disables API attempts for the remainder of that run. Restart and retry after Thursday's deployment; do not request or expose the key in chat or logs.

Windows headless diagnostic (also accepts `--headed` for comparison):

```bat
cd modules\seat-watcher
python live_amc_diagnostic.py --start 2026-09-02 --days 3 --check-seats
```

Sept. 2 live result: current-day CityWalk discovery returned four Odyssey IMAX 70MM showtimes, and inventory was captured for all four. AMC returned HTTP 403 for its dated React-results request on Sept. 3 and Sept. 4 in both headless and visible Chromium. The engine reports those checks as showtime discovery unavailable. Do not treat them as empty schedules and do not bypass the access response.

## Reconstruction note

The exact source tree for post-Codex commit `7a19015` was not recoverable.
The module in this repository is a careful reconstruction from the user's
uploaded V44 baseline plus the saved Codex handoff.

Before making it the permanent Git baseline:

1. Run the nine offline tests.
2. Launch it on the Mac.
3. Repeat a controlled AMC live test.
4. Verify date selection, format classification, CityWalk routing, theater cleanup, seat matching, and browser handoff.
5. Update `PROJECT_STATUS.md` with the live result.
6. Then make the master Git baseline commit.

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
.venv\Scriptsctivate
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

The recovered bundle is Windows-oriented. Do not invent a Mac launcher. Port/setup should be done intentionally, preserving the working Ticketmaster logic.

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
results state. The next step is real adapter wiring after the Movies API
deployment and Mac acceptance regression. Do not change the protected Seat
Watcher engine as part of shell work.

---

# 11. Switching computers safely

Once a private Git remote is configured, the operating pattern should be:

## Before switching away

```bash
git status
# run tests
git add -A
git commit -m "Describe the completed checkpoint"
git push
```

## On the other computer

```bash
git pull
git status
```

Then tell Codex:

```text
Read AGENTS.md, PRODUCT_VISION.md, PROJECT_STATUS.md, and RUNBOOK.md before doing anything.
Then tell me the current milestone, the module I am working on, its last known good state, and the next task.
```

This is the intended cure for cross-computer / ChatGPT / Codex drift.

---

# 12. What must never be treated as source of truth

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
