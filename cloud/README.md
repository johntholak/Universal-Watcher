# Cloud API boundary

`migrations/0001_initial.sql` defines the first D1 schema; apply
`0002_dispatch_gate.sql` after it for the one-row dispatch reservation gate,
then `0003_watch_jobs.sql` for Watch coverage and one-active-job enforcement,
then `0004_watch_criteria_versions.sql` for criterion-version history.
`worker.mjs` has a
private-beta session route, a Family Deals one-time Search queue/retrieval
slice, separately authenticated bounded job claims and lease heartbeat, chunked
result intake, live coverage progress, finalization, and paginated result reads. Result chunks are at
most five records each to keep an invocation bounded; there is no overall
result limit. Stable IDs and payload digests make duplicate delivery safe.
This is offline code until the dedicated API deployment workflow is run. The browser UI and API share one origin through the Worker static-assets binding. A user Search signals one fixed GitHub workflow run, which claims one job and exits. There is no recurring Cron trigger. Dispatch is bounded by a one-minute cooldown and daily run limit. `wrangler.example.toml` remains a deployment template with a D1 placeholder. No restaurant source is contacted by the API itself. `docs/API_V1_CONTRACT.md` defines the route shapes.
No credential or database ID is stored here.

The schema retains exact versioned criteria in compact JSON, separates one-time
searches from recurring Watches, leases jobs, records meaningful Watch events,
and deduplicates notifications. Queries must always scope user-owned records by
`user_id`. The Worker must verify a signed private-beta session before accepting
browser calls and a separate worker secret before internal claim/result calls.

Family Deals Watches can be saved only from a completed Search; they copy its
exact stored criteria and use a conservative fixed 24-hour check cadence. The
API supports list/detail/history, Check Now, pause/resume/keep watching and
soft-stop. An edit must reference a new completed Search owned by the user;
it is rejected while that Watch has a pending/running job. The Watch copies
the new exact criteria, increments its version and retains previous versions
for interpreting older runs. A partial unique index and due-time key prevent duplicate active Watch jobs. Watch scheduling is dormant while the Worker has no Cron trigger, in keeping with the on-demand-only deployment. Results and coverage are scoped to the owner. Repeated identical
outcomes do not add redundant history; a changed outcome, candidate set or
coverage does. Notifications are not connected yet.

`family_deals_v5.py` drives the preserved V5 page through full-radius discovery,
filtering, and the Python verifier. `run_family_deals_batch.py` claims one Family
Deals job at a time, renews its lease, uploads results in chunks of five, and
handles up to ten jobs per invocation. Its GitHub Actions workflow is manual
only. It requires repository secrets `UW_API_BASE` (the HTTPS Worker origin) and
`UW_WORKER_SECRET` (the same long secret configured on the Worker). No criteria or
credentials are passed in the workflow dispatch. The adapter conservatively
marks V5 candidates partial until an explicit deal name and applicability to
the particular restaurant location can be proved. Zero results become
`NO_MATCH` only after complete restaurant coverage.

Execution exceptions use the authenticated `/failure` route. The Worker backs
off a retry by 30 minutes per attempt and stops after three claims. Expired
third leases are finalized by Cron, including a Watch history event and a
paused Watch; provider failures are `UNAVAILABLE` without automatic retry.
No exception text or source payload is sent to the failure route. These are
offline-tested policies, not a live provider acceptance claim.
Evidence-backed result chunks and checked/unavailable/unresolved coverage snapshots are readable to the owning user while a job is
`CLAIMED` or `RUNNING`, so a connected client can show candidates and honest progress before the full
radius check finishes. Search status reports `RUNNING` during execution. These
early candidates must remain visibly provisional until final outcome and coverage
are known. Failure reports or expired-lease reclamation clear a job's old chunks
before another attempt.

Dispatch is enabled only when `DISPATCH_ENABLED=true`, a Cloudflare secret
`GITHUB_DISPATCH_TOKEN` with permission to dispatch this repository's workflow,
and an integer `DISPATCH_DAILY_LIMIT` (1–100) are configured. Set that limit
only after calculating a conservative allowance from the account's free Actions
balance and the 120-minute workflow timeout. The D1 gate reserves one run
before contacting GitHub and retains ambiguous failures as reservations.
When the daily allowance is exhausted, the one-time Search is failed with an
explicit capacity error rather than left queued. The current deployment has no
Cron trigger. Dispatch carries only `{ "ref": "main" }`; the runner claims criteria
from D1 through the authenticated API. The dispatch limit is local to this
Worker and cannot see other repositories' use of the same account's Actions balance.

Run the offline migration test from the repository root:

```text
python -m unittest discover -s cloud -p "test_*.py" -v
node --test cloud/test_*.mjs
```

Do not run a remote D1 migration or deploy until live adapter acceptance and the private beta
auth, zero-cost account setup and quota behavior are reviewable together. The
site and API must share an origin for the strict cookie and CSRF checks.


## On-demand production deployment

Run the manual GitHub Actions workflow **Deploy Universal Watcher Family Deals API**
only after these repository Actions secrets exist:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `UW_D1_DATABASE_NAME`
- `UW_D1_DATABASE_ID`
- `UW_ACCESS_SECRET` (at least 32 characters)
- `UW_SESSION_KEY` (at least 32 characters)
- `UW_WORKER_SECRET` (at least 32 characters)
- `UW_API_BASE` (the HTTPS API Worker origin used by the batch runner)
- `UW_GITHUB_DISPATCH_TOKEN` (a GitHub token scoped to this repository with Actions: read/write permission)

The workflow applies D1 migrations, deploys the app and API from the same Worker origin,
sets private session and dispatch secrets, then smoke-tests the homepage and session.
The Worker has no Cron trigger. Each browser Search signals the fixed batch workflow,
which claims one job and exits. Failed dispatch is recorded as a failed Search instead
of leaving a hidden queued job behind.
