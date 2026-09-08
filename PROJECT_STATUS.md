# PROJECT_STATUS.md — Automated Job Hunter

**Status date:** September 8, 2026
**Stage:** Bootstrap framework complete; active product definition resumed in ChatGPT while Work execution is unavailable

## Current state

The product has been separated conceptually from Universal Watcher and given a standalone framework covering product vision, UX, source strategy, matching philosophy, contracts, and a minimal Python scaffold.

No live job provider is connected. No browser automation, scraping, application submission, or employer contact exists.

The primary V1 user experience is now locked as resume-first search:

`Drop resume -> choose practical filters -> Find My Best Jobs -> ranked shortlist`

Manual/specific search remains a secondary mode and still uses the resume-derived profile for fit evaluation.

## Locked V1 direction

- Resume-first search is the primary entry point; users should not need to build a large candidate profile manually before searching.
- Search first, application automation later.
- Supported/authorized ATS data only.
- Search broadly, understand deeply, rank aggressively, and eliminate cautiously.
- Optimize first for recall of worthwhile opportunities, then precision.
- Normalize and deduplicate before ranking.
- Hard filters before fit scoring.
- Only objective, user-authorized constraints should eliminate jobs early.
- Unknown facts remain unknown rather than silently becoming pass/fail decisions.
- Fit must be explainable by dimension and distinguish direct, equivalent, transferable, gap, and unknown evidence.
- Career fit and practical fit should remain separately inspectable.
- Assessment confidence should reflect evidence completeness/quality.
- Do not use a fixed top-N quota; return every job that clears the configured quality bar.
- Results should surface Excellent Match, Strong Match, Worth a Look, and Transferable/Interesting opportunities, with filtered-out jobs remaining inspectable.
- Searches can become watches for newly posted or materially changed qualifying roles.

See `docs/JOB_RESUME_SEARCH_V1.md` for the detailed locked V1 search experience and ranking philosophy.

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
- `docs/JOB_RESUME_SEARCH_V1.md`

## Verification

The scaffold was created as a GitHub bootstrap while local/Work execution was unavailable. The four starter test cases were subsequently reproduced and run in the ChatGPT Python environment and all passed. This is a preliminary logic check only; rerun the tests from the actual dedicated repository checkout before claiming repository-level runtime acceptance.

## NEXT TASK WHEN RESUMED

1. Create a dedicated `Automated-Job-Hunter` repository from this bootstrap.
2. Run the scaffold tests from that repository and establish a clean baseline commit.
3. Fix only genuine scaffold issues revealed by those tests.
4. Implement one Greenhouse adapter with offline fixtures before adding any second provider.
5. Normalize Greenhouse postings into the shared job model.
6. Verify hard filters, deduplication, provenance, and explainable scoring against fixtures.
7. Add a second provider only after the Greenhouse path is stable.

## Product quality target

The key validation metric is recall of worthwhile opportunities:

> Of the jobs the user considers genuinely worth applying to, how many did Job Hunter successfully surface?

The system should earn the right to narrow aggressively only after this recall is consistently high.
