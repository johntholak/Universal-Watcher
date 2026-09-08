# Automated Job Hunter — V1 UI / Interaction Design

## Goal

The interface should make the primary experience feel simple even though the underlying search is broad and sophisticated.

Primary flow:

`Drop resume -> choose a few practical filters -> Find My Best Jobs -> review ranked results`

The product should not feel like a traditional job board with dozens of filters and an endless result list. It should feel like a personal job-search analyst.

## Design principles

- Resume-first, not form-first.
- Minimal controls on the main screen; advanced options stay collapsed.
- Emphasize quality and explainability over result volume.
- Show enough search-progress information to build trust that broad retrieval happened before narrowing.
- Keep Career Fit, Practical Fit, and Confidence visibly distinct.
- Missing information must look unknown, never silently negative.
- Results should be scannable in seconds, with deeper reasoning one click away.
- Filtered-out jobs remain inspectable for auditability.
- No fixed top-N presentation cap.

## Primary navigation

V1 top-level areas:

1. Find Jobs
2. Saved / Watching
3. Applications
4. Resume / Profile

`Find Jobs` is the default landing area.

## Screen 1 — Find My Best Jobs

### Header

Primary heading:

**Find My Best Jobs**

Supporting line:

Upload your resume, choose what matters right now, and Job Hunter will search broadly and rank the roles worth your time.

### Resume panel

Large drag-and-drop area at the top of the workflow.

States:

#### No resume

- Drag & drop resume
- Upload PDF or DOCX
- Short privacy/explainability note

#### Resume processing

Show lightweight progress such as:

- Reading resume
- Building experience profile
- Identifying direct, adjacent, and transferable role families

#### Resume ready

Compact summary card containing:

- resume file name
- last analyzed time
- high-level role-family summary
- detected seniority / leadership scope
- a small `Review profile` action
- `Replace resume`

Do not force the user to review or correct the profile before searching.

### Main search controls

Use compact segmented controls / dropdowns rather than a large form.

#### Posted

Options:

- 24 hours
- 3 days
- 7 days
- 14 days
- 30 days
- Any time

Default: 7 days.

#### Minimum salary

Options:

- No minimum
- $75k+
- $100k+
- $125k+
- $150k+
- $175k+
- $200k+
- Custom

If salary is missing, the role remains eligible unless the user explicitly enables a future strict known-salary rule.

#### Location / distance

Reference location can be saved once.

Options:

- 10 mi
- 25 mi
- 50 mi
- 100 mi
- Custom
- Anywhere

Also show work-arrangement choices:

- Remote
- Hybrid
- Onsite
- Any

Multiple modes may be selected.

#### Employment

- Full-time
- Contract
- Part-time
- Temporary
- Any

#### Match style

Use three visually clear choices:

- Best Matches Only
- Best + Good Stretches
- Include Transferable Roles

Suggested default: Best + Good Stretches.

### Advanced options

Collapsed by default behind `Advanced filters`.

Possible fields:

- titles to include
- titles to exclude
- companies to include
- companies to exclude
- industries
- seniority range
- travel tolerance
- required skills
- excluded keywords
- credential / authorization requirements

Advanced controls should never dominate the primary workflow.

### Primary action

Large primary button:

**Find My Best Jobs**

Secondary text action:

**Search for something specific**

This opens manual / natural-language search while continuing to use the active resume profile for fit analysis.

## Search progress state

Do not show only a generic spinner.

Show a staged progress panel such as:

1. Searching supported sources
2. Discovering additional company boards
3. Removing duplicates
4. Applying practical hard filters
5. Deeply reviewing plausible roles
6. Ranking the jobs worth showing

Useful live counters when available:

- jobs discovered
- duplicates removed
- plausible jobs retained
- jobs deeply reviewed
- jobs worth showing

Example:

`1,842 discovered -> 317 plausible -> 64 deeply reviewed -> 21 worth showing`

Counts are informational and must not imply exhaustive internet coverage.

Include a small expandable `Coverage` area showing provider/board successes and failures.

## Screen 2 — Results

### Results header

Use a human summary rather than a raw count-first job-board header.

Example:

**21 jobs worth your time**

Subtext can summarize the active resume version and practical filters.

Actions:

- Modify search
- Keep Watching This Search
- View coverage

### Result categories

Default visible categories:

1. Excellent Match
2. Strong Match
3. Worth a Look
4. Transferable / Interesting

A fifth inspectable section:

- Filtered Out

Do not force a fixed number of cards into each category.

### Job card hierarchy

Each card should answer the important questions before the user opens the job.

Top area:

- job title
- company
- location / work arrangement
- posted freshness
- compensation when explicitly known

Assessment row:

- Career Fit
- Practical Fit
- Confidence
- recommendation bucket

Avoid presenting one opaque overall number as the sole truth.

Example:

`Career Fit 91 · Practical Fit 84 · High confidence · Excellent Match`

### Why it fits

Show 2–4 concise evidence-based bullets, e.g.:

- Led comparable full-lifecycle programs
- Budget and operational scale align strongly
- Direct people and vendor leadership match
- Technical production experience is highly relevant

### Watch-outs

Show only meaningful concerns, e.g.:

- SaaS industry experience preferred
- 30% travel expectation

### Unknown

Clearly separated from concerns:

- Exact hybrid schedule not provided
- Compensation not published

Unknowns should never be styled like failures.

### Card actions

Primary actions:

- View Job
- Save
- Mark Applied
- Not Interested

Secondary action:

- Why this ranked here

Direct application links should prefer the official employer/ATS destination whenever available.

## Screen 3 — Why This Ranked Here

Open as a side panel or modal so the user does not lose their place in the result list.

Sections:

### Strong evidence

Resume/profile evidence that directly supports the role.

### Equivalent experience

Responsibilities performed under different titles or contexts.

### Transferable evidence

Credible adjacent capabilities that support success in the role.

### Gaps / concerns

Explicit requirements that are unsupported or weaker.

### Unknowns

Important facts not reliably known.

### Score breakdown

Show dimension-level reasoning rather than only a total:

- role/function
- responsibility overlap
- seniority/scope
- skills/experience
- leadership
- scale/complexity
- domain relevance
- preferred qualifications

Also show Practical Fit dimensions separately.

## Screen 4 — Filtered Out audit

Filtered jobs should not clutter the primary experience, but users must be able to inspect them.

Each filtered item should preserve the reason, e.g.:

- outside selected distance
- published compensation below minimum
- disallowed employment type
- posting outside freshness window
- blocked company
- explicit required credential not met

Jobs hidden due only to low ranking should be distinguishable from jobs removed by hard filters.

## Screen 5 — Keep Watching

After a search, the user can choose:

**Keep Watching This Search**

The confirmation should summarize:

- resume/profile version
- freshness setting
- compensation rule
- location/work arrangement
- employment type
- match style
- any advanced constraints

The user should not need to rebuild the search.

Watching should surface only genuinely new or materially changed qualifying jobs and avoid repeat alerts for the same posting.

## Screen 6 — Manual / specific search

Secondary mode available from the main search screen.

Input can support:

- explicit title search
- company search
- industry search
- natural-language intent

Examples:

- `Director of Events`
- `Jobs at Netflix, Disney, Apple, or Amazon`
- `Technical operations roles where my event production background transfers`
- `Jobs outside events I could realistically get`

Manual search modifies the search intent, not the underlying resume evidence.

## Visual direction

The product should feel polished, intelligent, calm, and high-confidence rather than like a dense enterprise ATS.

Preferred characteristics:

- medium-light interface
- strong contrast between functional areas
- depth and layering through cards/panels rather than flat form fields
- clear expandable/collapsible affordances
- restrained use of purple, blue, and green accents
- ample whitespace without looking empty
- results cards should feel recommendation-oriented, not like copied job-board rows

Avoid:

- giant walls of form controls
- overly dark UI
- overly pale low-contrast UI
- unnecessary gradients/effects that reduce readability
- result cards dominated by logos or marketing imagery
- color as the only indicator of fit/status

## Responsive behavior

Desktop is the initial design priority, but the hierarchy should collapse cleanly on mobile.

On smaller screens:

- search controls stack vertically
- result assessment chips wrap cleanly
- Why This Ranked Here opens full-screen rather than as a narrow side panel
- primary actions remain easy to reach

## V1 success test

A first-time user should be able to:

1. upload a resume,
2. understand the extracted high-level profile,
3. set freshness, salary, distance/work arrangement, employment type, and match style,
4. start a search,
5. understand that broad retrieval/narrowing is occurring,
6. inspect a ranked job and understand exactly why it was surfaced,

without needing instructions or a setup wizard.
