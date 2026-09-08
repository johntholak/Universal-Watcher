# Universal Watcher Pause Checkpoint

Date: September 8, 2026
Status: Intentionally paused / shelved until more development time is available

## Locked scope at pause

User-facing product direction:

- Movies
- Family Deals
- Drops

Tickets remains shelved/hidden. Automated Job Hunter has been moved out as a standalone product. Event Producer Copilot remains a separate later concept. Restaurant PDF Menu Builder remains outside Universal Watcher.

## What was completed before pause

- Authoritative master repository and portability rules exist.
- Movies, Family Deals, Home, Watch, Drops product/UX, and visual baselines are documented.
- Approved visual reference is preserved in the repository.
- Tickets remains preserved but hidden.
- Drops has product, UX, and data-source architecture baselines, but no live integration yet.
- Universal Watcher web implementation is still incomplete and should continue to follow the approved dark layered visual target rather than the old generic preview shell.
- Existing Movies and Family Deals engines should be preserved rather than rewritten.

## Resume order

When Universal Watcher resumes:

1. On the Mac, complete the pending Movies V44.7 acceptance check using the Odyssey / IMAX 70MM / CityWalk case and Burbank ordinary-seat case.
2. Verify final seat decoder/full-map agreement and accessible-seat exclusion.
3. Continue the approved Universal Watcher web implementation: Home -> Movies -> Family Deals -> Watches.
4. Integrate proven Movies and Family Deals engines through adapters only after acceptance.
5. Continue Drops from its documented product, UX, and source baselines.

## Guardrails

- Do not reactivate Tickets without a new explicit decision and a legitimate reliable data path.
- Do not re-add Automated Job Hunter as a Universal Watcher module.
- Do not restore arbitrary Family Deals restaurant caps.
- Do not casually rewrite the AMC engine.
- Treat the approved visual references as implementation targets, not loose inspiration.

This file is the explicit pause/resume checkpoint. The more detailed technical state remains in `PROJECT_STATUS.md`, and setup/run instructions remain in `RUNBOOK.md`.
