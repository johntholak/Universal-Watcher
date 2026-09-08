# Job Resume Intelligence Profile V1

## Purpose

The resume intelligence layer converts an uploaded resume into a structured, reviewable working profile that powers job discovery and fit analysis.

The user should not need to manually recreate their career history before searching.

The profile must be evidence-backed. It may infer reasonable role families and transferable capabilities, but it must not invent facts that are not supported by the resume or explicit user input.

## Primary flow

1. User uploads PDF or DOCX.
2. Extract resume text and structure.
3. Parse chronology and role history.
4. Extract explicit facts and accomplishments.
5. Derive capability evidence.
6. Generate direct, adjacent, and transferable role families.
7. Show a compact review summary.
8. Allow user corrections/overrides.
9. Save a versioned working profile.
10. Use that profile for search, scoring, and watches.

## Profile sections

### Identity / location

Store only job-search-relevant information that is explicitly present or supplied by the user:

- name when provided
- home/reference location when provided
- preferred search location separately from resume location

Do not infer protected or sensitive personal characteristics.

### Role history

For each role capture, when available:

- employer
- title
- start date
- end date / current status
- location
- employment type if explicit
- role summary
- responsibilities
- accomplishments
- direct reports / team scope
- budget ownership
- geographic scope
- clients / brands / business units
- tools / systems / technologies
- industries / domains

Each field should retain evidence provenance to the source resume section/text.

### Career-level signals

Derive cautiously from role history:

- total relevant experience range
- leadership experience range
- people-management evidence
- strategic ownership evidence
- execution/operations depth
- budget/program scale
- executive stakeholder exposure
- vendor/client ownership
- cross-functional leadership
- technical/operational depth
- field/travel experience
- business ownership / P&L evidence when explicit

Do not turn an uncertain chronology into a precise years-of-experience claim.

### Skills and capabilities

Represent capabilities as structured evidence rather than a flat keyword list.

Each capability should include:

- canonical capability name
- evidence strength
- evidence type
- supporting role(s)
- supporting accomplishment/responsibility excerpts or references
- recency when available
- scale/scope signals when available
- confidence

Examples of capability families:

- event strategy
- event operations
- experiential marketing
- production management
- AV / event technology
- program management
- project management
- field operations
- logistics
- vendor management
- RFP / contracts
- budget ownership
- staffing / team leadership
- executive stakeholder management
- client services
- launches / conferences / activations

The capability taxonomy should remain extensible rather than hard-coded only for one user's resume.

## Evidence states

Resume-derived facts should distinguish:

### Explicit

Directly stated in the resume.

### Strongly derived

Not stated as a label, but strongly supported by multiple explicit resume facts.

### Tentative inference

Plausible but uncertain. Tentative inferences may help broaden discovery but must not be treated as known qualifications in scoring.

### User confirmed

Explicitly corrected or confirmed by the user. User-confirmed data overrides automated inference unless later changed by the user.

## Role-family generation

The profile should generate three discovery lanes.

### Direct role families

Roles closely aligned with titles and responsibilities already performed.

### Adjacent role families

Roles with substantial responsibility/scope overlap under different naming or organizational structures.

### Transferable role families

Roles where capability evidence supports a credible transition despite different title/domain conventions.

Every generated role family should preserve a reason, for example:

- `Director of Events` because of direct title/responsibility evidence
- `Director of Experiential Marketing` because event strategy + brand activations + vendor/budget leadership strongly overlap
- `Senior Program Manager` because multi-workstream delivery + cross-functional coordination + budget/schedule ownership transfer strongly

The system should avoid producing hundreds of speculative role families. Breadth should be meaningful, not random.

## Title normalization

Store both original title and normalized interpretations.

Example:

- original: `Manager, Events and Experiences`
- normalized families: `Events`, `Experiential`, `Event Operations`, `Program/Project Management`

Title normalization must use responsibilities and scope, not title text alone.

## Seniority inference

Seniority should use multiple signals:

- title
- reporting/management scope
- budget authority
- strategic ownership
- stakeholder level
- program scale
- decision authority
- career progression

Do not assume every `Director` role is equivalent or every `Manager` role is below every `Director` role.

Represent seniority as a range or band when evidence is mixed.

## Accomplishment extraction

Prefer measurable evidence where present:

- budget size
- team size
- event/program count
- attendee/user scale
- revenue/savings
- geographic reach
- launch count
- client/brand scope
- operational performance

Do not invent metrics from vague language.

These accomplishments should materially influence scale, seniority, leadership, and responsibility-overlap scoring.

## Requirements matching support

The profile should be capable of answering structured questions such as:

- Has the user managed people?
- Has the user owned budgets of comparable scale?
- Has the user run multi-vendor programs?
- Has the user worked directly with executives?
- Is there direct SaaS experience?
- Is there equivalent experience even if the exact industry differs?
- Is a requested capability unsupported or merely not explicitly labeled?

The answer should include evidence and confidence, not only yes/no.

## Unknown handling

If the resume does not establish a fact, keep it unknown.

Examples:

- do not infer a degree that is not listed
- do not infer security clearance
- do not infer work authorization
- do not infer salary history
- do not infer willingness to relocate/travel
- do not infer a certification from adjacent experience

Search controls/user preferences are stored separately from resume facts.

## User review experience

After upload, show a concise summary rather than a giant editable form.

Suggested summary:

- current/most recent role
- inferred seniority band
- strongest capability families
- direct role families
- adjacent role families
- transferable role families
- notable leadership/scale signals

Actions:

- Looks right
- Edit
- Add target role
- Remove suggested role family

Detailed evidence editing may live behind an advanced view.

## User overrides

User corrections are first-class data.

Examples:

- `I managed 40 people overall, not 12.`
- `Do not search sales roles.`
- `I am open to Chief of Staff roles only when they are operations/marketing adjacent.`
- `I do have experience with X even though it is not on this resume.`

Store overrides separately with provenance `user_confirmed` rather than rewriting the original resume evidence.

## Profile versioning

Every material resume replacement or confirmed profile edit creates a new profile version.

A search/watch should record which profile version was used.

This matters because:

- resume updates may change fit scores
- user corrections may change role-family generation
- watches should be reproducible
- historical application decisions should remain auditable

## Resume file handling

V1 should support PDF and DOCX.

The system should preserve the original file reference securely but should operate downstream on extracted structured data.

Extraction failures must be explicit. Do not silently continue with a partial/empty resume as if parsing succeeded.

## Quality checks

Resume parsing tests should include:

- multi-page PDF
- DOCX
- two-column layouts
- unusual section headings
- overlapping employment dates
- current role with no end date
- role with multiple promotions at one company
- sparse resume
- highly detailed resume
- resume with tables
- missing dates
- ambiguous job title
- metrics embedded in bullets

## Acceptance criteria

Before resume-first search is considered reliable:

1. chronology is substantially correct on representative fixtures
2. explicit employers/titles/dates are not fabricated
3. material accomplishments and scale signals are retained
4. user corrections override inference cleanly
5. direct/adjacent/transferable role families include explanations
6. unsupported facts remain unknown
7. downstream matching can cite profile evidence for its conclusions
8. resume replacement creates a new profile version without corrupting prior searches/watches

## Core product rule

The resume is not merely a keyword source.

It is evidence about what the user has actually done, at what scale, with what responsibility, and which adjacent capabilities are credibly transferable.
