# Source Inventory for Master Repo V1

## Imported intact

### Family Deals
Source snapshot: `HUNT-Codex-Handoff-v5.0.zip`
Date: September 1, 2026
Imported into: `modules/family-deals/`

### Ticket Watcher
Source snapshot: `ticket-watcher-v1.11.zip`
Date: September 1, 2026
Imported into: `modules/ticket-watcher/`

## Seat Watcher reconstruction

The user supplied `Seat_Watcher_V44_DEPTH_LAYERING`, which matches the pre-macOS-migration baseline described by the Codex handoff. The exact later Git source at `7a19015` was not recoverable. A reconstructed post-Codex V44 module is now included, implementing the documented macOS/date/format/Next Best/CityWalk/theater-cleanup changes while preserving the sensitive V44 seat parsing engine. It must receive a fresh controlled live regression before becoming the permanent baseline.

The current reconstructed Movies implementation is V44.6. It adds truthful
inventory states and an optional approved AMC Showtime API adapter while
preserving the sensitive V44 seat parsing engine. It must receive the
post-Thursday API/Mac acceptance regression before becoming the permanent
baseline.

Additional Movies support:

- `modules/seat-watcher/amc_showtime_api.py` — optional catalog client; no credential bundled.
- `modules/seat-watcher/live_amc_diagnostic.py` — repeatable headless diagnostic.
- `modules/seat-watcher/.env.example` — ignored local key template.

## Universal Watcher web shell

The first dependency-free control-center preview is in `web/`:

- `web/index.html` — module chooser, active-watch/activity surfaces, and draft dialog.
- `web/styles.css` — responsive shell styling and keyboard focus states.
- `web/app.js` — local draft/navigation behavior only; no live watcher calls.
- `web/test_web_shell.py` — focused static shell checks.

## Separate project

Restaurant PDF menu builder is not part of this repo.
