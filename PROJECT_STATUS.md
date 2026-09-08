# PROJECT_STATUS.md — Automated Job Hunter

**Status date:** September 8, 2026
**Stage:** Bootstrap framework complete, intentionally shelved

## Current state

The product has been separated conceptually from Universal Watcher and given a standalone framework covering product vision, UX, source strategy, matching philosophy, contracts, and a minimal Python scaffold.

No live job provider is connected. No browser automation, scraping, application submission, or employer contact exists.

## Locked V1 direction

- Search first, application automation later.
- Supported/authorized ATS data only.
- Normalize and deduplicate before ranking.
- Hard filters before fit scoring.
- Fit must be explainable by dimension.
- Unknown facts remain unknown.
- Results are triaged into Strong Fit, Maybe, and Skip.
- Searches can later become watches for newly posted qualifying roles.

## Initial provider candidates

First providers to evaluate when development resumes:

1. Greenhouse public job-board data
2. Lever public postings
3. Ashby public job postings
4. SmartRecruiters public postings

LinkedIn/Indeed are not V1 dependencies.

## Framework files

- `job_hunter/models.py`
- `job_hunter/contracts.py`
- `job_hunter/pipeline.py`
- `tests/test_pipeline.py`
- `docs/JOB_UX_BASELINE.md`
- `docs/JOB_DATA_SOURCE_BASELINE.md`
- `docs/JOB_MATCHING_BASELINE.md`

## Verification

Scaffold was created as a GitHub bootstrap while local/Work execution was unavailable. Tests are included but have **not been run in this checkpoint**. Do not claim runtime acceptance until they are executed in a normal development environment.

## NEXT TASK WHEN RESUMED

Create a dedicated `Automated-Job-Hunter` repository from this bootstrap, run the scaffold tests, then implement one Greenhouse adapter with offline fixtures before adding any second provider.
