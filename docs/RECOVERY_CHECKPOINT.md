# Universal Watcher recovery checkpoint

Date: September 8, 2026. Authoritative repository: `johntholak/Universal-Watcher`,
branch `main`. Recovery started from clean commit
`6a9a9982fb97879ec6088dd982b640d40d0e05c4`; no pre-existing local edits existed.

## What survived and why the docs drifted

GitHub contains the engines, core contracts, adapter mappings, draft web shell,
and approved UX documents. The work was not reconstructed from an older ZIP.
The recovered Movies engine remains the V44.7 reconstruction already in Git;
it is not the lost historical commit `7a19015`.

The last code milestone was `a2be8fb` (AMC reliability). Subsequent commits added
Movies UX (`c839396`), Family Deals UX (`15f0571`), Home UX (`165284b`), Watch UX
(`b88207d`), the visual reference (`2239924`), visual rules (`0d7fee4`), and Drops
planning (`6a9a998`). Those planning commits did not implement their designs or
update all root/module status docs. The older three-module shell therefore
contradicted the later Home decision.

## Implemented state versus approved target

| Area | Recovered implementation | Remaining work |
|---|---|---|
| Home | Light-themed overview, module cards, empty watch/activity/results panels | Approved two-card Home hierarchy; conditional watches/results; shared dark layered shell |
| Movies | V44.7 desktop engine with discovery, filters, date modes, adjacency, ranking, map verification and handoff; generic name-only web draft | Full Movies search UI with every existing control, discovered movie/theater choices, summary, rich results; safe engine boundary after Mac acceptance |
| Family Deals | V5.0.1 independent server and full-radius engine; conservative hours parsing; isolated result mapping | Approved location/radius/party/budget/cuisine/type flow and deal-first verified results in shared web UI; live benchmark/evidence review |
| Watches | In-memory drafts and lifecycle transitions; no worker is started | Save the same module search criteria; edit/check/pause/stop; persistent state and real monitoring; truthful last-check/coverage information |
| Results/core | Shared watch/evidence/result contracts; empty results API; Family Deals and Ticket output mappings | Real execution boundary, result publication and evidence UI; unavailable must remain distinct from no match |
| Tickets | V1.11 bundle/V1.9 Ticketmaster path and adapter preserved | Shelved, hidden; no expansion or integration until explicitly reactivated |
| Drops | Product baseline and placeholder directory only | Future-only; no current implementation or user-facing entry |
| Platform | Portable launch/setup source and dependency pins | Fresh Python 3.14/Mac setup verification; accounts, scheduling, notifications, local-helper boundary and cross-device state are not implemented |

## Safe recovery changes

- Reconciled the four root docs, startup reference, web README and module status
  with active Movies/Family Deals, shelved Tickets and future-only Drops.
- Removed Tickets navigation/card/select option and the future placeholder card.
  `/api/modules` exposes only active modules and new shelved/future drafts fail
  validation. Hydration hides unsupported module records from the shell without
  removing the underlying engines, shared contracts or adapter capability.
- Restored the original PNG mockup from the attachment in the referenced
  **Universal Watcher Planning** conversation
  (`6a986860-ec08-83e8-8a31-94a941be13b7`). The earlier JPEG in Git is unreadable
  by both the image viewer and Pillow; there is no earlier valid version in its
  Git history. The PNG is an exact attachment copy, not an AI reconstruction.
- Updated the visual baseline to point to the PNG and retained the invalid JPEG
  as historical provenance. Verified PNG decoding, 1224 × 1285 dimensions and
  SHA-256 `c75822b27bd3cb6e36cdc125f231edbdb2b6e25c5abd0c65641be6cc397249d0`.
  The image's illustrative Tickets navigation is superseded by active scope.
- Extended repository structure verification to include the approved baselines,
  recovered PNG and this checkpoint.

No engine implementation, dependency pin, credentials, settings, provider
configuration or personal watch configuration changed. No live provider request,
browser installation/launch, Mac acceptance, or production deployment occurred.

## Verification and environment limits

Recovery used Windows with bundled Python **3.12.14**, not the documented
Python 3.14 baseline. The root launcher correctly rejects this older interpreter;
the `manage.py` version requirement was not weakened. Standard venv/pip setup
also encountered temporary-file permission errors in this environment.

For offline verification only, the exact seven pinned wheel versions from
`constraints.txt` were downloaded from PyPI, checked against PyPI SHA-256 values,
and extracted into the ignored local `.venv` using the compatible Python 3.12
Windows wheels. This is a test-environment workaround, not a supported setup
change. No browser executable was installed or run.

Equivalent suite commands, with the test interpreter in place of `python`:

```text
python tools/verify_repo.py
python -m unittest discover -s core -p "test_*.py" -v
python -m unittest discover -s web -p "test_*.py" -v
python -m unittest discover -s adapters -p "test_*.py" -v
```

Run `python -m unittest discover -s tests -p "test_*.py" -v` separately from
each of `modules/family-deals`, `modules/ticket-watcher`, and
`modules/seat-watcher`, as the root launcher does. Module working directories
are required for their imports; do not discover them from the root directly.

Results: **105 offline tests passed**: core 5, web 10, adapters 12, Family Deals
19, Tickets 12, Movies 47. Web checks exercise served HTML, active module listing,
rejection of shelved/future drafts, draft lifecycle and honest result outcomes.
Repository structure and JavaScript syntax checks passed. These are not fresh
Python 3.14 setup acceptance, rendered-browser UI acceptance, live provider
verification or proof that the approved visual design is implemented.

## Resume sequence

The single global NEXT TASK remains in `PROJECT_STATUS.md`: on the Mac, after
AMC access permits, perform the bounded V44.7 CityWalk and Burbank seat-map
comparison in `RUNBOOK.md`. Record expected showtimes/seats from the actual
displayed map; count unavailable checks as unsuccessful. Then expand to the
documented reliability and NEXT BEST/scrolling/Activity/handoff acceptance set.
Do not retry live browser work on this restricted Windows machine.

After that gate passes, implement approved Home, then Movies, Family Deals and
shared Watches using the restored PNG and UX baselines. Preserve all existing
engine controls; a name-only draft is not a module integration. Safe offline
presentation work may proceed while the gate is pending, but live execution
must stay gated. Tickets does not reactivate when Movies passes; Drops stays
future-only. No new speculative architecture or AMC rewrite is needed.

On a supported machine, pull `main`, read the four authoritative docs and this
checkpoint, run `python manage.py setup` (add browsers only for an appropriate
live-test machine), then `python manage.py test`. Configure credentials securely
only if needed. This recovery clone has no recovered personal credentials or
uncommitted user data; its ignored `.venv` is disposable and not portable.
