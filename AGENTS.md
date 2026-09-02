# AGENTS.md — Universal Watcher Operating Rules

## Mandatory startup sequence

Before doing anything in this repository, read completely:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`

Then inspect the module-specific handoff/status file for the module being changed.

Do not begin feature work until you understand the current state and the protected areas.

## The product

Universal Watcher is one product, not a collection of unrelated apps.

The intended end state is a single web-based Universal Watcher control center with shared user accounts, saved watches, results, history, notifications, and reusable watcher infrastructure.

Individual modules may use different backend mechanisms. Browser automation, local helpers, APIs, crawlers, and server-side workers can all exist behind the same web product.

## Naming

- Overall product: **Universal Watcher**
- `HUNT`: legacy Family Deals code name only
- Restaurant PDF menu builder: separate project, excluded

Do not rename working internal files merely for cosmetic consistency. Rename only through an intentional migration with tests and a recovery point.

## Source-of-truth discipline

`PROJECT_STATUS.md` and `RUNBOOK.md` must be updated whenever a meaningful change affects:

- module version or maturity
- run instructions
- dependencies
- known bugs
- completed milestones
- next task
- architecture
- a protected behavior
- local-vs-server execution requirements
- URLs, ports, launchers, or environment setup

A change is not considered complete if the code changed but the status/runbook became stale.

## Git discipline

Once a remote repository is configured:

1. Pull before beginning work.
2. Check `git status`.
3. Create a recovery commit before risky changes.
4. Make narrow changes.
5. Run relevant tests.
6. Update project documentation.
7. Commit with a specific message.
8. Push before switching computers or ending a work session.

Never use random ZIP copies on multiple computers as parallel editable sources once the Git remote exists.

## General engineering rules

- Preserve working behavior before improving architecture.
- Diagnose observed failures before rewriting logic.
- Prefer adapters around proven modules over rewrites.
- Keep module-specific logic separable from Universal Watcher shared infrastructure.
- Do not trade correctness for inflated result counts.
- Do not silently reduce search coverage to improve speed.
- Build tests around failures before fixing them when practical.
- Keep user-facing explanations in plain English.
- Avoid requiring manual line-by-line patching by the user.
- Make recovery points before risky changes.

## Universal module contract direction

Over time, modules should converge on a common conceptual contract:

1. **Discover** possible sources/items.
2. **Normalize** them into a consistent internal representation.
3. **Filter** using user criteria.
4. **Verify** claims using defensible evidence.
5. **Rank** qualifying results.
6. **Monitor** changing state when requested.
7. **Alert** when conditions are met.
8. **Act** by opening or linking to the relevant destination.

Do not force every module into an identical implementation prematurely. Stabilize the contract through real modules first.

## Protected module rules

### Seat Watcher

The post-Codex AMC backend contains hard-won behavior and must not be casually rewritten or simplified.

High-risk areas include:

- AMC showtime discovery
- live date-selector refresh verification
- format association
- Seat response interception
- multi-encoding / fallback seat parsing
- seat-position extraction
- consecutive-seat grouping
- minimum-row filtering
- ranking
- CityWalk canonical route handling
- headless-to-visible browser handoff
- Tk worker-thread/event-queue boundaries

The current working source must be imported from the user's current local Seat Watcher folder. Do not substitute an older Library ZIP as the current baseline.

### Family Deals

Preserve full-radius discovery. There is no arbitrary top-N restaurant cap.

Do not improve speed by silently checking fewer restaurants. Improve speed through filtering, concurrency, caching, source deduplication, and architecture.

A result should not be called verified unless price, offer identity, serving capacity, location applicability, and required availability evidence are defensible.

### Ticket Watcher

Preserve the working Ticketmaster watcher while experimenting with additional marketplaces independently.

Do not bypass anti-bot or access controls. Prefer documented/approved APIs or other permitted integrations when a marketplace blocks automation.

## Current development order

The immediate priority is repository consolidation and source-control reliability, then the Universal Watcher web shell and integration architecture.

Do not jump directly into Drop Watch, Job Hunter, or Event Copilot until `PROJECT_STATUS.md` says the current milestone is complete.

## End-of-session requirement

Before finishing a substantial Codex session:

- update `PROJECT_STATUS.md`
- update `RUNBOOK.md` if launch/setup changed
- note exact next step
- note any uncommitted user data
- run tests that cover changed areas
- commit/push when a remote is configured

The goal is that a different computer or a fresh AI session can recover the full state by reading this repository.
