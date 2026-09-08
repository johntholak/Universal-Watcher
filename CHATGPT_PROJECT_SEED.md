# Automated Job Hunter — ChatGPT Project Seed

Use this file to start a clean ChatGPT Project/chat dedicated only to Automated Job Hunter.

## Project identity

Automated Job Hunter is a standalone product. It is not a Universal Watcher module.

Universal Watcher may have inspired some reusable architecture patterns, but the products should remain separate in UX, roadmap, repository, and project context.

## Product promise

Find jobs that are genuinely worth applying to, remove noise and duplicates, explain why each role fits or does not fit, keep watching for better opportunities, and give the user a clean decision queue instead of another high-volume job board.

## Original concept carried forward

The Job Hunter idea was to use the user's resume/background as the basis for searching across many company career pages and job sources, remove duplicate postings, identify legitimate-fit roles, score them, explain strengths and weaknesses, filter by practical constraints such as location/remote and compensation, and alert only when opportunities clear a worthwhile threshold.

The system should specialize in evaluating:

- experience and skills
- explicit job requirements
- compensation when known
- location and work arrangement
- seniority and scope
- industry/domain
- weaknesses or missing requirements
- likely practical hiring fit, without pretending certainty

## Locked V1 workflow

1. Build a candidate/search profile.
2. Discover jobs from supported public or authorized sources.
3. Normalize postings into one internal model.
4. Deduplicate the same role found through multiple sources.
5. Apply hard eligibility filters before any fit score.
6. Score remaining roles with visible, decomposable reasoning.
7. Sort results into Strong Fit, Maybe, and Skip.
8. Let the user save searches as watches for newly posted qualifying roles.
9. Provide basic application-status tracking.

## Candidate/search profile

V1 should support:

- target titles and role families
- seniority range
- location and commute radius
- remote / hybrid / onsite preferences
- employment type
- minimum compensation when known
- industries and company types
- required skills
- preferred skills
- travel tolerance
- must-have criteria
- exclusion criteria

The product should be usable before a perfectly structured resume/profile exists. Resume history can enrich matching later.

## Matching philosophy

A fit score is an explanation aid, not an oracle.

Hard disqualifiers must be handled before weighted scoring.

Useful scoring dimensions include:

- role/title match
- seniority and scope
- experience and skills
- industry/domain relevance
- location/work arrangement
- compensation
- explicit requirements
- practical concerns or weaknesses

Unknown information stays unknown. It should never silently become a pass or fail.

The product should optimize for worthwhile applications, not application volume.

## Result experience

Each result should make it easy to answer:

- What is the job?
- Why is it a fit?
- What could be a problem?
- What important information is missing?
- How fresh is the posting?
- Where did it come from?
- What should I do next?

Primary triage states:

- Strong Fit
- Maybe
- Skip

## Monitoring

A saved search becomes a watch.

The system can later alert when a newly posted role clears the user's configured criteria/fit threshold so the user does not repeatedly search the same sources manually.

## V1 source strategy

First provider families to evaluate:

1. Greenhouse public job-board data
2. Lever public postings
3. Ashby public job postings
4. SmartRecruiters public postings

LinkedIn and Indeed are not V1 dependencies.

Do not build V1 around scraping blocked sites, bypassing access controls, or assuming partner-only APIs will become available.

## Architecture direction

Reuse the conceptual pipeline where useful:

Discover -> Normalize -> Filter -> Verify -> Rank -> Monitor -> Alert

Expected structure over time:

- source/provider adapters
- normalized job model
- deduplication layer
- hard-filter layer
- fit-scoring/explanation layer
- review queue
- watch/monitoring layer
- application tracker

The system should preserve source provenance and freshness so users can see how defensible each result is.

## V1 boundaries

Do not make V1 an auto-application bot.

Do not:

- auto-submit applications
- scrape blocked sources as a core dependency
- bypass anti-bot/access controls
- invent salary, work arrangement, requirements, or other missing facts
- optimize for the largest number of applications

Possible later phases, only after discovery/matching is excellent:

- resume tailoring
- cover-letter generation
- application assistance
- recruiter/outreach assistance
- interview preparation
- more advanced application workflow automation

## User job-search context to preserve

The user's background is strongest in events, experiences, technical production, event technology, operations, project/program management, vendor management, budgets, cross-functional execution, and team leadership.

Representative target-role directions discussed previously include:

- Director of Events
- Event Manager
- Event Operations Director
- VP Event Operations
- Site Manager / Managed Technology
- Head of Brand Innovation / experiential leadership roles
- Chief of Staff to senior marketing leadership where the scope fits
- Partner Events roles
- Program / Project Manager roles where event, operations, technology, or field execution experience transfers well

The user is based in West Hills, California and has considered both local and remote opportunities.

Career-history details worth preserving for future fit scoring include experience with large event budgets, full event lifecycle ownership, AV/technical production, hotel event technology operations, vendor/RFP/contracts, travel/logistics, staffing, cross-functional leadership, direct management, and prior business ownership/leadership.

Writing preferences for future application materials:

- human, warm, professional tone
- concise/punchy
- one-page cover letters when practical
- no em dashes
- resume wording prefers “ran the company” when describing prior ownership/leadership

## Existing bootstrap state

Current staging location:

- GitHub repo: `johntholak/Universal-Watcher`
- branch: `job-hunter-bootstrap`

This branch is only a temporary staging home. Job Hunter should become its own dedicated repository when active development resumes.

Existing framework includes:

- `AGENTS.md`
- `PRODUCT_VISION.md`
- `PROJECT_STATUS.md`
- `RUNBOOK.md`
- `docs/JOB_UX_BASELINE.md`
- `docs/JOB_DATA_SOURCE_BASELINE.md`
- `docs/JOB_MATCHING_BASELINE.md`
- `job_hunter/models.py`
- `job_hunter/contracts.py`
- `job_hunter/pipeline.py`
- `tests/test_pipeline.py`
- `CHATGPT_PROJECT_SETUP.md`

Important commits:

- bootstrap framework: `d5aec29e08181ec013a85fc841b55ea71e2b6df2`
- ChatGPT project setup file: `315ed8af96923febb9603d7dc7073dc59e4baf16`

Starter tests exist but were not run at the time of the bootstrap because normal local/Work execution was unavailable. Do not claim runtime acceptance until they are executed.

## Exact next task when resumed

1. Create a dedicated `Automated-Job-Hunter` repository from the bootstrap.
2. Run the scaffold tests.
3. Fix only genuine scaffold issues found by tests.
4. Implement one Greenhouse adapter using offline fixtures first.
5. Normalize its postings into the shared job model.
6. Verify hard filters, deduplication, and explainable scoring against fixtures.
7. Add a second provider only after the Greenhouse path is stable.

## Project operating rule

This ChatGPT Project should contain Job Hunter work only.

Do not pull Universal Watcher implementation tasks into this project. The only Universal Watcher context that matters here is the historical fact that Job Hunter was deliberately separated into a standalone product.

When important Job Hunter decisions become locked, preserve them in the Job Hunter repository/docs so a future machine or chat can resume without relying on conversation memory alone.
