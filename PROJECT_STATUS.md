# PROJECT_STATUS.md — Automated Job Hunter

**Status date:** September 8, 2026
**Stage:** Bootstrap framework complete; active product definition and implementation preparation continuing in ChatGPT while Work execution is unavailable

## Current state

Automated Job Hunter is a standalone product, completely separate from Universal Watcher.

The project currently has a minimal Python scaffold plus a substantially expanded set of authoritative V1 product, matching, source, data-model, validation, UI, and implementation specifications.

No live provider adapter is implemented yet. No browser automation, scraping, automatic application submission, or employer contact exists.

The original scaffold starter tests were subsequently reproduced and run in the ChatGPT Python environment; all four starter cases passed. This remains a preliminary logic check only. Repository-level runtime acceptance must still be established after migration to the dedicated repository.

## Locked primary V1 experience

Primary flow:

`Drop resume -> choose practical filters -> Find My Best Jobs -> ranked shortlist`

The user should not need to build a large candidate profile manually before searching.

Manual/specific search remains a secondary mode and still uses the resume-derived profile for fit evaluation.

Primary visible controls:

- resume
- posting freshness
- minimum compensation
- location/distance
- work arrangement
- employment type
- match style

Advanced controls remain collapsed by default.

The current visual baseline is intentionally simple and provisional: clean/light layout, restrained purple/blue/green accents, one compact search bar/card, recommendation-style job rows, one primary visible job action, and deeper analysis revealed only when expanded. Pixel-level polish is intentionally deferred until the intelligence and search pipeline work reliably.

## Core product rules

- Search broadly, understand deeply, rank aggressively, and eliminate cautiously.
- Optimize first for recall of worthwhile opportunities, then precision.
- Missing a genuinely worthwhile job is a more serious failure than showing an occasional extra `Worth a Look` result.
- Do not use a fixed top-N result quota. Surface every job that clears the configured quality bar.
- Only objective, user-authorized constraints should hard-filter jobs early.
- Unknown facts remain unknown rather than silently becoming pass/fail decisions.
- Resume matching is evidence-based, not keyword matching.
- Direct, equivalent, and transferable experience are distinct first-class evidence types.
- Career Fit and Practical Fit remain separately inspectable.
- Assessment Confidence describes evidence quality/completeness, not candidate quality.
- Strong equivalent or transferable evidence can outrank weak direct-title alignment.
- Major unsupported required qualifications can cap or block a recommendation even when the numeric score is otherwise high.
- Results are recommendation-style: Excellent Match, Strong Match, Worth a Look, Transferable/Interesting, with Filtered Out remaining auditable.
- Every important decision must preserve provenance and enough evidence to explain why it happened.
- Search first; application automation is a later phase.
- Supported/authorized public source access only. Do not make bypassing anti-bot controls a dependency.

## Resume intelligence

The resume is treated as structured career evidence, not a keyword blob.

Locked behavior includes:

- PDF and DOCX intake
- chronology and role-history extraction
- explicit employer/title/date preservation
- accomplishments, scale, team, budget, technical, vendor, client, and leadership evidence
- direct / adjacent / transferable role-family generation
- explicit / strongly-derived / tentative-inference / user-confirmed evidence states
- user corrections as first-class overrides without rewriting original resume evidence
- versioned ProfileVersion records
- searches and watches pinned to the profile version used
- unsupported facts remain unknown

Implementation acceptance is defined in `docs/JOB_RESUME_FIXTURES_V1.md`, including difficult fixtures for two-column layouts, tables, promotions, sparse resumes, missing dates, ambiguous titles, and embedded metrics.

## Scoring baseline

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
- Worth a Look: normally Career Fit ~62+ or a stronger match with meaningful uncertainty/concerns
- Transferable/Interesting: credible equivalent/transferable evidence makes the role genuinely worthwhile even when title/function alignment is indirect

Thresholds are guide rails, not unquestionable truth.

Matching regression cases are defined in `docs/JOB_MATCHING_FIXTURES_V1.md` so title-only behavior, industry over-filtering, unknown handling, hard blockers, preferred-vs-required qualifications, and transferable-role recall can be tested permanently.

## Source strategy

Initial provider order:

1. Greenhouse
2. Lever
3. Ashby
4. SmartRecruiters after confirming intended endpoint/access behavior during implementation

LinkedIn and Indeed are not V1 dependencies.

Current official documentation checks confirm useful public company-scoped job data patterns for the initial ATS families. These are implementation inputs, not claims that adapters already exist.

## Locked Source Registry architecture

The Source Registry is a first-class product subsystem, not merely a list of URLs.

Important locked change: **do not fetch every registered board from scratch for every user search.**

Instead:

1. maintain durable CompanyIdentity records separate from ATS board identity
2. maintain verified SourceRegistryEntry records for provider boards/sites
3. continuously/adaptively refresh sources into a normalized local current-job corpus
4. execute searches primarily against that indexed corpus
5. selectively live-refresh high-value stale sources during a search
6. dynamically discover missing supported boards/companies
7. merge newly discovered/refreshed postings before final ranking

This is intended to make the product faster because it remembers the job market, not less complete because it searches fewer sources.

Source Registry rules include:

- one company may own multiple active sources
- companies may change provider, token, domain, brand, or regional board structure
- company identity and provider-source identity must not be collapsed
- prior provider/source history is retained when a company moves
- global/EU or other provider instances remain distinct
- guessed provider identifiers are never automatically trusted as company ownership
- official company careers-page evidence is preferred for ownership verification
- web/search results are discovery evidence, not final source truth
- valid zero-job boards are distinct from failed/unavailable boards
- transient errors never become `no jobs` or automatic source deletion
- failed refreshes must not silently close previously observed jobs
- source health, freshness, latency/failure type, schema/normalization failures, and anomalous posting-count changes are tracked
- board fetches are reused across role lanes/searches rather than repeated per title
- concurrent identical board refreshes should be deduplicated/coalesced where practical
- each search retains an auditable coverage/freshness report

Detailed behavior is locked in `docs/JOB_SOURCE_REGISTRY_V1.md` and regression scenarios in `docs/JOB_SOURCE_REGISTRY_FIXTURES_V1.md`.

## Seed employer universe

The day-one source universe is also a first-class part of V1.

The seed must be personalized from the resume/profile and preferences but must never become a hidden whitelist or career boundary.

Locked seed design:

- maintain a reusable global base of verified supported ATS boards
- derive a user-specific priority universe from direct, adjacent, and transferable role families plus geography/work-arrangement preferences
- use seed priority to control discovery and refresh effort, not whether a company/job is allowed to appear
- allow any legitimate newly discovered employer/source outside the seed to enter the registry and compete normally
- preserve why an employer was prioritized so seed behavior remains auditable

For the current bootstrap profile, the initial user-specific universe should intentionally over-cover:

- events and experiential leadership
- media, entertainment, streaming, sports, and live experiences
- technology companies with major event/field-marketing organizations
- event technology, AV, broadcast, production, and managed services
- hospitality, venues, convention, and destination organizations
- brand marketing and field activation organizations
- senior program/project/operations transfer opportunities
- selective Chief of Staff/business-operations adjacency where the function matches
- Southern California employers inside user-selected geography rules
- US-remote employers with relevant direct/adjacent/transferable roles

Provisional initial coverage goal: roughly **250 verified employers/sources** in the first useful seed, diversified across these lanes rather than concentrated in one industry, expanding toward **1,000+** through discovery as the product matures. These are coverage targets, not search limits or completeness claims.

The complete strategy is locked in `docs/JOB_SEED_UNIVERSE_V1.md`.

## Indexed corpus and freshness

Each successful source refresh should:

1. preserve raw provider observation/provenance
2. normalize provider postings
3. compare with the prior valid source snapshot
4. classify postings as new / changed / unchanged / disappeared
5. update provider-posting and LogicalJob lineage
6. update the current searchable corpus

Refresh priority is adaptive rather than one universal interval.

Relative source tiers:

- Hot: active watches, explicit company searches, recent highly relevant results
- Warm: active relevant boards with regular posting activity
- Cold: valid boards with low change/relevance
- Recovery: temporarily unavailable boards using provider-aware backoff

At search time, use the indexed corpus immediately, identify stale relevant sources, live-refresh the highest-value stale sources within a bounded budget, perform targeted discovery for named/missing companies, merge results, then complete ranking.

## Greenhouse implementation baseline

Greenhouse remains the first provider.

The locked adapter spec is in `docs/JOB_GREENHOUSE_ADAPTER_V1.md`.

Key design:

- broad board retrieval first
- normalize list payloads
- cheap relevance screening
- selective job-detail enrichment only when useful
- preserve first-published vs updated vs retrieved timestamps separately
- capture explicit pay-transparency ranges when available
- provider failures remain distinct from legitimate zero jobs
- offline fixtures are required before live-provider acceptance

## Search / watch behavior

The end-to-end search/watch pipeline is locked in `docs/JOB_SEARCH_WATCH_V1.md`.

Each SearchRun is an immutable snapshot tied to ProfileVersion, search preferences, search intent, source coverage/freshness, scoring-model version, and result order.

Watches repeat the same decision logic against new observations and prevent duplicate notifications. Existing watches remain pinned to the profile version used at creation unless deliberately changed.

Watches are not implemented until one-shot search behavior is reliable.

## V1 data model

The conceptual domain model is locked in `docs/JOB_DATA_MODEL_V1.md`.

Important separations include ResumeDocument vs ProfileVersion, resume facts vs user preferences, CompanyIdentity vs SourceRegistryEntry, ProviderPosting vs LogicalJob, JobObservation vs current job identity, JobRequirement vs EvidenceMatch, Career Fit vs Practical Fit vs Confidence, FilterDecision vs FitAssessment, SearchRun vs Watch, ApplicationRecord vs posting availability, and user feedback vs explicit search criteria.

The existing Python scaffold remains intentionally minimal and should evolve incrementally with tests, not via a giant rewrite.

## Validation target

Primary product metric:

> Of the jobs the user considers genuinely worth applying to, how many did Job Hunter successfully surface?

Provisional V1 target: surface at least **95%** of jobs labeled `Definitely Apply` or `Probably Apply` in a human-reviewed held-out validation set before relying on aggressive automatic narrowing.

Validation failures must be diagnosed by subsystem:

- source not discovered -> source coverage/registry regression
- source stale/unavailable mishandled -> refresh/health regression
- job discarded during cheap screening -> broad-retrieval regression
- job hard-filtered incorrectly -> hard-filter regression
- job scored/ranked incorrectly -> matching/scoring regression

Do not fix one subsystem's failure by weakening an unrelated subsystem.

## Authoritative framework/spec files

Core:

- `AGENTS.md`
- `PRODUCT_VISION.md`
- `PROJECT_STATUS.md`
- `RUNBOOK.md`
- `CHATGPT_PROJECT_SEED.md`

Bootstrap code:

- `job_hunter/models.py`
- `job_hunter/contracts.py`
- `job_hunter/pipeline.py`
- `tests/test_pipeline.py`

Product/spec docs:

- `docs/JOB_UX_BASELINE.md`
- `docs/JOB_DATA_SOURCE_BASELINE.md`
- `docs/JOB_MATCHING_BASELINE.md`
- `docs/JOB_RESUME_SEARCH_V1.md`
- `docs/JOB_RESUME_PROFILE_V1.md`
- `docs/JOB_SCORING_V1.md`
- `docs/JOB_SOURCE_COVERAGE_V1.md`
- `docs/JOB_SOURCE_REGISTRY_V1.md`
- `docs/JOB_SEED_UNIVERSE_V1.md`
- `docs/JOB_SEARCH_WATCH_V1.md`
- `docs/JOB_DATA_MODEL_V1.md`
- `docs/JOB_UI_V1.md`
- `docs/JOB_VALIDATION_V1.md`

Implementation/test specs:

- `docs/JOB_RESUME_FIXTURES_V1.md`
- `docs/JOB_MATCHING_FIXTURES_V1.md`
- `docs/JOB_GREENHOUSE_ADAPTER_V1.md`
- `docs/JOB_SOURCE_REGISTRY_FIXTURES_V1.md`
- `docs/JOB_IMPLEMENTATION_CHECKLIST_V1.md`

## Exact next implementation sequence when development execution resumes

1. Create the dedicated `Automated-Job-Hunter` repository from this bootstrap.
2. Run the existing scaffold tests from that repository and establish a clean baseline commit.
3. Fix only genuine scaffold issues revealed by those tests.
4. Evolve bootstrap models incrementally toward `JOB_DATA_MODEL_V1.md`, starting with provenance and CompanyIdentity/SourceRegistryEntry.
5. Implement provider source-identifier parsers and Source Registry state/health transitions against `JOB_SOURCE_REGISTRY_FIXTURES_V1.md`.
6. Implement resume text extraction/profile building against `JOB_RESUME_FIXTURES_V1.md`.
7. Implement the seed-universe generator/prioritizer from `JOB_SEED_UNIVERSE_V1.md` and create a small deterministic test seed.
8. Implement Greenhouse board verification and the Greenhouse adapter against offline fixtures.
9. Expand the verified bootstrap registry toward the provisional initial coverage target while preserving provider/source verification evidence.
10. Persist normalized provider snapshots into the current indexed corpus.
11. Implement hard filters and broad relevance screening.
12. Implement requirement/evidence matching and explainable scoring against `JOB_MATCHING_FIXTURES_V1.md`.
13. Implement SearchRun, coverage reporting, indexed-corpus query, and selective stale-source refresh.
14. Build a human-labeled held-out validation set and measure worthwhile-job recall.
15. Fix false negatives by the responsible subsystem until the recall target is met.
16. Build the V1 UI against stable backend contracts.
17. Implement watches only after one-shot search behavior is reliable.
18. Add Lever, then Ashby, repeating provider and registry fixture discipline.
19. Expand scheduled source discovery and registry health maintenance.

## Current resume point

The project is implementation-ready at the specification level.

When execution access returns, do **not** restart product design. Begin with repository migration, baseline tests, Source Registry/provenance models, resume fixtures, seed-universe generation, and the existing fixture-driven implementation checklist.
