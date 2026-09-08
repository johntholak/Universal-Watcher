# Automated Job Hunter V1 Implementation Checklist

## Purpose

This is the execution checklist for the first coding phase after the bootstrap is migrated into the dedicated `Automated-Job-Hunter` repository.

Do not begin by building the UI or adding multiple providers. Establish the resume -> profile -> Greenhouse -> normalize -> filter -> match path with offline tests first.

## Phase 0: repository baseline

- create/migrate dedicated `Automated-Job-Hunter` repository
- preserve authoritative docs
- run existing scaffold tests
- establish a clean baseline commit
- record Python/runtime version
- do not change behavior until baseline is green

Command currently documented:

```bash
python -m unittest discover -s tests -v
```

## Phase 1: model evolution foundation

Evolve models incrementally toward `JOB_DATA_MODEL_V1.md`.

First additions:

- ResumeDocument
- EvidenceReference
- RoleExperience
- CapabilityEvidence
- RoleFamilySuggestion
- ProfileVersion
- SearchPreferences
- SourceRegistryEntry
- ProviderPosting

Do not add every future model in one giant rewrite.

Tests should verify:

- unknown fields remain null/unset
- IDs/provenance survive transformations
- ProfileVersion is immutable/reproducible

## Phase 2: resume fixture harness

Create the fixture structure from `JOB_RESUME_FIXTURES_V1.md`.

Minimum first fixtures:

1. basic single-column PDF
2. basic DOCX
3. two-column resume
4. promotions at same company
5. ambiguous `Producer` title with program/operations evidence
6. metrics-in-bullets resume
7. sparse resume
8. malformed/partial extraction

Implement fixture helper utilities before parser logic so every parser change is easy to regression-test.

## Phase 3: resume extraction boundary

Implement separate PDF and DOCX extraction behind one interface.

Conceptual contract:

```text
extract_resume(document) -> ExtractedResumeDocument
```

Output must include:

- text/blocks
- source/page references where practical
- extraction status
- warnings/errors
- extractor/parser version

Critical rule: partial/failed extraction must be explicit.

Do not infer career meaning in the extraction layer.

## Phase 4: structured resume parser

Conceptual contract:

```text
parse_resume(extracted_document) -> ParsedResume
```

Implement/test:

- sections
- employers
- titles
- dates/current-role state
- role grouping
- bullets/responsibilities
- accomplishments
- education/certifications when explicit
- numeric scope signals

First definition of done:

- no fabricated employers/titles/dates on fixtures
- chronology materially correct
- bullets attached to correct role
- metrics retain meaning

## Phase 5: profile builder

Conceptual contract:

```text
build_profile(parsed_resume, user_overrides=None) -> ProfileVersion
```

Implement/test:

- explicit facts
- strongly derived capability evidence
- tentative inferences
- user-confirmed overrides
- seniority band/range
- direct role families
- adjacent role families
- transferable role families
- reasons/evidence refs for every role-family suggestion

Do not use a flat keyword list as the profile.

## Phase 6: Source Registry

Implement SourceRegistryEntry persistence/logic before live Greenhouse retrieval.

Minimum fields:

- company
- provider
- board token/provider identifier
- public board URL
- discovery/verification timestamps
- status
- last success/failure

Tests:

- transient failure does not permanently invalidate source
- invalid source is distinguishable from temporarily unavailable

## Phase 7: Greenhouse offline adapter parser

Use `JOB_GREENHOUSE_ADAPTER_V1.md`.

Implement fixture parsing first with no network dependency.

Conceptual contracts:

```text
parse_greenhouse_board(payload, source_entry, retrieved_at) -> ProviderFetchResult
parse_greenhouse_detail(payload, posting) -> ProviderPosting
```

Required first tests:

- normal board posting
- content=true description/departments/offices
- empty board
- null internal job ID
- multiple offices
- first_published vs updated_at
- missing first_published
- one pay range
- multiple pay ranges
- missing salary
- malformed payload

## Phase 8: Greenhouse HTTP boundary

Only after offline parsing tests are stable, add injectable HTTP transport.

Conceptual contract:

```text
GreenhouseAdapter.fetch_board(source_entry) -> ProviderFetchResult
GreenhouseAdapter.fetch_detail(source_entry, posting_id) -> ProviderPosting
```

HTTP tests should mock/inject:

- 200
- 404 invalid token
- 429
- timeout
- 5xx
- malformed JSON

Provider failure must never become a normal successful zero-job result.

## Phase 9: selective enrichment

Implement broad board sweep + permissive plausibility screening + selective detail fetch.

Do not detail-fetch every job automatically.

Regression tests must protect ambiguous potentially relevant titles such as:

- Producer
- Program Manager
- Operations Manager
- Field Marketing Manager
- Chief of Staff

Title alone is not enough to discard these.

## Phase 10: normalization + LogicalJob/dedupe

Add only the LogicalJob/dedupe fields required for one-provider search first.

Preserve:

- provider posting ID
- internal job ID
- requisition ID
- URL
- company/title/location
- source lineage

Do not build cross-provider heuristics before the one-provider path is stable.

## Phase 11: hard filter expansion

Extend existing hard-filter logic to support V1 SearchPreferences.

Implement deterministic tests for:

- freshness when published date known
- freshness unknown
- known salary below floor
- salary unknown
- distance/work arrangement explicit mismatch
- work arrangement unknown
- employment type
- blocked company
- explicit unsatisfied credential/license rule

Unknown is not fail by default.

## Phase 12: requirement extraction + matching

Use `JOB_MATCHING_FIXTURES_V1.md`.

Conceptual pipeline:

```text
extract_requirements(job) -> JobRequirement[]
match_evidence(requirements, profile) -> EvidenceMatch[]
assess_fit(job, profile, preferences) -> FitAssessment
```

Persist structured evidence states:

- direct
- equivalent
- transferable
- gap
- unknown

A language model may assist interpretation, but tests must operate on stored structured results and must not depend exclusively on opaque prose.

## Phase 13: scoring/buckets

Implement Career Fit, Practical Fit, and Confidence separately.

Use the guide rails in `JOB_SCORING_V1.md`, but do not hard-code them as unquestionable truth.

Regression tests:

- equivalent scope match can beat weak direct-title match
- credible transferable job can surface
- required blocker beats high numeric score
- missing preferred qualification does not behave like required gap
- sparse posting lowers confidence, not qualification automatically

## Phase 14: SearchRun + coverage report

Implement one-shot search record before watches.

Record:

- profile version
- preference snapshot
- source attempts
- provider failures
- counts by stage
- scoring model version
- result ordering

The system must be able to explain whether a short result list came from strong filtering or incomplete source coverage.

## Phase 15: held-out validation

Create a real/anonymized validation set independent from development fixtures.

Human labels:

- Definitely Apply
- Probably Apply
- Maybe
- No

Primary gate:

- >=95% recall on Definitely Apply + Probably Apply before enabling aggressive automatic hiding

Every meaningful false negative becomes a minimized regression fixture.

## Phase 16: controlled live Greenhouse smoke test

Only after offline tests are green:

- choose one verified public Greenhouse board
- fetch board
- normalize
- selectively enrich a few candidates
- run the one-shot pipeline
- inspect SourceCoverageReport
- compare direct Greenhouse URL/details with normalized result

Do not call this broad production coverage yet.

## Phase 17: UI

Build the V1 UI from `JOB_UI_V1.md` only after the backend contracts are stable enough to feed it.

Initial UI should support:

- resume upload/review
- freshness
- minimum salary
- distance/work arrangement
- employment type
- match style
- Find My Best Jobs
- compact search progress
- ranked job rows
- expand `Why this ranked here`
- filtered-out audit view

Do not let UI work block backend validation.

## Phase 18: watches

Only after one-shot search is trustworthy:

- save SearchPreferences + profile version
- repeat source/search pipeline
- detect new/materially changed LogicalJobs
- suppress duplicates
- notify only newly qualifying jobs

## Phase 19: second provider

Add Lever only after Greenhouse is stable.

Repeat the same discipline:

- fixtures
- normalization
- failure semantics
- provenance
- coverage reporting

Then Ashby.

## First coding-session target

A successful first implementation session does not need a live job result.

The best first milestone is:

1. dedicated repo exists
2. baseline tests pass
3. first ResumeDocument/ProfileVersion models exist
4. resume fixture harness exists
5. basic PDF + DOCX fixtures parse into correct role chronology

That is a stronger foundation than rushing to a live provider call.

## Core rule

Build the system in the same order the product earns trust:

`Resume truth -> Source truth -> Deterministic filters -> Explainable matching -> Validation -> UI -> Watches -> More sources`.