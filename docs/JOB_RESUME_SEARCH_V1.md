# Job Resume-First Search V1

## Locked primary experience

Automated Job Hunter should be usable with minimal setup. The primary V1 entry point is:

`Drop resume -> choose a few practical filters -> Find My Best Jobs -> ranked shortlist`

The resume becomes the main source of candidate context. A manually configured candidate profile may enrich or override extracted data, but users should not need to complete a large profile form before searching.

Manual/specific search remains a secondary mode and should still use the resume-derived profile when evaluating results.

## Resume intake

V1 should accept at minimum:

- PDF
- DOCX

The system should extract a structured working profile including, when supported by evidence in the resume:

- roles held
- seniority and career progression
- years and depth of experience
- industries and domains
- responsibilities
- hard skills
- operational skills
- technical skills
- leadership scope
- budget/program scale
- vendor/client management
- cross-functional work
- education and certifications
- travel/field experience
- likely direct role families
- likely adjacent role families
- credible transferable role families

Unknown or ambiguous facts remain unknown. Resume inference should be reviewable/editable rather than treated as unquestionable truth.

## Default search controls

The main screen should expose only a small set of high-value controls.

### Posting freshness

- Last 24 hours
- Last 3 days
- Last 7 days
- Last 14 days
- Last 30 days
- Any time

Suggested default: Last 7 days.

### Minimum compensation

- No minimum
- Preset salary floors
- Custom minimum

A missing salary should remain unknown and should not be rejected solely because compensation was not published unless the user explicitly chooses a strict known-salary policy.

### Location / distance

- 10 miles
- 25 miles
- 50 miles
- 100 miles
- Custom radius
- Anywhere

The user can store a home/reference location once. Distance rules apply to jobs that require physical presence when location can be determined.

### Work arrangement

- Remote
- Hybrid
- Onsite
- Any

Multiple selections may be allowed.

### Employment type

- Full-time
- Contract
- Part-time
- Temporary
- Any

### Match style

- Best Matches Only
- Best + Good Stretches
- Include Transferable Roles

Match style changes how broadly results are surfaced, but should not change explicit hard filters.

## Advanced search controls

Keep advanced controls collapsed by default. Candidate fields include:

- specific titles to include
- titles to exclude
- companies to include
- companies to exclude
- industries
- seniority range
- travel tolerance
- required skills
- excluded keywords
- explicit credential/authorization constraints

Future fields may include company size, benefits, schedule constraints, and other practical preferences.

## Search philosophy

The product should search broadly, understand deeply, rank aggressively, and eliminate cautiously.

If Job Hunter shows fewer jobs than a traditional job board, missing a genuinely strong opportunity becomes the primary failure mode.

Therefore the system should optimize for high recall before high precision:

1. Search broadly across direct, adjacent, and transferable role families.
2. Normalize and deduplicate.
3. Apply only genuine hard filters early.
4. Deeply compare plausible jobs against the resume/profile.
5. Separate career fit from practical fit.
6. Rank strongly but hide conservatively.

There should be no fixed top-N quota. Return every job that clears the configured quality bar.

## Hard-filter rules

Only objective, user-authorized constraints should remove a role before deep scoring. Examples:

- posting is outside the selected freshness window
- onsite/hybrid job is outside the allowed distance
- explicitly published compensation is below a required floor
- disallowed employment type
- user-blocked company
- required work arrangement is explicitly not met
- an explicit credential, authorization, or clearance requirement is known to be unsatisfied

Do not hard-reject merely because:

- salary is missing
- work arrangement is unclear
- the user is slightly short of a preferred years-of-experience number
- the industry differs
- the title is unfamiliar
- a keyword is absent when equivalent or transferable experience may exist

## Role discovery lanes

Resume analysis should generate multiple search lanes rather than one title query.

### Direct roles

Titles/functions that closely match work already performed.

### Adjacent roles

Titles/functions with substantially overlapping scope under different naming or organizational context.

### Transferable roles

Roles where the resume supplies credible evidence for success even if the user has not held the exact title.

Manual search should also be supported for explicit titles, companies, industries, or natural-language searches.

## Fit analysis

Keyword overlap alone is insufficient.

For each plausible job, Job Hunter should distinguish:

- direct evidence: the user has explicitly done the requested work
- equivalent experience: the user has done essentially the same responsibility under another title/context
- transferable evidence: the user's background credibly supports the responsibility even without exact prior-title alignment
- real gaps: explicit requirements unsupported by the resume/profile
- unknowns: facts that cannot be determined reliably

The scoring system should evaluate at least:

- role/function fit
- seniority and scope
- relevant experience
- skills
- leadership responsibility
- industry/domain relevance
- transferable experience
- location/work arrangement
- compensation
- travel expectations
- explicit required qualifications

## Separate fit concepts

Do not collapse all reasoning into one opaque number too early.

### Career Fit

How strongly the resume/profile supports performing the work.

### Practical Fit

Whether the role meets the user's real-world constraints such as compensation, location, work arrangement, travel, and employment type.

### Confidence

How complete and reliable the evidence is. A strong score based on a detailed posting should be distinguished from a similar score based on sparse or ambiguous data.

## Result experience

The default results should prioritize worthwhile opportunities, not result volume.

Suggested visible buckets:

- Excellent Match
- Strong Match
- Worth a Look
- Transferable / Interesting

Known hard mismatches and low-value results may be hidden by default, but should remain inspectable in a Filtered Out view with the reason preserved.

Each job card should answer:

- What is the job?
- Why does it fit?
- What might be a problem?
- What is unknown?
- What is the career-fit assessment?
- What is the practical-fit assessment?
- How confident is the assessment?
- How fresh is the posting?
- What salary/work arrangement/location information is known?
- Where did the posting come from?
- What should the user do next?

Primary actions:

- View Job
- Save
- Mark Applied
- Not Interested

A result should provide an auditable "Why this ranked here" view showing strong evidence, partial evidence, gaps, and unknowns.

## Search progress

During a search, the UI should communicate that broad retrieval and narrowing are happening rather than showing only a generic spinner.

Useful concepts include:

- jobs discovered
- duplicates removed
- plausible candidates retained
- jobs deeply reviewed
- jobs worth showing

Counts are informational and should not imply exhaustive coverage when sources are incomplete or unavailable.

## Watches

Any completed search can become a watch. A watch preserves:

- resume/profile version
- search filters
- match style
- fit threshold

It should alert on genuinely new or materially changed qualifying jobs rather than repeatedly resurfacing the same posting.

## Learning from feedback

User actions may later improve ranking:

- Apply: strong positive signal
- Save: positive signal
- Maybe/Worth a Look: weak positive signal
- Not Interested: negative signal, optionally with a short reason

Explicit search criteria always outrank learned preferences. Learned behavior must not silently override a user's stated filters.

## Quality target

Before aggressively hiding results, the system should be validated against human review.

The key product metric is not raw classification accuracy. It is recall of worthwhile opportunities:

> Of the jobs the user considers genuinely worth applying to, how many did Job Hunter successfully surface?

The system should earn the right to narrow aggressively only after this recall is consistently high.
