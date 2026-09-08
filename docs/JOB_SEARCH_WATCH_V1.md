# Job Search + Watch Execution V1

## Purpose

This document defines the end-to-end behavior from pressing `Find My Best Jobs` through ranked results and saved watches.

The system should make broad discovery feel simple to the user while retaining enough internal state to explain coverage, ranking, freshness, and future alerts.

## Search modes

### Resume-first search

Primary V1 mode.

Inputs:

- active resume/profile version
- freshness window
- minimum compensation
- reference location / radius
- accepted work arrangements
- employment types
- match style
- optional advanced filters

The system generates direct, adjacent, and transferable role lanes from the active profile.

### Manual/specific search

Secondary V1 mode.

Inputs may include:

- explicit title/function
- company/companies
- industry/domain
- natural-language intent
- same practical filters as resume-first mode

Manual intent changes discovery scope but does not disable resume-based fit evaluation.

## Search snapshot

Every search creates an immutable `SearchRun` snapshot recording at least:

- search id
- started timestamp
- completed timestamp
- profile version id
- search mode
- normalized search filters
- generated role lanes / manual query intent
- source registry version/snapshot reference
- providers attempted
- boards attempted
- source failures
- raw posting count
- deduped posting count
- plausible candidate count
- deeply assessed count
- surfaced result count
- scoring model version
- search status

This allows results to be reproduced and audited even after the profile or scoring model evolves.

## Search execution pipeline

### 1. Validate inputs

Confirm:

- resume/profile exists for resume-first mode
- reference location exists when distance is required
- filters are internally consistent

Do not silently invent missing required user settings.

### 2. Build discovery plan

Combine:

- direct role families
- adjacent role families
- transferable role families when allowed by Match Style
- explicit advanced filters
- company/industry targets
- active Source Registry

The plan should be broad enough to protect recall and should avoid turning every role family into redundant provider fetches.

### 3. Known-board retrieval

Fetch active supported boards using provider adapters.

Board retrieval should normally happen once per board per freshness/cache window, not once per title lane.

Provider failures are captured individually.

### 4. Dynamic source expansion

Look for relevant supported boards/company career sources not yet in the registry.

Validate newly discovered board/company relationships, add them to the registry, and include their public postings in the current search when practical.

### 5. Normalize

Convert provider-specific data into the shared `JobPosting` representation.

Preserve:

- provider/source identity
- provider job/posting id
- requisition id when available
- original URL
- apply URL
- published/updated/retrieved timestamps
- raw provenance reference

### 6. Freshness filter

Apply the user-selected posting-age rule using the best available publication evidence.

Priority:

1. first-published timestamp
2. provider-created/published timestamp
3. defensible posting timestamp from direct source
4. update timestamp only when publication time is unavailable, marked with lower confidence

Do not claim a job was newly posted merely because it was recently updated.

### 7. Deduplicate

Collapse duplicate representations into one logical job while retaining all provenance.

### 8. Broad relevance screening

Use inexpensive signals to remove jobs that are clearly unrelated before deep analysis.

Signals may include:

- role-family/title similarity
- department/function
- responsibility terms
- profile capability families
- manual intent

This stage must be tuned for recall. Uncertain candidates continue forward.

### 9. Selective enrichment

For plausible candidates, request detail data when useful to improve:

- description completeness
- first-published date
- compensation
- workplace type
- location
- requisition id
- requirements

Do not make per-job enrichment mandatory if list data already provides sufficient evidence.

### 10. Hard filters

Apply only explicit objective constraints from the active search/profile rules.

Preserve every filter reason.

### 11. Deep evidence matching

Compare remaining jobs against the active resume/profile.

Produce structured:

- direct evidence
- equivalent evidence
- transferable evidence
- gaps
- unknowns

### 12. Score

Compute:

- Career Fit
- Practical Fit on known dimensions
- Confidence
- recommendation bucket

Use the locked V1 scoring model/version.

### 13. Surface

Return every result that clears the configured quality bar; do not force a fixed top-N.

Default visible buckets:

- Excellent Match
- Strong Match
- Worth a Look
- Transferable / Interesting

Filtered results remain inspectable with reasons.

### 14. Persist run

Save:

- result ordering
- evidence/scoring output
- source coverage report
- filter decisions
- dedupe lineage

## Search progress UX

Suggested progress states:

- Searching job sources
- Expanding company sources
- Removing duplicates
- Checking freshness and filters
- Comparing jobs to your resume
- Ranking worthwhile matches

Useful live counts:

- jobs discovered
- duplicates removed
- plausible candidates
- deeply reviewed
- jobs worth showing

Counts should be factual and should not imply global internet exhaustiveness.

## Match Style behavior

### Best Matches Only

Surface Excellent and Strong by default.

Worth-a-Look candidates may be hidden from the main view but remain accessible.

### Best + Good Stretches

Surface Excellent, Strong, and Worth a Look.

### Include Transferable Roles

Also activate transferable role discovery lanes and surface credible Transferable/Interesting results.

Match Style never relaxes explicit hard filters.

## Result identity and history

Each logical job should have a stable internal identity derived from the strongest available identifiers.

Retain observation history:

- first seen by Job Hunter
- last seen
- first source(s)
- current active/closed state
- material field changes
- prior user action
- prior score/bucket versions

A re-posted job should not automatically be treated as brand new if evidence strongly indicates it is the same requisition.

## User actions

### Save

Adds to saved jobs and creates a positive relevance signal.

### Mark Applied

Creates/updates an application record and a strong positive relevance signal.

### Not Interested

Dismisses the logical job from default future results.

Optionally capture a reason:

- wrong role
- pay
- location
- company
- seniority
- industry
- other

The same unchanged posting should not repeatedly resurface after dismissal.

### View Job

Opens the best direct employer/ATS destination available.

Viewing alone should be a weak or neutral feedback signal in V1.

## Creating a watch

Any completed search may be saved as a watch.

A watch stores:

- watch id
- name
- active profile version or profile policy
- normalized search filters
- role lanes/manual intent
- Match Style
- minimum surfacing threshold/buckets
- source scope
- created timestamp
- last successful run
- last notified observation state

## Profile behavior for watches

Default V1 behavior: a watch stays tied to the profile version used when created so its behavior is reproducible.

When a new resume/profile version becomes active, prompt/offer to update existing watches rather than silently changing their meaning.

A future option may allow `always use latest profile` explicitly.

## Watch triggers

A watch should notify only for a newly qualifying or materially improved opportunity.

Potential notification triggers:

### New job

A logical posting not previously observed by the watch and currently qualifying.

### Newly qualifying job

A previously observed job that did not qualify before but now does because the posting materially changed.

Examples:

- compensation added/increased
- location/work arrangement changed
- job description materially changed
- required qualification changed

### Meaningful ranking improvement

Optional later behavior when a material posting change moves a job into a substantially stronger bucket.

Do not notify merely because:

- retrieval timestamp changed
- source HTML formatting changed
- posting order changed
- inconsequential text changed

## Duplicate notification protection

Track notification state per logical job/watch.

Do not repeatedly alert for the same unchanged posting across:

- repeated watch runs
- mirrored ATS URLs
- provider rediscovery
- search-index rediscovery

## Closed/removed jobs

When a previously active posting disappears or is explicitly closed:

- mark it inactive/closed with observation timestamp
- do not delete history
- preserve application records
- stop surfacing it as open

A temporary provider failure must not mark every job on that board closed.

## Watch failures

A watch run can complete with partial coverage.

Store:

- successful sources
- failed sources
- whether results are complete enough to notify

A source failure should not create false `no new jobs` confidence.

## Notification content

A V1 alert should be concise and decision-oriented:

- title
- company
- recommendation bucket
- Career Fit
- salary if known
- location/work arrangement
- posted/freshness evidence
- one-line reason it is worth attention
- direct view/apply destination

Alerts should not submit applications.

## Application tracking

Basic V1 states:

- Saved
- Applied
- Interviewing
- Rejected
- Offer
- Archived

Application tracking is user-controlled.

The same logical job should connect search history, watch history, and application history rather than creating separate copies.

## Search/watch acceptance criteria

1. one button can execute a resume-first search from a valid profile + practical filters
2. each run records source coverage and profile/scoring versions
3. board data is not redundantly fetched per title lane
4. dynamic discovery can expand a search beyond the initial Source Registry
5. freshness rules distinguish published vs updated time
6. dedupe lineage survives into the result
7. every filter decision and surfaced score is explainable
8. no fixed top-N truncation occurs
9. dismissed unchanged jobs do not repeatedly resurface
10. watches notify once for new qualifying jobs and do not duplicate alerts across mirrored sources
11. provider failure does not mass-close jobs or become `zero jobs`
12. profile updates do not silently mutate existing watch behavior

## Product rule

A search is a documented decision process, not just a list of links.

A watch is the same search decision process repeated against new source observations, with duplicate protection and explicit coverage state.
