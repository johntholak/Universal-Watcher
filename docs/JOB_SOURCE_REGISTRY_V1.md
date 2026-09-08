# Job Source Registry V1

## Purpose

The Source Registry is the coverage engine behind Automated Job Hunter.

A strong matcher cannot recommend a worthwhile job it never discovers. V1 therefore needs more than provider adapters: it needs a persistent, auditable system that discovers company career sources, verifies them, refreshes them, tracks provider moves/failures, and maintains a searchable local corpus of current jobs.

The registry must optimize for both breadth and speed.

## Locked architecture decision

Do **not** fetch every known company board from scratch every time the user clicks `Find My Best Jobs`.

Instead:

1. maintain a persistent registry of known company career sources
2. refresh registered sources on an adaptive schedule
3. normalize current public postings into a local searchable corpus
4. execute user searches primarily against that indexed corpus
5. selectively live-refresh stale/high-value boards during a search
6. run targeted discovery for companies/boards not yet in the registry
7. merge newly discovered postings into the same corpus and search run

This architecture allows broad coverage without making every user search wait on thousands of remote requests.

## Separate concepts

### CompanyIdentity

Represents the employer as a durable entity independent of its ATS.

Suggested fields:

- `id`
- `canonical_name`
- `known_name_aliases`
- `primary_domain`
- `known_career_domains`
- `country/region context when needed for disambiguation`
- `created_at`
- `last_verified_at`

A company may have zero, one, or multiple active source entries.

### SourceRegistryEntry

Represents one public career/job-board source for one company.

Suggested fields:

- `id`
- `company_id`
- `provider`
- `provider_instance/region`
- `provider_identifier`
- `public_board_url`
- `api_endpoint_reference`
- `board_display_name`
- `source_scope` such as global / region / business unit when known
- `discovery_method`
- `discovery_evidence`
- `ownership_confidence`
- `first_discovered_at`
- `last_verified_at`
- `last_fetch_attempt_at`
- `last_successful_fetch_at`
- `last_nonempty_fetch_at`
- `last_failure_type`
- `consecutive_failure_count`
- `current_posting_count`
- `status`
- `adapter_version`

Registry identity should be based primarily on provider + provider instance + provider identifier, not company display name alone.

## Source states

Use explicit states rather than one active boolean.

Recommended states:

- `candidate` — discovered but ownership/validity not sufficiently verified
- `verified_active` — valid public source with active postings or recently valid public source
- `verified_empty` — valid public source currently returning zero active postings
- `temporarily_unavailable` — transient provider/network/rate-limit failure
- `access_restricted` — source exists but current access method is not available/authorized
- `moved` — company appears to have changed provider/board identifier
- `inactive` — previously valid source no longer appears to publish jobs
- `invalid` — discovery candidate proven not to be a legitimate board/source

A zero-job response is **not** the same as unavailable or invalid.

One transient failure must never delete or permanently disable a valid source.

## Provider identity patterns

Provider-specific discovery should use explicit parsers.

### Greenhouse

Current public hosted-board pattern uses a board token. Greenhouse documents the hosted board root as `boards.greenhouse.io`, with the final URL segment serving as the customizable board token.

Public GET Job Board API endpoints require no authentication. Useful verification endpoints include:

- retrieve board metadata by board token
- list board jobs

The board metadata endpoint returns the organization/board name, which is useful verification evidence.

Store:

- provider = `greenhouse`
- provider identifier = board token
- hosted board URL when present
- public API board endpoint

Do not assume all Greenhouse customers expose their careers UI directly on the Greenhouse hostname; API-driven/non-Greenhouse-hosted career pages also exist. The board token remains the useful API identity.

### Lever

Lever public postings are namespaced by a site identifier.

Hosted-site patterns include global and EU instances, e.g. jobs hosted under a site name. The official Postings API documents one site per company in the normal model and exposes public published jobs for that site.

Store:

- provider = `lever`
- provider instance = global / EU
- provider identifier = site name
- hosted job-site URL
- postings API endpoint

Do not collapse global and EU instances into the same registry identity.

### Ashby

Ashby's public job-board API uses the organization's hosted jobs-page name as `JOB_BOARD_NAME`.

The hosted board path's final segment is the board name used by the public API.

Store:

- provider = `ashby`
- provider identifier = job board name
- hosted board URL
- public posting API endpoint

### SmartRecruiters

SmartRecruiters public posting endpoints are company-scoped by a company identifier that appears at the end of the default career-site URL.

Store:

- provider = `smartrecruiters`
- provider identifier = company identifier
- career-site URL
- posting endpoint
- access/auth capability observed by the adapter

Because provider access/product behavior can evolve, the adapter must verify current public-access behavior rather than assuming one historical rule for all endpoints.

## Discovery sources

Use multiple discovery channels. No single discovery mechanism is sufficient.

### 1. Seed registry

Begin with a curated bootstrap set of companies likely to contain useful roles.

Seed categories should include:

- companies explicitly targeted by the user
- companies previously producing relevant applications/interviews
- major employers in the user's geography
- major remote-friendly employers
- companies likely to employ the resume-derived direct/adjacent/transferable role families
- companies discovered during historical job-search work

The seed is only a bootstrap. It must not become the permanent search universe.

### 2. Official careers-page detection

Given a company/domain:

1. find the official careers/jobs page
2. follow normal public links/redirects
3. inspect public URLs and page markup for supported ATS patterns
4. extract candidate provider identifiers
5. validate the direct ATS/API source
6. store ownership evidence linking the company domain to the provider board

Relevant public evidence can include:

- direct career-page link to a hosted ATS board
- iframe/embed source
- public script/config reference containing the board/site identifier
- company-hosted job links carrying ATS job identifiers
- redirects from official career pages to the ATS board

Do not bypass access controls or rely on stealth browser behavior.

### 3. Public web discovery

Use ordinary public web search/index results to discover:

- ATS-hosted board URLs
- individual ATS job URLs
- official career pages
- company + role results that reveal an unregistered provider board

A web result is discovery evidence, not final source truth. Validate against the direct ATS/company source before promoting a registry entry to verified status.

### 4. Result-driven expansion

When any search finds a legitimate posting from an unregistered board:

1. parse provider + identifier
2. validate source availability
3. validate company ownership with available evidence
4. add/update CompanyIdentity
5. add the SourceRegistryEntry
6. fetch the complete current public board
7. normalize its jobs
8. make those jobs available to the current/future search corpus

Every legitimate result can therefore expand future coverage.

### 5. Targeted company expansion

When a user explicitly names a company not represented in the registry:

1. resolve the company's official domain
2. perform careers-page/ATS discovery
3. verify any supported source
4. search it before concluding that no qualifying jobs were found

## Ownership verification

A valid provider endpoint alone does not prove that the board belongs to the company we think it does.

Keep a confidence score/state based on evidence such as:

### Strong ownership evidence

- official company careers page directly links/redirects to the provider board
- provider board metadata names the same company and the official domain links to it
- company-hosted job page embeds/references the exact provider identifier

### Moderate evidence

- provider board branding/name strongly matches company and multiple current job postings reference the company
- public search results repeatedly connect the company domain and exact provider board

### Weak evidence

- guessed token/site name happens to resolve
- display name similarity only

Weak evidence can create a `candidate` entry but should not silently become verified source coverage.

## Alias and provider-move handling

Companies may:

- rebrand
- merge/acquire
- change domains
- change ATS provider
- change board token/site identifier
- operate multiple regional/business-unit boards

Therefore:

- never use display name as the only company key
- preserve prior source entries and history
- mark old entries `moved` or `inactive` rather than overwriting them
- allow multiple simultaneously active sources for one CompanyIdentity
- store aliases and domains separately from board identifiers

If an official career page starts pointing to a different supported ATS, create/verify the new source and retain the old source history.

## Indexed corpus

The Source Registry feeds a persistent current-job corpus.

For every successful source refresh:

1. store raw provider observation/provenance
2. normalize provider postings
3. compare against prior source snapshot
4. mark new / changed / unchanged / disappeared postings
5. update LogicalJob/deduplication lineage
6. update current searchable index

The user search should query this corpus rather than remote ATS endpoints one by one.

## Freshness and adaptive refresh

Not every source requires the same refresh frequency.

Refresh priority should consider:

- whether an enabled watch depends on the board
- whether the board has recently produced relevant jobs
- historical posting/change frequency
- time since last successful fetch
- whether the user explicitly requested that company
- source health/failure history
- provider rate-limit/capacity constraints

Suggested relative tiers rather than hard universal intervals:

### Hot

Boards tied to active watches, recent highly relevant results, or explicit company searches.

Refresh most frequently within provider-safe limits.

### Warm

Active boards that regularly publish jobs and are relevant to one or more candidate role lanes.

Refresh routinely.

### Cold

Valid boards that rarely change or have low current relevance.

Refresh less frequently while still periodically checking for changes.

### Recovery

Temporarily unavailable boards use backoff and retry without being interpreted as empty.

Exact intervals should be configurable and calibrated against provider behavior rather than hard-coded into product semantics.

## Search-time freshness policy

At search start:

1. query the indexed corpus immediately
2. identify relevant source entries whose cached snapshot is older than the search freshness target
3. live-refresh the highest-value stale boards within a bounded search-time refresh budget
4. perform targeted discovery for missing named companies or obvious source gaps
5. merge refreshed/new observations
6. complete ranking against the updated corpus

This gives the user fast initial progress without sacrificing fresh data for the most important sources.

A search run must record which results came from already-fresh indexed data versus same-run refresh/discovery.

## Board-fetch efficiency

Fetch a board once per refresh cycle, not once per title/role lane.

One normalized board snapshot can be evaluated against many generated search lanes and many searches.

Use provider-aware request deduplication so concurrent searches/watches do not trigger duplicate identical board fetches.

## Source health

Track health metrics such as:

- success rate
- consecutive failures
- latency
- last HTTP/provider error category
- last valid schema version
- last posting count
- unexpected large posting-count changes
- parsing/normalization error count

A sudden change from hundreds of jobs to zero should be treated as potentially suspicious until the response/source state is validated.

## Discovery queue

Dynamic source discovery should create queue items rather than directly trusting every candidate.

Suggested fields:

- candidate company/domain
- suspected provider
- suspected provider identifier
- discovery origin
- evidence URLs/references
- discovered_at
- verification status
- verification attempts
- confidence

Verification promotes a candidate into the Source Registry.

## Coverage metrics

Track coverage at two levels.

### Registry coverage

- verified companies
- verified boards by provider
- active/empty/unavailable/moved counts
- boards added recently
- boards successfully refreshed within target freshness

### Search-run coverage

- registry boards considered relevant
- indexed snapshots used
- stale boards identified
- same-run refreshes attempted/succeeded/failed
- new boards discovered
- raw postings available
- source failures

Never show a raw board count to imply internet-wide completeness.

## Seed growth strategy

The registry should grow in controlled phases.

### Phase A — deterministic bootstrap

Create a meaningful seed set spanning the user's direct, adjacent, transferable, local, and remote employer universe.

Goal: immediate usefulness and deterministic testing.

### Phase B — search-driven growth

Every real search adds verified boards discovered from public career/search evidence.

### Phase C — scheduled discovery sweeps

Periodically look for new supported boards/companies across role families, locations, industries, and known ATS hosts.

### Phase D — coverage gap targeting

Use validation misses to identify source gaps. If the user finds a worthwhile job manually that Job Hunter missed because the company/board was absent, that becomes both:

- a new registry entry/discovery improvement
- a source-coverage regression fixture

## What not to do

Do not:

- brute-force random board tokens/site names as the main discovery strategy
- treat guessed identifiers as verified ownership
- delete sources after transient errors
- fetch the same board separately for every role query
- make every user search wait on a full-universe remote sweep
- rely on LinkedIn/Indeed scraping as the registry backbone
- convert provider outages into `no jobs`
- imply exhaustive internet coverage

## Implementation order

1. implement CompanyIdentity + SourceRegistryEntry models
2. implement provider-specific source identifier parsers
3. implement source state/health transitions
4. add offline verification/discovery fixtures
5. create a small deterministic seed registry
6. connect Greenhouse registry entries to the Greenhouse adapter
7. persist normalized source snapshots/current corpus
8. add search-time stale-source refresh logic
9. add official-career-page discovery for Greenhouse
10. add result-driven discovery
11. repeat provider discovery/verification for Lever, then Ashby
12. add scheduled registry expansion/health maintenance

## Acceptance criteria

Source Registry V1 is ready for production-style search only when:

1. one company can correctly own multiple source entries
2. provider changes preserve source history rather than overwriting it
3. zero active postings is distinguishable from failed/unavailable source
4. a transient failure does not remove a valid source
5. official careers-page evidence can promote a candidate board to verified
6. weak/guessed identifiers remain unverified candidates
7. search uses one board snapshot across multiple role lanes
8. stale relevant boards can be selectively refreshed during a search
9. a newly discovered supported board can be added and searched
10. indexed job corpus records posting appearance/change/disappearance
11. coverage reports expose source failures and data freshness
12. a source-level false negative can be converted into a regression fixture

## Core product rule

The Source Registry should make Job Hunter faster **because it remembers the job market**, not less complete because it searches fewer sources.

The target behavior is:

> Maintain a broad, fresh map of known employer job sources continuously, then spend search-time effort only where freshness or coverage actually needs improvement.
