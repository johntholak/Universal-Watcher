# Universal Watcher production architecture

**Decision date:** September 25, 2026. This is the approved V1 target, not a deployed system.

## Cost and ownership

Additional infrastructure cost must remain **$0**. Use Cloudflare's free site hosting, Worker API, Cron and D1, plus standard GitHub Actions runners for Python/browser execution. Use a free Cloudflare URL. If free capacity runs short, slow checks; if exhausted, mark work `DELAYED` with reason `free_capacity` until reset. Never upgrade, incur overages, buy a domain, or require a paid service. Stop and ask before any setup that requires payment information. Validate current service terms and quotas before deployment.

Cloudflare/D1 owns job and Watch state. Cron checks due work around every 15 minutes and dispatches GitHub Actions only when needed; GitHub scheduled workflows are not the authoritative clock. Search creates a queued job and immediately dispatches a workflow. The browser talks only to `/api/v1`, never to providers, engines or GitHub. The user's Mac is not part of normal production operation.

```text
Browser → Cloudflare site / Worker API → D1 jobs and Watches
                                      ↓
                          Cron / immediate dispatch
                                      ↓
                           GitHub Actions worker
                                      ↓
                    module adapter → preserved engine → provider
                                      ↓
                      normalized result/evidence → API → D1
```

The worker securely claims bounded batches, groups compatible work for safe source reuse, renews leases where necessary, and submits idempotent results. Expired leases can be reclaimed. Store versioned criteria and `user_id` on user-owned records; index user/status/due/provider/time queries. Proposed tables are users, searches, watches, jobs, watch_runs, results, result_evidence, provider_status and notifications. Store compact diagnostics and evidence, not entire seat maps or restaurant pages. Watch history records meaningful transitions, not each identical no-match poll.

Adapters validate criteria, run the preserved engine and normalize output. Family Deals V5 is the first end-to-end cloud gate; Movies V44.7 follows after authorized catalog and reliable seat inventory acceptance. Tickets remains shelved. Shared outcomes are `MATCH`, `NO_MATCH`, `PARTIAL`, `UNAVAILABLE`, `ERROR`. A block or failed inventory is never a no-match. Central provider states are `HEALTHY`, `DEGRADED`, `RATE_LIMITED`, `BLOCKED`, `UNAVAILABLE`; circuit breakers prevent repeated provider failures and allow a controlled recovery probe. Fingerprints deduplicate notifications and meaningful changes. A Watch preserves the exact search criteria and can remain active after a match.

Private beta can use a high-entropy access secret and signed secure session cookie, with no secret in frontend code. GitHub credentials, provider keys and worker authentication secrets belong in managed secrets, not JavaScript, D1, screenshots, documentation or logs. Browser dispatch payloads should contain only a minimal work-available signal; workers retrieve criteria through authenticated internal endpoints. In-app notifications are the initial channel. Email and browser push are optional only after a genuinely free route is verified.

## AMC credential boundary

Old-key recovery is **closed**. A new AMC catalog/vendor key was obtained September 25, 2026 and is **not validated**. Development location: ignored `modules/seat-watcher/.env`; production location: GitHub Actions secret `AMC_VENDOR_KEY`. When live verification is appropriate, make one controlled catalog authentication request, record success only, and stop to diagnose on 401, 403 or 429. Catalog access does not establish seating/ecommerce authorization. Do not retry blocked browser scraping, proxy or stealth routes.

## Plugins and connectors

Check connected and available plugins for a concrete development, research, validation or operations task. GitHub is valuable for repository history and Actions; Gmail/Drive can support correspondence or references. Ticket plugins remain for later Tickets research. Resend or Firecrawl require a specific justified need and free-tier verification. A ChatGPT plugin is a development/research capability, **not** automatically a production API. Never make production depend implicitly on a ChatGPT-only connection or create a competing app in an alternative builder.
