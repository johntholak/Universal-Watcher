# PRODUCT_VISION.md — Universal Watcher

## One-sentence vision

Universal Watcher is a personal internet agent that continuously searches fragmented sources, understands a user's real criteria, verifies what it finds, and alerts or routes the user to the right opportunity when it appears.

## End product

The end product is **one usable web application**, not separate standalone products.

A user should be able to sign in from a Mac, PC, phone, or browser and see one control center:

- create a new watch
- see active watches
- see matches and evidence
- pause/resume watches
- change criteria
- review history
- open the destination when a match appears
- manage notifications and devices

Example module entry points:

- Movie Seats
- Tickets
- Family Dinner Deals
- Drop Watch
- Jobs
- future modules such as Car Search

## Product architecture

The web application is the control plane.

Not every watcher must literally run inside the browser.

A likely architecture is:

```text
Universal Watcher Web App
          |
          v
Universal Watcher API / Watch Manager
          |
          +--------------------+
          |                    |
          v                    v
 Shared Core Services      Module Adapters
          |                    |
  discovery/filtering     Seat Watcher
  verification/ranking    Ticket Watcher
  schedules/history       Family Deals
  alerts/results          Drop Watch
                          Job Hunter
          |
          v
Server Workers and, where necessary,
a small Universal Watcher local helper
for browser-dependent tasks.
```

For modules such as Seat Watcher or certain ticket marketplaces, a local helper may eventually run browser automation on a user's computer while the web app remains the single interface.

## The reusable engine

The common product pattern is:

**Discover → Normalize → Filter → Verify → Rank → Monitor → Alert → Act**

This is more than search.

A normal search engine returns pages. Universal Watcher should do the scavenger hunt:

- identify the relevant universe
- search enough sources to justify coverage
- understand the user's actual constraint
- distinguish real matches from misleading nearby text
- keep checking when the condition can change
- explain what was checked
- surface only defensible matches
- route the user to the next action

## Module strategy

Existing modules are laboratories for the common platform.

### Family Deals

Teaches Universal Watcher:

- geographic universe discovery
- source resolution
- deduplication
- evidence extraction
- semantic verification
- full-coverage transparency
- caching and concurrency

### Seat Watcher

Teaches Universal Watcher:

- dynamic site automation
- live inventory monitoring
- complex structured extraction
- ranking
- exact-match alerting
- browser handoff

### Ticket Watcher

Teaches Universal Watcher:

- event matching
- multiple marketplaces
- price thresholds
- live offer monitoring
- source-specific capabilities
- anti-automation/API constraints

### Drop Watch

Will test whether the common watcher infrastructure generalizes cleanly to releases, restocks, price/availability changes, and similar conditions.

### Automated Job Hunter

Will test broad multi-source discovery, deduplication, fit scoring, monitoring, and prioritization.

### Event Producer Copilot

Remains on the roadmap but comes after the watcher platform is mature.

## Integration principle

Do not rewrite proven engines merely because the final product is web-based.

Instead, progressively separate:

```text
module UI
    |
module engine
```

into:

```text
Universal Watcher Web UI
        |
Universal Watcher API
        |
module adapter
        |
proven module engine
```

Seat Watcher is the clearest example: the valuable AMC engine survives. Its current CustomTkinter interface can eventually become a legacy development interface once the web app controls the engine.

## Product quality principles

1. **Correctness over quantity.**
2. **Coverage should be visible.**
3. **Uncertainty should be labeled, not guessed away.**
4. **Speed should come from architecture, not hidden reductions in coverage.**
5. **Modules should share infrastructure without erasing necessary source-specific logic.**
6. **One account and one interface should eventually manage every watch.**
7. **A user should not need to understand scraping, APIs, browser automation, or workers.**
8. **The product should feel like an agent doing work, not a developer dashboard.**

## Current product milestone

The immediate milestone is **Universal Watcher Foundation / Master Repo V1**:

- establish one authoritative repository
- preserve current module baselines
- make status and run instructions recoverable on any computer
- configure a shared Git remote
- import the current Seat Watcher post-Codex source
- then begin the first Universal Watcher web shell

The restaurant PDF menu builder is explicitly outside this product.
