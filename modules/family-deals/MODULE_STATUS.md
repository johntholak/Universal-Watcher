# Family Deals Module Status

**Current state (October 9, 2026):** V5.0.1 is preserved as the discovery and verification engine. Full-radius discovery, existing filters, and strict price-to-meal evidence rules remain required.

The shared Universal Watcher web interface now includes the Family Deals search form. The private API/browser integration supports one-time searches, progressive candidate results, and live coverage snapshots. The implementation and its offline CI checks are green on main.

**Production is not yet verified.** The dedicated deployment workflow is manual. Do not call the feature live until the D1 migrations, private-beta session, dispatch secrets, homepage/session smoke tests, and one controlled live-adapter acceptance run have all passed. The deployment template has no recurring Cron trigger.

## Source of truth

- V5 discovery and verifier: `server.py` and `index.html`
- Shared web interface: `../../web/index.html`, `../../web/app.js`, `../../web/styles.css`
- API and progressive job execution: `../../cloud/worker.mjs`, `../../cloud/run_family_deals_batch.py`, `../../cloud/family_deals_v5.py`
- Deployment gate and required secrets: `../../cloud/README.md`
- API contract: `../../docs/API_V1_CONTRACT.md`

## Locked product requirements

- No arbitrary top-N cap on restaurant discovery.
- Budget uses exact total price in cents. A deal at the budget qualifies; a deal one cent above does not.
- Family size is 4 through 10. Serving capacity must cover the selected party.
- Deal name, meal, total price, serving capacity, restaurant/location applicability, and dinner hours when requested must be supported by evidence.
- Unknown evidence stays unknown. Partial coverage must never become a false `NO_MATCH`.
- Search runs only when the user starts a Search. No recurring Cron schedule is configured.
