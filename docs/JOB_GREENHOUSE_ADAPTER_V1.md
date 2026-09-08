# Greenhouse Adapter V1

## Purpose

This document defines the first live-source adapter implementation for Automated Job Hunter.

Greenhouse is the first provider because its Job Board GET endpoints are public and structured, making it suitable for a fixture-first implementation without browser automation or blocked-site scraping.

The adapter must preserve direct-source provenance and provider failure semantics. A Greenhouse error must never be translated into `no jobs found`.

## Provider identity

Provider name: `greenhouse`

Primary public API family:

```text
https://boards-api.greenhouse.io/v1/boards/{board_token}/...
```

Board token is stored in the Source Registry and is not inferred anew on every request when a verified registry entry already exists.

## V1 request strategy

Use a two-stage retrieval strategy.

### Stage 1: board sweep

Request:

```text
GET /v1/boards/{board_token}/jobs?content=true
```

Purpose:

- retrieve all currently published posts for the board
- get job-post IDs and internal job IDs
- title
- location text
- absolute URL
- update timestamp
- requisition ID when present
- full content/description
- departments
- offices
- exposed metadata

Do not make one detail request per board job immediately.

### Stage 2: selective detail enrichment

Only for jobs that survive inexpensive plausibility checks or need missing details for ranking/filtering, request:

```text
GET /v1/boards/{board_token}/jobs/{job_id}?pay_transparency=true
```

Purpose:

- obtain `first_published` when present
- preserve `updated_at` separately
- obtain pay transparency ranges when available
- obtain company name / detailed job representation when useful
- obtain application deadline when present

Do not request application questions in V1 search unless a later feature explicitly needs them.

## Why two stages

Board sweeps may contain hundreds or thousands of posts across companies in the registry.

Fetching details for every posting before any relevance screening would add unnecessary requests and latency.

Therefore:

`Board sweep -> Normalize -> Cheap plausibility -> Selective enrich -> Hard filters -> Deep match`

The cheap plausibility stage must remain recall-oriented. It may remove clearly irrelevant job families, but it must not behave like final scoring.

## Source Registry input

The adapter receives a verified SourceRegistryEntry containing at minimum:

- provider = greenhouse
- canonical company name
- board token
- public board URL when known
- last verified state

If the board token fails, the adapter reports source failure/health data to the registry layer rather than guessing another company identity internally.

## Normalized ProviderPosting mapping

### IDs

Greenhouse `id` -> `provider_posting_id`

Greenhouse `internal_job_id` -> `provider_job_id`

Greenhouse `requisition_id` -> `requisition_id`

Do not collapse `id` and `internal_job_id`; they have distinct provider semantics.

### Company

Preferred order:

1. detail response `company_name` when present
2. Source Registry canonical company name

Do not infer company from department/office names.

### Title

Greenhouse `title` -> `title`

Preserve exact provider title in provenance even if downstream canonical title normalization differs.

### Location

Greenhouse list/detail `location.name` -> `location_text`

Greenhouse `offices` may provide additional structured location context.

V1 should preserve:

- raw `location.name`
- office names/locations
- any parsed structured locations produced downstream

Do not infer Remote/Hybrid/Onsite solely from office presence.

### Work arrangement

Only populate when explicit evidence exists in provider title/location/content/metadata and the normalization rule can cite it.

Examples:

- explicit `Remote`
- explicit `Hybrid`
- explicit required onsite language

Otherwise keep unknown.

### Employment type

Populate only when explicitly available through content or exposed metadata with adequate confidence.

Otherwise unknown.

### Description

Greenhouse `content` -> raw description provenance.

Create a normalized text representation downstream for matching.

The provider may encode HTML entities; normalization should decode safely while preserving the original raw provider content separately.

Do not strip headings/bullets so aggressively that requirement structure is lost.

### Department/team

Greenhouse `departments` -> department provenance and normalized department names.

Team may remain unknown unless explicit metadata/content supports it.

### Published vs updated timestamps

Detail `first_published` -> `published_at`

`updated_at` -> `updated_at`

Never substitute `updated_at` for `published_at` without explicitly lowering freshness confidence and marking publication time unknown.

If Stage 1 is all that exists for a candidate and only `updated_at` is available:

- preserve updated time
- leave published time unknown
- do not claim the role was posted at the update timestamp

### Retrieval timestamp

Adapter request time -> `retrieved_at`

Use a timezone-aware timestamp.

### Job/apply URL

Greenhouse `absolute_url` -> provider job/apply destination.

Preserve the original URL.

Downstream canonicalization may normalize query parameters for dedupe, but provenance retains the original.

### Compensation

Detail `pay_input_ranges` is the preferred structured source when returned.

For each pay range preserve:

- min cents
- max cents
- currency
- title
- blurb/raw context

Normalize numeric amounts from cents to currency units.

Do not assume a period if Greenhouse does not provide one explicitly in structured data. A downstream compensation parser may infer period from explicit range title/blurb/job text only when evidence supports it, with provenance/confidence.

Multiple pay ranges may represent location tiers. Preserve all provider ranges rather than selecting one silently.

If compensation only appears in description text, it may be extracted downstream with source=`description`, not presented as structured Greenhouse pay data.

## Freshness handling

Freshness is critical because the UI supports Last 24 hours through Last 30 days.

Priority of evidence:

1. `first_published` from detail response
2. another explicit provider publication field if Greenhouse adds one later
3. unknown publication date

`updated_at` is not publication time.

For jobs where the user's freshness filter could determine eligibility and publication time is unknown after Stage 1, detail enrichment should be prioritized before hard-filtering on age.

If publication time remains unknown, the freshness FilterDecision should be `unknown`, not fail, unless the user chose a strict known-date rule.

## Reposts and material changes

V1 should not assume every `updated_at` change means a newly posted job.

Use provider-post identity + LogicalJob history + `first_published` + material-field hash to distinguish:

- same posting updated
- closed and later reposted under a new posting ID
- material change to compensation/location/title
- duplicate representation

A watch should not notify repeatedly on trivial provider update timestamps.

## Cheap plausibility screen

Before detail enrichment, the system may use title, department, description, role lanes, and broad location/work information to identify jobs requiring deeper evaluation.

The screen should be intentionally permissive.

Examples safe to remove early:

- clearly unrelated licensed clinical role when no relevant clinical lane exists
- clearly unrelated software engineering role when neither direct, adjacent, nor transferable lanes support it

Examples unsafe to remove solely by title:

- Producer
- Program Manager
- Operations Manager
- Field Marketing Manager
- Chief of Staff

Those may be highly relevant depending on responsibilities and resume evidence.

## HTTP behavior

### Success

2xx valid JSON with expected shape -> normalize.

### Board not found / invalid token

Report source-registry failure with response status/context.

Do not return an ordinary successful empty list.

### Rate limit / transient server failure

Report provider/source temporarily unavailable.

Do not mark board invalid after one transient failure.

### Timeout/network failure

Return/raise an adapter availability error carrying enough context for SourceCoverageReport.

### Valid board with zero jobs

This is distinct from provider failure.

Return successful board observation with zero current postings.

### Malformed JSON / unexpected schema

Treat as adapter/provider parsing failure, preserve redacted diagnostic context, and fail that source attempt explicitly.

Do not silently skip the whole board and call it zero jobs.

## Adapter result contract

The provider adapter should return more than a list.

Conceptually:

```text
ProviderFetchResult
- source_registry_entry_id
- provider
- started_at
- completed_at
- status: success / partial / failed
- postings
- raw_count
- warnings
- errors
- adapter_version
```

This lets SearchRun build an honest SourceCoverageReport.

## Offline fixture set

Recommended structure:

```text
fixtures/providers/greenhouse/
  board_basic.json
  board_content_html_entities.json
  board_empty.json
  board_missing_internal_job_id.json
  board_multiple_offices.json
  detail_basic.json
  detail_pay_transparency.json
  detail_multiple_pay_ranges.json
  detail_missing_first_published.json
  detail_application_deadline.json
  error_404.json
  error_429.json
  malformed.json
```

## Required normalization tests

### Basic board job

Assert:

- provider posting ID retained
- internal job ID retained separately
- requisition ID retained
- title/location/URL retained
- updated timestamp parsed timezone-aware
- retrieved timestamp populated

### Content=true job

Assert:

- content is available for matching
- departments/offices preserved
- encoded HTML can be normalized without changing provenance

### Prospect post / missing internal job ID

Assert:

- null internal ID does not crash normalization
- posting can still preserve provider-post identity

### Empty board

Assert:

- successful zero result
- source attempt marked successful
- not confused with error

### Multiple offices

Assert:

- all office evidence is retained
- location is not collapsed prematurely to one office

### Detail with first_published

Assert:

- `published_at` uses first_published
- `updated_at` remains separate

### Detail without first_published

Assert:

- publication remains unknown
- updated time does not substitute silently

### Single pay range

Assert:

- cents convert correctly
- currency retained
- raw title/blurb retained
- period remains unknown unless separately evidenced

### Multiple pay ranges

Assert:

- all ranges retained
- no arbitrary range becomes global salary
- location-tier context can be preserved

### Missing salary

Assert:

- compensation remains unknown
- minimum salary filter does not hard-fail merely due to missing data unless strict policy enabled

### Provider errors

Assert separately for 404, 429, timeout, malformed JSON:

- zero jobs is not returned as a normal success
- error context reaches source coverage/registry health layer
- one transient failure does not permanently invalidate the source

## Enrichment selection tests

Create a synthetic board containing:

- 100 obviously unrelated jobs
- 15 broad plausible jobs
- 5 clear direct-fit titles

Expected behavior:

- not all 120 receive detail calls
- plausible and direct-fit jobs remain eligible for detail enrichment
- ambiguous-but-transferable titles are not discarded solely by title

The exact enrichment count is not a product contract; recall of worthwhile candidates is.

## Dedupe-support requirements

ProviderPosting must preserve enough identifiers for downstream dedupe:

- board/source registry entry
- provider posting ID
- internal job ID
- requisition ID
- exact company
- exact title
- locations
- absolute URL

Same `internal_job_id` with multiple post IDs may be related but must not be merged blindly without confirming provider semantics/location differences.

Cross-provider dedupe happens outside this adapter.

## Provenance requirements

For every normalized field, the system should be able to identify whether it came from:

- board list response
- detail response
- Source Registry
- downstream extraction from description

Raw fixture/provider payloads should be stored by reference in production and directly available in tests.

## Privacy and non-goals

V1 Greenhouse search does not submit applications.

Do not request or process applicant demographic/compliance questions for job discovery.

Do not use Greenhouse application POST endpoints in this phase.

## Acceptance gates

Do not call the Greenhouse adapter stable until:

1. all required offline fixtures pass
2. provider failures are distinguishable from empty boards
3. publication time and update time are not conflated
4. missing salary/location/work arrangement remain unknown
5. all pay ranges are preserved accurately
6. source provenance survives normalization
7. selective enrichment does not create obvious recall failures in fixture tests
8. SourceCoverageReport can explain whether a board succeeded, failed, or returned zero posts
9. one real public Greenhouse board smoke test succeeds after offline tests are stable
10. no second provider is added before these behaviors are reliable

## Implementation order

After migration to the dedicated repository:

1. create fixture loader/test helpers
2. implement Greenhouse payload parser against fixtures only
3. implement ProviderFetchResult/error types
4. add HTTP client boundary with injectable transport
5. add board sweep
6. add selective detail enrichment
7. wire Source Registry health reporting
8. run a controlled live board smoke test
9. connect normalized postings to LogicalJob/dedupe/search pipeline

## Core rule

The adapter's job is to retrieve Greenhouse truth faithfully.

It should not make opaque career-fit decisions, invent missing facts, or hide provider failures. Matching belongs downstream.