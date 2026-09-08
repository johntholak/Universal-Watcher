# Automated Job Hunter Separation

Status: Locked product decision
Date: September 8, 2026

## Decision

Automated Job Hunter is **not a Universal Watcher module**.

It should be built as a separate product with its own repository/project, product vision, status, runbook, UX, source strategy, and execution model.

Universal Watcher must not show Jobs in user-facing navigation, module cards, placeholders, draft choices, or future-module teasers.

## Why

Although Job Hunter can reuse technical ideas from Universal Watcher, its product behavior is materially different. It needs to understand a person's background and goals, score fit, manage opportunities and applications, tailor materials, support follow-up, and potentially help with interview preparation. That is broader than the everyday exact-condition discovery/watch pattern that defines Universal Watcher.

## Relationship to Universal Watcher

The separate Job Hunter product may reuse general engineering patterns such as:

Discover -> Normalize -> Filter -> Verify -> Rank -> Monitor -> Alert

That shared pattern is an implementation relationship only. It does not make Job Hunter a Universal Watcher module.

Do not create cross-product coupling merely for code reuse. Share libraries or patterns later only when a real stable interface exists.

## Universal Watcher scope after this decision

Current/future Universal Watcher product direction centers on:

- Movies
- Family Deals
- Drops

Tickets remains shelved/hidden unless viable legitimate provider access changes the product decision.

Automated Job Hunter belongs outside this product.

## Separate Job Hunter project bootstrap

When repository/project creation is available, create a dedicated Job Hunter workspace with at least:

- `AGENTS.md`
- `PRODUCT_VISION.md`
- `PROJECT_STATUS.md`
- `RUNBOOK.md`
- `README.md`
- `docs/SOURCE_STRATEGY.md`
- `docs/UX_BASELINE.md`

Initial feasibility baseline already established in planning:

- Public/legitimate ATS job-board sources can provide a viable discovery foundation.
- Greenhouse, Lever, Ashby, and SmartRecruiters are strong candidates for direct public-source discovery.
- LinkedIn/Indeed must not be required for V1.
- Do not make scraping restricted job platforms a dependency.
- Do not automate applications until discovery, fit scoring, evidence, and user approval flows are defined and tested.

## Immediate next step for the separate product

Define the product promise and V1 boundaries before implementation: what Job Hunter should find, how it should score fit, what personal profile/resume data it needs, and where human approval is required before any outward action.
