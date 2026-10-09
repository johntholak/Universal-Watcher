# Universal Watcher `/api/v1` contract

**Status:** Offline D1 migration and partial Worker API. Session creation,
Family Deals Search creation/lookup, guarded dispatch, Watch creation/list/detail,
Check Now and lifecycle, internal bounded claims and lease heartbeat, chunked
result intake, Search/Watch finalization and paginated result reads exist in
`cloud/worker.mjs`, but no route is deployed or wired to the browser. Dispatch
is disabled by default; notifications remain planned. The current
`/api/*` endpoints in `web/server.py` are local, in-memory previews.

## Public requests

All public routes require a signed, secure private-beta session cookie. Every
read and write is scoped to the authenticated `user_id`; clients never supply
an authoritative user ID. JSON objects containing criteria have
`schema_version: 1`. Unknown schema versions and invalid module criteria fail
validation. Prices are decimal totals at the API boundary and should be stored
as integer cents in verified result details to avoid floating-point threshold
errors. Timestamps are UTC ISO 8601 strings.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/searches` | Validate module/criteria, atomically create Search plus queued Job, signal immediate dispatch. Return `202` with Search ID and `QUEUED` state. Dispatch failure leaves retriable queued work. |
| GET | `/api/v1/searches/:id` | Return state, coverage, last outcome, and active job status. Reports `RUNNING` once claimed, before finalization. |
| POST | `/api/v1/watches` | Save the exact criteria from a completed Search (`search_id`), including module and schema version. Set `ACTIVE` and schedule next check after 24 hours. |
| GET | `/api/v1/watches` | List user Watches with last and next check, coverage, provider state and match state. |
| GET | `/api/v1/watches/:id` | Watch, current results and meaningful history. |
| PATCH | `/api/v1/watches/:id` | Pause, resume, stop, keep watching, or `edit_from_search` with a new completed owned `search_id`. Edits preserve previous criteria versions and refuse pending/running Watch jobs. |
| POST | `/api/v1/watches/:id/check` | Queue an immediate check with per-Watch deduplication and capacity guard. |
| DELETE | `/api/v1/watches/:id` | Stop/soft-delete user-facing Watch without erasing its result audit trail. |
| GET | `/api/v1/results` | Cursor-paginated results filtered by Search/Watch. Evidence-backed Search candidates are readable during `CLAIMED`/`RUNNING` and remain provisional until final coverage is known. |
| GET | `/api/v1/results/:id` | One result and its compact evidence, including candidates from an active Search. |
| GET | `/api/v1/system/status` | Safe public health/capacity status, no secrets or internal diagnostics. |

The first implementation should accept Family Deals criteria from the approved
form: `location` (address/ZIP or coordinate string), positive `radius_miles`,
`party_size` integer 4–10, `max_total_price` positive decimal,
`cuisines` array, `restaurant_type` from `any`, `independent_local`,
`independent`, `chains`, and boolean `open_tonight`. Empty cuisines means any.
Do not put a top-N cap on restaurant discovery. Movies criteria can be
validated in the later Movies adapter milestone.

## Search response and result state

```json
{"id":"search-id","module":"family-deals","status":"QUEUED","created_at":"UTC timestamp"}
```

Every completed execution has `outcome` from `MATCH`, `NO_MATCH`, `PARTIAL`,
`UNAVAILABLE`, `ERROR`, a summary, coverage counts and provider state.
`NO_MATCH` requires sufficient successful coverage. A blocked source, failed
seat inventory, or partial scan never becomes a complete negative result.

Family Deals result cards require deal name, restaurant/location, cuisine,
classification, distance, verified total cents, serving capacity, included
food, verification (`VERIFIED`, `PARTIALLY_VERIFIED`, `UNABLE_TO_VERIFY`),
source URL, direct deal URL if established, and last verified timestamp.
Missing fields remain explicitly unknown. `UNABLE_TO_VERIFY` belongs in
coverage reporting rather than an equal-ranked deal list. Source evidence is
compact and records the exact claim it supports, never a full page.

## Internal worker routes

Internal routes use a separate worker authentication secret, never a browser
cookie. They accept no browser CORS origin, limit batch size and response size,
and log no credentials or private criteria.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/internal/jobs/claim` | Atomically claim a bounded due batch; return criteria, `claim_id`, attempt number, lease expiry. Reclaim expired leases. |
| POST | `/api/v1/internal/jobs/:id/heartbeat` | Extend only the matching active claim. |
| POST | `/api/v1/internal/jobs/:id/results` | Accept one to five compact normalized results/evidence for a matching active claim per chunk; repeat chunks safely with stable IDs and payload digests. No overall match cap. |
| POST | `/api/v1/internal/jobs/:id/complete` | Idempotently finalize Search or Watch with outcome/coverage. Incomplete coverage cannot become `NO_MATCH`; Watch history records meaningful changes only. |
| POST | `/api/v1/internal/jobs/:id/failure` | Record `execution` versus `provider` failure. Execution gets bounded backoff (three claims); provider failure stays unavailable. Circuit state remains future work. |

Cloudflare Cron is the authoritative scheduler. It queues due Watches and
dispatches GitHub Actions with only a `work available` signal. The GitHub
worker claims a bounded batch one job at a time. No criteria or secrets go in
the workflow dispatch payload. Free capacity exhaustion delays work until
reset; no paid fallback is permitted.

## Auth and implementation gate

This contract alone grants no access. Implement signed session issuance,
CSRF protection for cookie-authenticated mutations, worker secret comparison,
input limits, and user-scoped SQL before exposing any route. Add tests for
cross-user access, stale claims, duplicate result submission, and free-capacity
delays before deployment. Keep GitHub token, private access secret, session
signing key, and worker secret in managed secrets only.
