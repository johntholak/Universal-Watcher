# Job Source Coverage V1

## Purpose

High-quality ranking is useless if the system never sees a worthwhile job.

Job Hunter therefore treats source coverage as a first-class product problem. The goal is broad discovery from public or authorized sources, then direct-source verification and normalization.

The system must not claim exhaustive coverage when sources are incomplete.

## V1 provider order

### 1. Greenhouse

Use Greenhouse Job Board API public GET endpoints.

Important current properties:

- published job board data is publicly available through GET endpoints
- authentication is not required for public GETs
- board list calls can include full posting content
- individual posting calls can expose first-published data and pay-transparency ranges when configured

Greenhouse remains the first adapter to implement and stabilize.

### 2. Lever

Use Lever's published Postings API / hosted job sites.

Important current properties:

- published postings are publicly viewable
- postings are namespaced by a company/site identifier
- list and detail endpoints are available
- the API is company-site scoped rather than a global cross-company search engine

### 3. Ashby

Use Ashby's public Job Postings API.

Important current properties:

- public job-board endpoint returns currently published postings for a job board
- compensation may be requested when available
- response can include title, location, secondary locations, remote/workplace type, description, publish date, employment type, job URL, and apply URL

### 4. SmartRecruiters

Evaluate after the first three adapters are stable.

SmartRecruiters exposes structured posting endpoints, but authentication/product behavior is more nuanced than the first three providers. Confirm the exact public-access model during implementation rather than assuming all companies can be consumed identically.

## Core coverage problem

Provider APIs are generally scoped to a company/job-board identifier.

Examples:

- Greenhouse: board token
- Lever: site name
- Ashby: job board name
- SmartRecruiters: company identifier

Therefore a provider adapter alone does not create broad search coverage. Job Hunter also needs a reliable way to discover and maintain the universe of company boards.

## Source Registry

Create a persistent `SourceRegistry` containing discovered company/job-board endpoints.

Suggested fields:

- canonical company name
- company domain
- ATS provider
- provider board/site/company identifier
- public board URL
- API/feed endpoint template
- first discovered timestamp
- last verified timestamp
- last successful fetch timestamp
- last failure state
- active/inactive status
- discovery method
- confidence

Do not delete a registry entry merely because one fetch fails. Provider errors are source-availability events, not proof that the company has no jobs.

## Board discovery methods

V1 should combine several methods rather than rely on one list.

### A. Seed registry

Start with a curated set of companies likely to contain relevant roles.

This gives deterministic test coverage and immediate usefulness while dynamic discovery matures.

The seed set should not become a hidden permanent universe. It is only a bootstrap.

### B. Career-page detection

When a company is known, inspect its public careers page and detect supported ATS destinations such as:

- Greenhouse-hosted boards
- Lever-hosted boards
- Ashby-hosted boards
- SmartRecruiters-hosted pages

Store the resolved provider identifier in the Source Registry.

Prefer official company careers pages as the starting evidence for provider identity.

### C. Public-web discovery sweeps

Use ordinary public web/search discovery to find ATS-hosted postings and boards that match search lanes, companies, roles, and geography.

Examples conceptually:

- discover Greenhouse board pages containing relevant role families
- discover Lever sites containing relevant functions
- discover Ashby boards from job results
- discover company career pages for companies not yet registered

Discovery search finds sources/candidates; the ATS/direct company source should be used for normalized truth whenever possible.

### D. Result-driven expansion

Whenever a legitimate posting is found from an unregistered company/provider board:

1. validate the company/board relationship
2. add the board to the registry
3. fetch the board's complete current public postings
4. normalize relevant candidates
5. retain the board for future watches/searches

The searchable universe should therefore improve over time.

### E. User/company targeted expansion

If a user explicitly searches a company or company type and it is absent from the registry, run provider/career-page discovery for that company before concluding there are no jobs.

## Search coverage strategy

A search should operate in two layers.

### Layer 1: Known-board sweep

Query all active registered boards relevant to the search scope.

Provider adapters should retrieve board data efficiently and cache appropriately so the same board is not redundantly fetched for every role lane.

### Layer 2: Discovery expansion

In parallel or after the known-board sweep, look for relevant companies/boards not yet in the registry.

Newly discovered boards are added and searched before the run is considered complete enough to present results.

The UI may report source coverage/progress, but must not call it exhaustive unless it truly is.

## Broad retrieval before deep scoring

Source retrieval should maximize plausible candidate recall cheaply.

Suggested pipeline:

1. fetch public postings from source boards
2. normalize metadata and content
3. apply freshness window
4. deduplicate
5. perform inexpensive broad relevance screening across direct/adjacent/transferable role lanes
6. enrich plausible candidates with provider detail calls where useful
7. run hard filters
8. run deep resume/job evidence matching
9. score/rank

Do not perform expensive deep analysis on every clearly irrelevant posting from a large board.

## Provider detail enrichment

Use list endpoints for broad retrieval when they already contain enough description data.

Use individual/detail calls selectively for fields that materially improve matching or practical fit, such as:

- first-published date
- explicit compensation
- richer description/requirements
- precise location/workplace data
- requisition identifiers

Avoid a mandatory detail request for every job on every board when the list payload is already sufficient.

## Freshness

Store separately when available:

- first published timestamp
- last updated timestamp
- retrieval timestamp

Do not substitute `updated_at` for `posted_at` when a provider exposes both.

Posting-age filters should use the best available evidence and clearly represent uncertainty when only update time is known.

## Direct-source verification

When a candidate was discovered through web search or another indirect path, verify against the direct ATS/company source before treating it as an active result whenever practical.

A stale indexed webpage should not outrank current ATS truth.

## Dedupe across providers

Preserve all provenance while presenting one logical job.

Cross-source duplicate evidence may include:

- requisition ID
- ATS job ID / canonical URL
- company + normalized title + normalized location
- substantially identical description
- same employer apply destination

Do not merge low-confidence postings solely because titles look alike.

## Failure handling

Distinguish:

- source returned zero active postings
- board identifier invalid
- network/provider unavailable
- parsing/normalization failure
- rate limit
- access/authentication issue
- board moved providers

Never convert an adapter failure into `no jobs found`.

## Caching and watches

Board data should be cached with provider-aware freshness rules.

Watches should preferentially use incremental/changed-posting behavior when supported, otherwise compare normalized snapshots.

For every observed posting retain enough history to detect:

- newly published
- materially updated
- removed/closed
- compensation change
- location/work-arrangement change

## Coverage transparency

Every search should retain a coverage report containing at least:

- providers attempted
- boards attempted
- boards successfully fetched
- boards failed/unavailable
- dynamically discovered boards
- total raw postings retrieved
- postings surviving freshness/dedupe/relevance stages

User-facing UI can simplify this, but internal logs must remain auditable.

## Acceptance criteria

Source coverage V1 is not ready merely because one adapter parses jobs.

Minimum acceptance:

1. Greenhouse adapter passes offline fixture tests
2. registry can store and revalidate multiple company boards
3. a search can sweep many boards without per-title redundant refetching
4. provider failures remain distinguishable from zero results
5. direct source URLs/provenance survive normalization/deduplication
6. dynamic discovery can add a previously unknown supported board
7. freshness timestamps are not conflated
8. source coverage report is produced for each search
9. broad-retrieval test set demonstrates that relevant jobs are not lost before deep scoring

## Product rule

Job Hunter should never imply that a short result list means only a few relevant jobs exist unless source coverage actually supports that conclusion.

A short list should mean:

> These are the worthwhile jobs we found across the sources we successfully searched.

not:

> These are all the worthwhile jobs on the internet.
