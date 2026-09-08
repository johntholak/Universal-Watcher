# Job Source Registry Fixtures V1

## Purpose

This fixture suite defines the minimum offline cases needed to prove that Source Registry logic preserves coverage, provenance, and source health correctly before live discovery is trusted.

These are registry/discovery tests, not provider-posting parser tests.

## Fixture structure

Each fixture should include, as applicable:

- company identity input
- official company domain/careers-page evidence
- discovered provider URL(s)
- suspected provider and identifier
- provider verification response/status
- prior registry state
- expected registry transition
- expected ownership confidence
- expected discovery/health events
- explicit assertions for what must **not** happen

Use local HTML/JSON fixtures and simulated HTTP status results. Tests must not depend on live provider availability.

## Core fixtures

### SR-01 — Greenhouse direct official link

Scenario:

- official company careers page contains a direct link to `boards.greenhouse.io/<token>`
- Greenhouse board metadata returns matching organization name
- jobs endpoint responds successfully

Expected:

- candidate is promoted to `verified_active` or `verified_empty` based on posting count
- CompanyIdentity and SourceRegistryEntry are linked
- discovery evidence includes official career page + Greenhouse verification
- board token is stored exactly

Must not:

- infer another board from a guessed company-name slug

### SR-02 — Greenhouse API-driven custom careers page

Scenario:

- official company careers page is hosted on the company's own domain
- public page/job URLs expose Greenhouse identifiers or configuration linking to a Greenhouse board token
- Greenhouse board metadata/jobs endpoint validates

Expected:

- source is recognized as Greenhouse despite non-Greenhouse careers UI
- official company domain is preserved separately from ATS board identity

### SR-03 — Lever global site

Scenario:

- official careers page links to `jobs.lever.co/<site>`
- global Lever postings endpoint responds successfully

Expected:

- provider=`lever`
- instance=`global`
- site identifier preserved
- source verified

### SR-04 — Lever EU site

Scenario:

- official careers page links to the EU Lever hosted site

Expected:

- provider instance stored as EU
- EU and global site identities do not collide

### SR-05 — Ashby official link

Scenario:

- official careers page links to `jobs.ashbyhq.com/<board-name>`
- public Ashby board API succeeds

Expected:

- board-name parsed and stored exactly
- source verified

### SR-06 — SmartRecruiters company identifier

Scenario:

- official careers link resolves to a SmartRecruiters default career site
- company identifier is parsed from the career-site path
- posting endpoint behavior is represented by fixture

Expected:

- source identity stored without assuming broader private API access
- adapter access capability is recorded explicitly

## Ownership-confidence fixtures

### SR-10 — Valid endpoint, wrong company

Scenario:

- guessed Greenhouse/Lever identifier resolves to a real board
- returned organization clearly belongs to another company
- no official-domain evidence links target company to board

Expected:

- do not verify ownership
- candidate marked invalid/mismatched or retained as unrelated discovery

Must not:

- attach the board to target CompanyIdentity because the token looked similar

### SR-11 — Matching display name only

Scenario:

- provider board name resembles target company
- no official link/domain evidence exists

Expected:

- candidate remains `candidate`
- ownership confidence low/moderate at most

### SR-12 — Official redirect is strong evidence

Scenario:

- official company careers URL redirects to exact supported ATS board

Expected:

- strong ownership evidence
- verified after provider source validation

### SR-13 — Multiple aliases / rebrand

Scenario:

- company has prior name/domain and current name/domain
- same current ATS board is linked from new official domain

Expected:

- one CompanyIdentity with aliases when evidence supports continuity
- source not duplicated merely due to display-name change

## State-transition fixtures

### SR-20 — Valid board with zero jobs

Prior:

- verified active board

Current fetch:

- successful valid provider response with zero active jobs

Expected:

- `verified_empty`
- last successful fetch updated
- source remains valid

Must not:

- mark unavailable
- delete registry entry

### SR-21 — First-time valid empty board

Scenario:

- source verifies successfully but currently has zero jobs

Expected:

- source may become `verified_empty`
- no requirement that a source contain a current posting to be legitimate

### SR-22 — HTTP 429 / rate limit

Prior:

- verified source

Current fetch:

- simulated 429

Expected:

- `temporarily_unavailable` or provider-specific backoff state
- prior jobs are not interpreted as closed solely due to failed refresh
- retry/backoff metadata recorded

### SR-23 — HTTP 5xx/transient network failure

Expected:

- temporary failure state
- source preserved
- cached corpus retains prior observation with stale/freshness marker

### SR-24 — 404 after previously valid source

Expected:

- do not immediately delete
- transition to revalidation/move investigation path
- official careers page rediscovery may locate new source

### SR-25 — invalid source on first verification

Scenario:

- discovered URL/identifier returns definitive invalid/not-found result and no contrary evidence

Expected:

- `invalid`
- no active coverage credit

## Provider-move fixtures

### SR-30 — Greenhouse to Ashby migration

Prior:

- verified Greenhouse board

New official careers evidence:

- company now links to Ashby board
- Greenhouse board no longer valid/current

Expected:

- create new Ashby SourceRegistryEntry
- retain historical Greenhouse source
- mark old source `moved` or inactive with evidence
- CompanyIdentity remains stable

### SR-31 — Token/site rename within same provider

Scenario:

- official company page changes from old board identifier to new one

Expected:

- preserve old source record
- create/verify new source identity
- do not overwrite historical provider identifier

### SR-32 — Multiple active regional boards

Scenario:

- company operates US and EU boards simultaneously

Expected:

- both active sources linked to same CompanyIdentity
- search scope can consume both without treating one as a migration

## Duplicate-source fixtures

### SR-40 — Same board discovered via three paths

Discovery paths:

- official careers page
- web search result
- individual job result

Expected:

- one SourceRegistryEntry
- evidence list enriched
- no duplicate fetch targets

### SR-41 — Equivalent URL variants

Scenario:

- trailing slash, query params, job-detail URL, and root board URL all reveal same provider identifier

Expected:

- normalize to one registry identity

### SR-42 — Separate boards with similar names

Scenario:

- two distinct provider identifiers belong to different companies with similar display names

Expected:

- remain separate
- no name-only merging

## Indexed-corpus fixtures

### SR-50 — New posting appears

Prior board snapshot:

- jobs A, B

Current snapshot:

- A, B, C

Expected:

- C marked new
- A/B unchanged unless material fields differ
- current corpus updated

### SR-51 — Posting disappears after successful refresh

Prior:

- A, B

Current successful valid snapshot:

- A only

Expected:

- B marked disappeared/possibly closed according to provider semantics
- disappearance tied to successful valid source observation

### SR-52 — Failed refresh must not close jobs

Prior:

- A, B

Current:

- provider failure, no valid snapshot

Expected:

- A/B not marked closed merely because response is unavailable

### SR-53 — Material update

Current posting retains identity but changes:

- compensation
- location/work arrangement
- title or substantive description

Expected:

- material change version increments when configured field/hash rules say change is material
- watches can detect update without treating it as a wholly new logical job unless dedupe identity changed

### SR-54 — Non-material update

Change:

- insignificant formatting/whitespace/provider metadata

Expected:

- no material-change alert/version bump

## Search-time freshness fixtures

### SR-60 — Fresh cache, no live fetch required

Scenario:

- source snapshot meets configured freshness target

Expected:

- search uses indexed data
- no duplicate remote refresh

### SR-61 — High-value stale board

Scenario:

- board relevant to search/watch is stale
- search-time refresh budget available

Expected:

- same-run live refresh attempted
- refreshed data merged before final ranking when successful

### SR-62 — Low-value stale board outside refresh budget

Expected:

- indexed data can still be used with explicit freshness state if policy permits
- coverage report notes stale source
- no false claim of fresh exhaustive coverage

### SR-63 — Explicitly requested company not in registry

Expected:

- targeted company discovery runs before returning no qualifying jobs for that company

## Concurrency/request-dedupe fixtures

### SR-70 — Two searches request same stale board

Expected:

- provider fetch is coalesced/deduplicated where implementation supports it
- both search runs receive same completed source snapshot

### SR-71 — Search + watch request same board

Expected:

- no unnecessary duplicate identical board requests
- independent SearchRun/Watch provenance still records source use

## Health anomaly fixtures

### SR-80 — Sudden 500 jobs to zero

Scenario:

- historically large valid board suddenly returns syntactically successful empty/near-empty result

Expected:

- configurable anomaly flag/revalidation path
- do not automatically assume every prior posting closed without confidence checks

### SR-81 — Schema/parsing regression

Scenario:

- HTTP success but required expected fields/schema cannot be parsed

Expected:

- parsing/normalization failure distinct from zero jobs
- prior corpus not wiped

### SR-82 — Board recovers after failure

Expected:

- return to verified active/empty based on valid response
- failure counters/backoff reset appropriately

## Coverage-regression fixtures

### SR-90 — User manually finds missed job from unknown board

Expected workflow:

1. record missed job/source
2. discover/verify provider board
3. add SourceRegistryEntry
4. add source-discovery regression fixture
5. confirm future equivalent search can see the board/job family

### SR-91 — Miss caused by stale registry

Expected:

- classify failure as freshness/refresh issue, not matching issue
- regression test targets scheduler/search-time refresh behavior

### SR-92 — Miss caused by incorrect ownership rejection

Expected:

- capture discovery evidence and fix confidence/verification logic
- do not compensate by weakening unrelated match scoring

## Minimum test assertions

Every source registry test should verify, where applicable:

- resulting source status
- company/source linkage
- provider identity and instance
- ownership confidence/evidence
- last successful fetch semantics
- posting-count semantics
- failure classification
- whether current indexed jobs should be retained/closed/updated
- coverage-report contribution

## Core regression rule

When Job Hunter misses a worthwhile job because it never saw the source, fix the **coverage system** and add a permanent source-registry regression test.

Do not try to solve a source-coverage miss by changing fit-scoring thresholds.
