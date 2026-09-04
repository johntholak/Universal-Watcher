# Universal Watcher

This repository is the master home for the Universal Watcher project.

Universal Watcher is one product with multiple watcher modules. The long-term product is a single web application where a user can create, monitor, review, and act on watches across different domains such as movie seats, tickets, restaurant deals, product drops, jobs, and future categories.

## New machine: start here

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

## Read first

Before making any change, human or AI contributors must read these four files in order:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`

Those files are the authoritative project-management layer.

## Current repository snapshot

The current repository contains:

- Family Deals V5.0 source, imported intact from the latest saved Codex handoff bundle.
- Ticket Watcher V1.11 source bundle, including the working Ticketmaster live-watcher path and StubHub diagnostics.
- Seat Watcher V44 reconstructed post-Codex source, built from the user's uploaded Depth/Layering baseline plus the saved August 28 Codex handoff. This is a reconstruction, not a byte-for-byte recovery of Git commit `7a19015`.
- Placeholder module directories for Theater Discovery, Drop Watch, Job Hunter, and Event Producer Copilot.
- Initial shared watch/result contracts and a dependency-free Universal Watcher
  web-shell preview for the future control center.
- Isolated Family Deals and Ticket Watcher adapters that map existing module
  outcomes into the shared result/evidence contract; live adapter execution
  remains gated.

## Important naming rule

`HUNT` is a legacy/temporary code name that remains inside the imported Family Deals source. It is not the umbrella product name. Use **Universal Watcher** for the overall product until a permanent brand name is chosen.

## Explicit exclusion

The restaurant PDF menu builder is a separate project and must not be added to this repository unless the user explicitly changes that decision.


## V5 Movies Next Best change

Movies `NEXT BEST` no longer uses a 14-day search horizon. It advances one calendar day at a time through AMC's currently selectable date range, tolerating gaps with no requested movie/format. A 35-day ceiling exists only as a safety guard if AMC's date selector fails to expose a reliable endpoint.

## Work mode handoff

When opening this repository in ChatGPT Work, read `WORK_START_HERE.md` after the four root project files.
