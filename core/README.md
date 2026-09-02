# Universal Watcher Core

This directory contains the first small shared contract layer for the future
Universal Watcher control plane. It is intentionally independent of the
existing module engines and does not start a server or a worker.

## Current contract preview

`contracts.py` defines:

- `WatchDefinition` — a module-neutral user request and lifecycle status.
- `Evidence` — concise, source-linked proof that can be shown to a user.
- `WatchResult` — a normalized outcome with separate `match`, `no_match`,
  `unavailable`, and `error` states.
- `WatchAdapter` — the narrow `run_once` bridge that adapters can implement
  without giving up module-specific discovery, browser, API, or worker logic.

The explicit `unavailable` outcome is important: a source that could not be
checked must never be represented as an empty result.

Verify the contract tests from the repository root:

```text
python -m unittest discover -s core -p "test_*.py" -v
```

Do not connect the shell to these contracts until the Movies API deployment
and Mac acceptance regression are complete.

Likely future concerns:

- Watch definition and lifecycle
- Common result/evidence models
- Source/provider adapter interfaces
- Scheduling and monitoring
- Persistence/history
- Notifications
- User/device identity
- Worker execution
- Server-vs-local-helper dispatch
- Observability and coverage metrics
