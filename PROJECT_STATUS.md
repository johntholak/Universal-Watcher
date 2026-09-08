# PROJECT_STATUS.md — Automated Job Hunter

**Status date:** September 8, 2026
**Stage:** Bootstrap framework complete; active product definition resumed in ChatGPT while Work execution is unavailable

## Current state

The product has been separated conceptually from Universal Watcher and given a standalone framework covering product vision, UX, source strategy, matching philosophy, contracts, and a minimal Python scaffold.

No live job provider is connected. No browser automation, scraping, application submission, or employer contact exists.

The primary V1 user experience is now locked as resume-first search:

`Drop resume -> choose practical filters -> Find My Best Jobs -> ranked shortlist`

Manual/specific search remains a secondary mode and still uses the resume-derived profile for fit evaluation.

The V1 scoring philosophy and initial scoring model are locked in `docs/JOB_SCORING_V1.md`.

The V1 resume intelligence/profile model is locked in `docs/JOB_RESUME_PROFILE_V1.md`. The resume is treated as structured, evidence-backed career history, not merely a keyword source. User corrections are first-class data and material profile changes create a new profile version.

The V1 source-coverage strategy is locked in `docs/JOB_SOURCE_COVERAGE_V1.md`. Coverage is treated as a first-class product problem: provider adapters are paired with a persistent source registry, dynamic board discovery, direct-source verification, and explicit search coverage reporting.

## Locked V1 direction

- Resume-first search is the primary entry point; users should not need to build a large candidate profile manually before searching.
- Resume parsing must preserve explicit facts, accomplishments, scope, chronology, and evidence provenance.
- Resume-derived facts distinguish explicit, strongly derived, tentative inference, and user-confirmed states.
- Direct, adjacent, and transferable role families are generated from responsibilities/capabilities, not title text alone.
- User-confirmed corrections override automated inference without rewriting the original resume evidence.
- Searches and watches record the resume/profile version used.
- Search first, application automation later.
- Supported/authorized ATS data only.
- Source coverage is as important as scoring quality; a system cannot rank a worthwhile job it never discovers.
- Use a persistent Source Registry for company -> ATS provider -> board/site identifiers and health/freshness state.
- Search known supported boards broadly and dynamically discover new supported boards/company career sources.
- Prefer direct ATS/company-source truth for active job details and freshness verification.
- Never translate a provider failure into `no jobs found`.
- Every search retains an auditable coverage report of providers/boards attempted, successes/failures, discovered boards, and raw posting counts.
- Search broadly, understand deeply, rank aggressively, and eliminate cautiously.
- Optimize first for recall of worthwhile opportunities, then precision.
- Normalize and deduplicate before ranking.
- Hard filters before fit scoring.
- Only objective, user-authorized constraints should eliminate jobs early.
- Unknown facts remain unknown rather than silently becoming pass/fail decisions.
- Fit must be explainable by dimension and distinguish direct, equivalent, transferable, gap, and unknown evidence.
- Career Fit and Practical Fit remain separately inspectable.
- Assessment Confidence reflects evidence completeness/quality rather than candidate quality.
- Transferable experience is a first-class evidence type and can receive substantial credit when the underlying responsibility/scope is genuinely comparable.
- Do not use a fixed top-N quota; return every job that clears the configured quality bar.
- Results should surface Excellent Match, Strong Match, Worth a Look, and Transferable/Interesting opportunities, with filtered-out jobs remaining inspectable.
- Numeric thresholds are guide rails, not unquestionable truth; major required gaps can cap a bucket and strong equivalent experience can outperform weak direct-title alignment.
- Searches can become watches for newly posted or materially changed qualifying roles.

See `docs/JOB_RESUME_SEARCH_V1.md` for the locked search experience, `docs/JOB_RESUME_PROFILE_V1.md` for resume intelligence, `docs/JOB_SCORING_V1.md` for scoring, and `docs/JOB_SOURCE_COVERAGE_V1.md` for source discovery/coverage.

## V1 scoring baseline

Career Fit default dimensions total 100 points:

- role/function alignment: 20
- responsibility overlap: 20
- seniority/scope: 15
- skills/experience evidence: 15
- leadership responsibility: 10
- scale/complexity: 10
- industry/domain relevance: 5
- education/certifications/preferred qualifications: 5

Practical Fit default dimensions total 100 points across known evidence:

- location/distance: 30
- work arrangement: 25
- compensation: 25
- employment type: 10
- travel/schedule expectations: 10

Initial recommendation guide rails:

- Excellent Match: normally Career Fit ~85+ with no hard blocker or major unsupported required qualification and sufficient evidence
- Strong Match: normally Career Fit ~75+ with no hard blocker and only manageable gaps
- Worth a Look: normally Career Fit ~62+ or a stronger career match with meaningful uncertainty/concerns
- Transferable/Interesting: credible equivalent/transferable evidence makes the role genuinely worthwhile even when title/function alignment is indirect

Unknowns reduce confidence, not qualification by default.

## Initial provider candidates

First providers to evaluate when development resumes:

1. Greenhouse public job-board data
2. Lever public postings
3. Ashby public postings
4. SmartRecruiters public postings after confirming current access/authentication behavior for the intended use

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
- `docs/JOB_RESUME_PROFILE_V1.md`
- `docs/JOB_SCORING_V1.md`
- `docs/JOB_SOURCE_COVERAGE_V1.md`

## Verification

The scaffold was created as a GitHub bootstrap while local/Work execution was unavailable. The four starter test cases were subsequently reproduced and run in the ChatGPT Python environment and all passed. This is a preliminary logic check only; rerun the tests from the actual dedicated repository checkout before claiming repository-level runtime acceptance.

Current official source checks confirm that Greenhouse exposes public unauthenticated Job Board GET endpoints, Lever exposes published company-site postings, and Ashby exposes a public job-board postings endpoint including optional compensation data. These are implementation inputs, not claims that adapters already exist.

## NEXT TASK WHEN RESUMED

1. Create a dedicated `Automated-Job-Hunter` repository from this bootstrap.
2. Run the scaffold tests from that repository and establish a clean baseline commit.
3. Fix only genuine scaffold issues revealed by those tests.
4. Implement resume parsing/profile extraction against offline PDF/DOCX fixtures.
5. Implement the Source Registry data model and health/freshness semantics.
6. Implement one Greenhouse adapter with offline fixtures before adding any second provider.
7. Normalize Greenhouse postings into the shared job model.
8. Verify hard filters, deduplication, provenance, resume evidence matching, source-coverage reporting, and the locked explainable scoring model against fixtures.
9. Build a human-labeled validation set and measure worthwhile-job recall before enabling aggressive hiding.
10. Add Lever, then Ashby, only after the Greenhouse path is stable.

## Product quality target

The key validation metric is recall of worthwhile opportunities:

> Of the jobs the user considers genuinely worth applying to, how many did Job Hunter successfully surface?

Provisional V1 target: surface at least 95% of jobs labeled `Definitely Apply` or `Probably Apply` in the human-reviewed validation set before relying on aggressive automatic narrowing.

False negatives on worthwhile jobs are considered more serious than showing an occasional extra `Worth a Look` result.
