# Universal Watcher

This repository is the master home for the Universal Watcher project.

Universal Watcher is one product with multiple watcher modules. The long-term product is a single web application where a user can create, monitor, review, and act on watches across different domains such as movie seats, tickets, restaurant deals, product drops, jobs, and future categories.

## Read first

Before making any change, human or AI contributors must read these four files in order:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`

Those files are the authoritative project-management layer.

## Current repository snapshot

This V1 bootstrap contains:

- Family Deals V5.0 source, imported intact from the latest saved Codex handoff bundle.
- Ticket Watcher V1.11 source bundle, including the working Ticketmaster live-watcher path and StubHub diagnostics.
- Seat Watcher V44 reconstructed post-Codex source, built from the user's uploaded Depth/Layering baseline plus the saved August 28 Codex handoff. This is a reconstruction, not a byte-for-byte recovery of Git commit `7a19015`.
- Placeholder module directories for Theater Discovery, Drop Watch, Job Hunter, and Event Producer Copilot.
- Architecture placeholders for the future Universal Watcher core and web app.

## Important naming rule

`HUNT` is a legacy/temporary code name that remains inside the imported Family Deals source. It is not the umbrella product name. Use **Universal Watcher** for the overall product until a permanent brand name is chosen.

## Explicit exclusion

The restaurant PDF menu builder is a separate project and must not be added to this repository unless the user explicitly changes that decision.


## V5 Movies Next Best change

Movies `NEXT BEST` no longer uses a 14-day search horizon. It advances one calendar day at a time through AMC's currently selectable date range, tolerating gaps with no requested movie/format. A 35-day ceiling exists only as a safety guard if AMC's date selector fails to expose a reliable endpoint.

## Work mode handoff

When opening this repository in ChatGPT Work, read `WORK_START_HERE.md` after the four root project files.
