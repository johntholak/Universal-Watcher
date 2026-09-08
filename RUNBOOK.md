# RUNBOOK.md — Automated Job Hunter

## Current status

This is a bootstrap scaffold only. No live provider calls are implemented yet.

## Intended environment

- Python 3.12+
- Standard library only for the initial scaffold

## When moved to its own repository

1. Clone the dedicated repository.
2. Read `AGENTS.md`, `PRODUCT_VISION.md`, `PROJECT_STATUS.md`, and this file.
3. Run tests:

```bash
python -m unittest discover -s tests -v
```

4. Add provider-specific credentials only through ignored local environment files if a future provider requires them.
5. Keep offline fixtures for parsing/provider tests.

## Current package

- `job_hunter.models`: normalized domain models
- `job_hunter.contracts`: adapter/scoring protocols
- `job_hunter.pipeline`: provider-agnostic dedupe/filter helpers

## Provider implementation order

Implement one adapter at a time. First target: Greenhouse public job-board data. Add fixtures, normalization tests, pagination/error handling, and provenance before moving to a second provider.

## Safety / correctness checks

- Never print credentials.
- Never convert provider failure into “no jobs found.”
- Preserve source URL and retrieval timestamp.
- Keep unknown compensation/location/requirements explicit.
- Do not submit applications or contact employers without a separately approved feature phase.

## Resume point

When development resumes, first move this bootstrap into a dedicated `Automated-Job-Hunter` repository, run the included tests, and establish a clean baseline commit before live-provider work.
