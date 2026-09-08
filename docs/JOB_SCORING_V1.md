# Job Scoring V1

## Purpose

The scoring system exists to answer one question reliably:

> Which jobs are genuinely worth the user's time?

The system should optimize first for recall of worthwhile opportunities, then for ranking quality. It should search broadly, eliminate cautiously, and explain every important judgment.

A missing keyword must never outweigh strong evidence that the user has actually done equivalent work.

## Order of operations

1. Normalize the posting.
2. Deduplicate.
3. Apply explicit hard filters.
4. Extract job requirements and responsibilities.
5. Compare each requirement/responsibility against resume/profile evidence.
6. Compute Career Fit.
7. Compute Practical Fit using known information only.
8. Compute assessment Confidence.
9. Assign a visible recommendation bucket.
10. Rank within the bucket.

No numeric score may override a known hard blocker.

## Hard filters

Hard filters are objective user-authorized constraints, not weighted preferences.

Examples:

- outside the selected posting-age window
- onsite/hybrid location outside an explicit allowed radius
- known compensation below an explicit required minimum
- disallowed employment type
- blocked company
- explicit work arrangement conflict
- explicit required credential, license, work authorization, or clearance known to be unsatisfied

Unknown information is not a hard failure unless the user explicitly requests a strict-known-data rule.

Do not hard-filter merely because:

- salary is missing
- work arrangement is unclear
- a title differs from the resume
- industry differs
- a keyword is absent
- the user is somewhat short of a preferred years-of-experience figure
- a preferred qualification is missing

## Evidence types

Every material job requirement should be mapped to one of five evidence states.

### Direct evidence

The resume/profile explicitly shows the same or substantially identical work.

### Equivalent evidence

The resume/profile shows essentially the same responsibility under another title, company type, industry, or operating context.

Equivalent evidence should receive nearly the same credit as direct evidence when the scope is comparable.

### Transferable evidence

The user has not performed the exact responsibility in the same context, but the resume/profile contains credible evidence that the capability transfers.

Transferable evidence can materially support a score and should not be treated as a token bonus.

### Gap

A material requirement appears unsupported by the available resume/profile evidence.

A gap may reduce Career Fit or cap a recommendation bucket, depending on importance. It is not automatically a hard blocker.

### Unknown

The system cannot determine whether the requirement is satisfied.

Unknown is not a pass and not a fail. It lowers confidence rather than silently lowering the user's qualification score.

## Career Fit

Career Fit measures how strongly the resume/profile supports performing the job successfully.

Use a 0-100 score composed of these default dimensions:

| Dimension | Default weight |
| --- | ---: |
| Role / function alignment | 20 |
| Responsibility overlap | 20 |
| Seniority and scope | 15 |
| Skills / experience evidence | 15 |
| Leadership responsibility | 10 |
| Scale / complexity | 10 |
| Industry / domain relevance | 5 |
| Education / certifications / preferred qualifications | 5 |
| **Total** | **100** |

Weights may later be profile- or search-specific, but changes must remain inspectable.

### Scoring evidence within a dimension

Direct and equivalent experience should normally receive strong credit.

Transferable evidence should receive meaningful credit based on how defensible the transfer is, not a fixed low ceiling.

A useful implementation pattern is:

- direct: full or near-full evidence credit
- equivalent: near-full evidence credit when scope is comparable
- transferable: partial-to-strong credit depending on similarity, scale, recency, and supporting accomplishments
- gap: little or no evidence credit and an explicit watch-out
- unknown: remove or reduce confidence in that judgment rather than silently treating it as zero

The exact numeric mapping should be calibrated against human-reviewed jobs rather than assumed to be scientifically precise.

### Seniority and scope

Do not infer seniority from title alone. Consider:

- ownership level
- team leadership
- budget authority
- program scale
- strategic vs execution responsibility
- stakeholder seniority
- decision-making authority
- complexity and geographic scope

A user can be a strong fit for a differently titled role when the underlying scope aligns.

### Required vs preferred qualifications

Required qualifications carry more weight than preferred qualifications.

A missing preferred qualification should rarely move an otherwise strong job out of consideration.

A missing material required capability should be surfaced clearly as a real gap and may cap the visible recommendation bucket even if the total weighted score remains high.

## Practical Fit

Practical Fit measures whether the job works for the user's stated search constraints and preferences.

Default dimensions:

| Dimension | Default weight |
| --- | ---: |
| Location / distance | 30 |
| Work arrangement | 25 |
| Compensation | 25 |
| Employment type | 10 |
| Travel / schedule expectations | 10 |
| **Total** | **100** |

Practical Fit is computed only across dimensions with known evidence unless the user has chosen a strict rule.

Examples:

- missing salary does not become a zero
- unclear hybrid schedule does not become an onsite mismatch
- unknown travel expectations do not become no-travel

The UI should therefore show both the practical score/status and information coverage/confidence.

An explicit practical must-have remains a hard filter and is handled before scoring.

## Confidence

Confidence represents how complete and reliable the assessment evidence is. It is separate from fit.

Inputs should include:

- completeness of the job description
- clarity of required vs preferred qualifications
- availability of compensation/location/work-arrangement data
- posting freshness and provenance quality
- resume/profile extraction confidence
- proportion of important requirements that could be evaluated

Suggested visible levels:

- High confidence
- Medium confidence
- Low confidence

A high Career Fit with low confidence should remain visible but clearly labeled rather than being silently downgraded as though the user were less qualified.

## Recommendation buckets

Recommendation buckets are user-facing decisions, not merely numeric score ranges.

### Excellent Match

Normally requires:

- Career Fit approximately 85+
- no hard blocker
- no major unsupported required qualification
- practical fit acceptable or unknown rather than contradicted
- enough evidence for at least medium confidence

### Strong Match

Normally requires:

- Career Fit approximately 75+
- no hard blocker
- no more than manageable gaps
- practical fit acceptable, mixed, or partly unknown

### Worth a Look

Use when:

- Career Fit is approximately 62+
- or a stronger career match has meaningful practical uncertainty/concerns
- or evidence is promising but incomplete

This bucket exists partly to protect recall. The system should prefer showing a plausible worthwhile role here rather than hiding it prematurely.

### Transferable / Interesting

Use when the exact title/function is not a direct match but strong equivalent or transferable evidence makes the role genuinely credible.

Transferable jobs are not automatically lower quality than direct-title matches. A transferable role may outrank a weaker direct-title role if the underlying responsibility/scope evidence is stronger.

### Filtered Out

Used for:

- hard-filter failures
- clearly low-value matches below the configured surfacing threshold
- user-dismissed jobs

The reason must be preserved and inspectable.

## Bucket guardrails

Do not use thresholds mechanically.

Examples:

- A numeric 88 with a missing legally required license should not appear as Excellent.
- A numeric 72 with strong equivalent responsibility evidence may still be a very worthwhile Strong or Worth-a-Look result.
- A sparse posting may have a high provisional Career Fit but low confidence; show the uncertainty instead of inventing certainty.

## Ranking within buckets

Default ranking priority:

1. stronger Career Fit
2. fewer material gaps
3. stronger Practical Fit on known dimensions
4. higher Confidence
5. greater posting freshness
6. stronger source/provenance quality

Do not use a fixed top-N cutoff. Surface every job that clears the configured quality bar.

## User-visible explanation

Every surfaced job should expose a `Why this ranked here` view with:

- strongest direct evidence
- equivalent evidence
- transferable evidence
- material gaps
- unknowns
- Career Fit
- Practical Fit
- Confidence
- hard-filter status

The explanation is more important than decimal precision in the score.

## High-recall protection

The system should be conservative about hiding jobs until validated against human review.

A candidate that lacks strong evidence of irrelevance should remain eligible for `Worth a Look` or `Transferable / Interesting` rather than disappearing solely because of an uncertain score.

The user should always be able to inspect filtered results and their reasons.

## Calibration and acceptance testing

Before aggressive hiding is enabled, create a human-labeled validation set of real jobs with labels such as:

- Definitely apply
- Probably apply
- Maybe
- No

Primary metric:

> Recall of jobs labeled Definitely Apply or Probably Apply.

Provisional V1 quality target: surface at least 95% of those worthwhile jobs in the validation set before relying on aggressive automatic narrowing.

Secondary metrics may include:

- precision of Excellent/Strong buckets
- ordering quality within buckets
- false hard-filter rate
- explanation agreement with human reasoning
- percentage of results with unresolved critical unknowns

False negatives on worthwhile jobs should be treated as more serious than showing an occasional extra `Worth a Look` result.

## Implementation principle

The scoring engine should produce structured evidence and deterministic components where practical. A language model may help interpret responsibilities, equivalent experience, and transferability, but it must not be the only uninspectable source of truth.

Persist the extracted evidence, dimension scores, gaps, unknowns, and reasons so the same assessment can be audited and tested offline.
