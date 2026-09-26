# Cloud API boundary

`migrations/0001_initial.sql` defines the first D1 schema. `worker.mjs` has a
private-beta session route and a Family Deals one-time Search queue/retrieval
slice. This is offline code, not a deployed or complete API. Search responses
explicitly say `dispatch: not_connected`; no GitHub worker or restaurant source
is contacted. `docs/API_V1_CONTRACT.md` defines the remaining route shapes.
No credential or database ID is stored here.

The schema retains exact versioned criteria in compact JSON, separates one-time
searches from recurring Watches, leases jobs, records meaningful Watch events,
and deduplicates notifications. Queries must always scope user-owned records by
`user_id`. The Worker must verify a signed private-beta session before accepting
browser calls and a separate worker secret before internal claim/result calls.

Run the offline migration test from the repository root:

```text
python -m unittest discover -s cloud -p "test_*.py" -v
node --test cloud/test_*.mjs
```

Do not run a remote D1 migration or deploy until dispatch, worker claims,
idempotent results, Cron and Watch endpoints are completed and the private beta
auth, zero-cost account setup and quota behavior are reviewable together. The
site and API must share an origin for the strict cookie and CSRF checks.
