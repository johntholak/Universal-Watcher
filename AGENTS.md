# AGENTS.md — Universal Watcher Operating Rules

## Mandatory startup sequence

Before doing anything in this repository, read completely:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`

Then inspect the module-specific handoff/status file for the module being changed.

Inspect repository structure, the current branch/state, relevant implementation,
and available tests before modifying files. Compare documentation with actual
code. Code establishes what exists; documentation establishes product intent
and recorded decisions. Investigate discrepancies instead of blindly trusting
either. These rules apply repository-wide unless a more specific AGENTS.md applies.

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

Keep document responsibilities separate: `AGENTS.md` defines agent operating
rules, `PRODUCT_VISION.md` defines the product, `PROJECT_STATUS.md` records the
current state and one primary next task, and `RUNBOOK.md` explains setup,
running, testing, and diagnosis. Do not rely on a previous conversation to
recover project state or combine these documents into one large instruction file.

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

1. Check `git status`; preserve any existing local work.
2. On a clean tree, run `git pull --ff-only` before beginning work.
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

Before replacing working logic, identify its edge cases and capture baseline
inputs, expected results, and timing where relevant. Large rewrites require a
concrete benefit, an explanation of the preserved behavior, and incremental
verification. Debug by reproducing, isolating, gathering evidence, and fixing
the smallest responsible layer; remove obsolete diagnostic noise afterward.

Measure performance before optimizing: discovery and checking duration, counts,
duplicates, requests, provider latency, browser operations, and cache hits.
Separate expensive source discovery from repeated inventory monitoring where
useful. Use bounded concurrency, batching, pagination, caching, and incremental
updates while respecting provider limits and local resources. Cache records
need freshness metadata and expiry appropriate to the volatility of the data.

Keep provider requests, legitimate authentication, parsing, errors, rate limits,
and retries inside provider adapters where practical. Normalize results without
losing important evidence or provenance. Deduplicate only with sufficient
confidence. A provider failure should preserve valid results from other sources
and visibly report incomplete coverage; unavailable is not a valid no-match.
Never invent missing prices, availability, classifications, or other facts.

Prefer official APIs, authorized/public structured sources, public web
information, then appropriate browser automation. Do not make bypassing access
controls a requirement. Extract shared infrastructure when real modules show
the need; avoid speculative abstractions or unnecessary stack changes.

Add dependencies only after considering existing libraries, maintenance,
platform support, and runtime cost. Centralize user settings where practical
and avoid assumptions about usernames, absolute paths, shells, or browsers.
Never print credentials or session secrets in logs.

Keep implementation complexity beneath the interface. Use plain-language
errors with diagnostic detail in logs. When UI work is requested, provide clear
hierarchy, depth, contrast, cohesive visuals, and obvious interaction states;
avoid unrelated redesign while functionality is unstable. Preferred new
user-facing module names are Movies, Tickets, Family Deals, Drops, and Jobs.
Do not introduce HUNT into new user-facing names.

Every meaningful change requires relevant verification: existing tests,
focused regression tests where practical, or a repeatable manual check.
Prefer offline fixtures for provider parsing, normalization, and filtering.
Completion requires verified behavior, no known major regression, current
documentation, and a clear next task. Document unrelated issues in the
appropriate backlog and continue the requested scope unless safe progress is
blocked. Do not silently weaken requirements or pursue unrelated improvements.

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

The current authoritative source is the reconstructed V44.7 tree in `modules/seat-watcher`. Its final seat-verification corrections await live Mac acceptance. The lost original commit is historical provenance, not a recoverable baseline. Do not replace this source with an old ZIP or another machine's folder.

### Family Deals

Preserve full-radius discovery. There is no arbitrary top-N restaurant cap.

Do not improve speed by silently checking fewer restaurants. Improve speed through filtering, concurrency, caching, source deduplication, and architecture.

A result should not be called verified unless price, offer identity, serving capacity, location applicability, and required availability evidence are defensible.

Preserve radius, price, restaurant-type, and practical cuisine filtering.
Find actual meals, deals, and specials. Restaurant-type choices are Any,
Independent + local, Independent only, and Chains only. Independent means a
standalone or extremely small operation; local generally means a small local
group of approximately five locations or fewer; chain means a larger
multi-location or multi-market network. Insufficient evidence means unknown,
not a guessed classification.

### Ticket Watcher

Preserve the working Ticketmaster watcher while experimenting with additional marketplaces independently.

Do not bypass anti-bot or access controls. Prefer documented/approved APIs or other permitted integrations when a marketplace blocks automation.

## Current development order

Read the current milestone and single NEXT TASK in `PROJECT_STATUS.md`.
Historical priority statements in imported notes do not override newer status.
The broader sequence is source-control reliability, web shell, then integration
of proven engines; module roadmaps are context rather than competing priorities.

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

## Portable setup contract

Use `python manage.py setup --browsers`, `python manage.py test`, and
`python manage.py run` from the root. See README for Python command variants.
Keep dependency constraints and module manifests consistent. Never commit local
`.env` files, credentials, virtual environments, or machine-specific absolute paths.
Preserve pre-existing user changes. Keep exactly one global NEXT TASK in
PROJECT_STATUS.md; module roadmaps are context, not competing session priorities.
