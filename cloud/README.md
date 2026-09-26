# Cloud API boundary

`migrations/0001_initial.sql` defines the first D1 schema. It is an offline,
unapplied contract, not a deployed API. `docs/API_V1_CONTRACT.md` defines the
request and response shapes that the Cloudflare Worker and GitHub worker will
implement next. No credential or database ID is stored here.

The schema retains exact versioned criteria in compact JSON, separates one-time
searches from recurring Watches, leases jobs, records meaningful Watch events,
and deduplicates notifications. Queries must always scope user-owned records by
`user_id`. The Worker must verify a signed private-beta session before accepting
browser calls and a separate worker secret before internal claim/result calls.

Run the offline migration test from the repository root:

```text
python -m unittest discover -s cloud -p "test_*.py" -v
```

Do not run a remote D1 migration or deploy until the private beta auth, zero-cost
account setup, quota behavior, and request handlers are reviewable together.
