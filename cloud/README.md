# Cloud API boundary

`migrations/0001_initial.sql` defines the first D1 schema. `worker.mjs` has a
private-beta session route, a Family Deals one-time Search queue/retrieval
slice, separately authenticated bounded job claims and lease heartbeat, chunked
result intake, finalization, and paginated result reads. Result chunks are at
most five records each to keep an invocation bounded; there is no overall
result limit. Stable IDs and payload digests make duplicate delivery safe.
This is offline code, not a deployed or complete API. Search responses
explicitly say `dispatch: not_connected`; no restaurant source is contacted by
the API. `docs/API_V1_CONTRACT.md` defines the remaining route shapes.
No credential or database ID is stored here.

The schema retains exact versioned criteria in compact JSON, separates one-time
searches from recurring Watches, leases jobs, records meaningful Watch events,
and deduplicates notifications. Queries must always scope user-owned records by
`user_id`. The Worker must verify a signed private-beta session before accepting
browser calls and a separate worker secret before internal claim/result calls.

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

Run the offline migration test from the repository root:

```text
python -m unittest discover -s cloud -p "test_*.py" -v
node --test cloud/test_*.mjs
```

Do not run a remote D1 migration or deploy until dispatch, Cron, Watch endpoints,
free-capacity handling and live adapter acceptance are completed and the private beta
auth, zero-cost account setup and quota behavior are reviewable together. The
site and API must share an origin for the strict cookie and CSRF checks.
