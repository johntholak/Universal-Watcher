# Job Matching Baseline

## Order of operations

1. Normalize posting
2. Deduplicate
3. Apply hard filters
4. Score remaining jobs
5. Explain score by dimension
6. Route to Strong Fit / Maybe / Skip

## Hard filters

Hard filters should be explicit user rules such as:

- unacceptable location / commute
- disallowed employment type
- known compensation below a required floor
- required remote arrangement not met
- explicit credential / authorization requirement the user cannot satisfy
- user-blocked company

Unknown information should not trigger a hard rejection unless the user explicitly chooses that policy.

## Fit dimensions

Recommended dimensions:

- role/title match
- seniority and scope
- skills / experience match
- industry / domain relevance
- leadership responsibility
- location / work arrangement
- compensation
- travel expectations
- explicit must-have requirements

Weights belong to the user/search profile and may evolve. The score must retain dimension-level reasons.

## Score interpretation

Do not imply scientific precision. A numeric score may be used internally or visually, but the user-facing explanation is more important than the number.

Suggested buckets:

- Strong Fit: no known hard blocker and strong evidence across priority dimensions
- Maybe: no known hard blocker but meaningful gaps/unknowns/weaknesses
- Skip: hard mismatch or user dismissal

## Feedback loop

User actions such as Save, Apply, Skip, and “not relevant” may later tune ranking, but V1 should keep the logic inspectable and avoid opaque personalization that overrides explicit criteria.

## Truthfulness

Never claim the user qualifies for a role solely because keywords overlap. Never infer compensation, sponsorship, security clearance, work arrangement, or required credentials without evidence.
