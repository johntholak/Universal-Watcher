# Job Resume Parser Fixtures V1

## Purpose

This document defines the implementation-ready offline fixture suite for resume extraction and profile building.

The goal is not merely to prove that text can be extracted from a PDF or DOCX. The goal is to prove that Job Hunter can recover career chronology, scope, accomplishments, capabilities, and uncertainty without fabricating facts.

All parser/profile tests should run offline. No fixture test should depend on a live model API, live document service, ATS provider, or network request.

## Test layers

Resume handling should be tested in three separate layers so failures are diagnosable.

### Layer A: document extraction

Input: PDF or DOCX fixture.

Output:

- extracted text blocks
- page/section references when available
- extraction warnings/errors

Layer A should not infer career meaning.

### Layer B: structured resume parsing

Input: extracted document representation.

Output:

- sections
- employers
- titles
- dates
- role chronology
- responsibilities
- accomplishments
- education/certifications when explicit
- numeric scope signals

Layer B should preserve ambiguity rather than resolve uncertain facts aggressively.

### Layer C: profile intelligence

Input: parsed resume structure.

Output:

- normalized role families
- capability evidence
- seniority band/range
- leadership/scale signals
- direct role families
- adjacent role families
- transferable role families
- evidence states and confidence

Every Layer C conclusion must be traceable to Layer B evidence or a user-confirmed override.

## Fixture directory shape

Recommended structure after migration to the dedicated repository:

```text
fixtures/
  resumes/
    basic_single_column/
      resume.pdf
      resume.docx
      expected_extraction.json
      expected_profile.json
    two_column/
    promotions_same_company/
    overlapping_dates/
    current_role_open_end/
    tables_layout/
    unusual_headings/
    sparse_resume/
    detailed_resume/
    missing_dates/
    ambiguous_title/
    metrics_in_bullets/
    malformed_or_partial/
```

PDF and DOCX do not need to exist for every semantic case, but the suite must include enough of each format to prove both extraction paths.

## Required fixture cases

### 1. Basic single-column resume

Purpose: establish the clean baseline.

Contains:

- three employers
- unambiguous titles
- month/year dates
- standard Experience / Education headings
- bullets with responsibilities and accomplishments

Assertions:

- employer/title/date chronology is correct
- current vs former roles are correct
- responsibilities remain attached to the correct role
- explicit education is retained
- no extra roles or degrees are invented

### 2. Two-column layout

Purpose: prevent text-order corruption.

Contains:

- experience in main column
- skills/education in side column
- dates visually aligned separately from title text

Assertions:

- role bullets do not get attached to the skills column
- chronology remains correct
- education is not mistaken for employment
- duplicated visual text is deduplicated cautiously

### 3. Promotions at one company

Contains:

- same employer
- multiple successive titles
- overlapping company header spanning the roles

Assertions:

- roles remain distinct RoleExperience entries
- same-company continuity is preserved
- promotion/career progression signal may be strongly derived
- dates are not collapsed into one giant role

### 4. Overlapping employment dates

Contains:

- two roles active during part of the same period
- one is explicitly contract/advisory

Assertions:

- both roles remain present
- total years-of-experience logic does not double-count calendar time blindly
- concurrency is represented rather than treated as a date error

### 5. Current role with no end date

Contains:

- `Present` or equivalent current-role marker

Assertions:

- `is_current=true`
- end date remains open/null
- parser does not invent an end date

### 6. Resume using tables

Contains:

- employer/title/date data inside table cells
- bullets outside the table

Assertions:

- logical role grouping survives table extraction
- dates attach to the intended role
- no table header becomes an employer/title

### 7. Unusual section headings

Examples:

- `Selected Experience`
- `Career Highlights`
- `Leadership`
- `Major Engagements`

Assertions:

- parser does not require exact standard headings
- career history vs standalone highlights are distinguished using structure/evidence

### 8. Sparse resume

Contains:

- titles and companies
- very few bullets
- little quantified scope

Assertions:

- known role facts are retained
- missing leadership/budget/team evidence stays unknown
- profile confidence is lower
- tentative role-family broadening may occur, but unsupported qualifications are not marked explicit

### 9. Highly detailed resume

Contains:

- long bullets
- many projects/clients
- multiple metrics

Assertions:

- important accomplishments are not lost due to truncation
- project/client names do not become employers accidentally
- capability evidence can cite multiple supporting facts

### 10. Missing dates

Contains:

- one role with no employment dates

Assertions:

- role remains usable
- chronology confidence is reduced
- system does not invent dates or precise years of experience from it

### 11. Ambiguous title

Example title:

- `Producer`

Responsibilities make it clear the role includes program management, vendor ownership, field operations, budgets, and live production.

Assertions:

- original title remains `Producer`
- normalized role families may include Events / Production / Program or Project Management when supported
- system does not infer unrelated film/TV creative-production capabilities solely from the title

### 12. Metrics embedded in bullets

Contains explicit facts such as:

- managed a $4.5M annual program budget
- led 8 direct reports and a 35-person seasonal team
- delivered 60+ events across 14 markets

Assertions:

- numeric values are retained with surrounding meaning
- budget does not become compensation
- team size does not become attendee count
- scope metrics influence leadership/scale evidence

### 13. Preferred-skill ambiguity

Contains explicit use of a tool in one old role and generic adjacent experience later.

Assertions:

- capability recency is preserved
- old direct evidence remains direct, not erased
- later adjacent experience does not become a false claim of recent direct tool use

### 14. Malformed/partial extraction

Contains a damaged or intentionally incomplete extracted representation.

Assertions:

- extraction/profile status becomes partial or failed as appropriate
- system does not silently publish a normal profile
- warnings/errors are inspectable
- downstream search cannot treat an empty/partial profile as fully valid without an explicit fallback policy

## Expected profile fixture format

Use structured expected outputs rather than full exact-object equality where wording may evolve.

Example:

```json
{
  "roles": [
    {
      "employer": "Example Events Co",
      "original_title": "Producer",
      "start": "2019-03",
      "end": "2022-08",
      "must_have_capabilities": [
        "event operations",
        "vendor management",
        "budget ownership"
      ]
    }
  ],
  "must_have_explicit_facts": [
    "budget:$4500000",
    "direct_reports:8",
    "extended_team:35"
  ],
  "must_have_role_families": {
    "direct": ["Events", "Production"],
    "adjacent": ["Program Management"],
    "transferable": ["Operations"]
  },
  "must_remain_unknown": [
    "degree",
    "security_clearance",
    "work_authorization"
  ]
}
```

Fixture assertions should favor semantic invariants over brittle generated wording.

## Evidence assertions

Every important extracted or derived fact should be testable for provenance.

At minimum, tests should confirm that:

- explicit facts point to resume evidence
- strongly derived capabilities cite one or more explicit facts
- tentative inferences are labeled tentative
- user-confirmed overrides are separate from resume-derived evidence
- unsupported facts have no fabricated evidence reference

## Role-family tests

Role-family generation should have dedicated tests independent of PDF/DOCX extraction.

Required scenarios:

### Direct-title alignment

Resume: Director of Events with matching scope.
Expected: Event leadership/director role family is direct.

### Different title, equivalent work

Resume: Producer with budget/vendor/team/program ownership.
Expected: Program/Project Management may be adjacent when evidence supports it.

### Transferable operations path

Resume: large-scale event operations leadership with complex logistics, staffing, vendors, budgets, and executive stakeholders.
Expected: selected operations leadership roles may be transferable with an explanation.

### Unsupported speculative path

Resume: no finance/accounting evidence.
Expected: Finance Director must not appear as direct/adjacent/transferable solely because the user managed budgets.

## Seniority tests

Seniority must not be title-only.

Fixtures should compare cases such as:

- `Manager` with large team/budget/global ownership
- `Director` with narrow individual-contributor scope

Assertions:

- inferred band may overlap
- title remains one signal among several
- the system can explain the scope evidence behind the band

## Resume replacement/versioning tests

Create two versions of the same synthetic candidate resume.

Version 1:

- older role history

Version 2:

- adds a new leadership role and new capability

Assertions:

- new ResumeDocument/ProfileVersion IDs are created
- prior ProfileVersion remains unchanged
- prior SearchRuns remain pinned to the old profile version
- new searches can use the new version

## User correction tests

Base fixture says:

- `Led 10-person team`

User override says:

- `10 were direct reports; total onsite organization was 40.`

Assertions:

- original resume evidence is preserved
- user-confirmed team-scope data is stored separately
- downstream scoring can use the confirmed broader scope
- provenance clearly distinguishes resume text from user confirmation

## Matching handoff fixtures

At least three profile fixtures should be designed specifically for downstream job matching:

### Profile A: obvious direct fit

Rich direct event-leadership evidence.

### Profile B: equivalent-title fit

Different titles but highly overlapping responsibilities.

### Profile C: credible transferable fit

Strong operations/program evidence with no exact target title.

These profiles should be reusable by scoring tests so parser and matcher share the same evidence model.

## Parser acceptance gates

Do not consider resume-first search ready until representative fixtures demonstrate:

1. no fabricated employers/titles/dates
2. chronology is materially correct
3. accomplishments stay attached to the right role
4. explicit metrics retain their meaning
5. ambiguity remains visible instead of being guessed away
6. role-family generation is explainable
7. user overrides work without mutating original evidence
8. prior profile versions remain reproducible
9. downstream matching can cite evidence references
10. partial extraction cannot masquerade as successful parsing

## Failure severity

Treat these as critical failures:

- invented employer/title/degree/certification
- role bullets assigned to the wrong employer in a way that changes qualification evidence
- fabricated dates or precise years
- losing a major explicit accomplishment used for matching
- silently accepting an extraction failure

Treat these as important but non-critical calibration issues:

- imperfect role-family ordering
- slightly conservative capability strength
- wording differences in explanations

## Core rule

A parser that produces more inferred information is not necessarily better.

The best parser preserves the resume's real career evidence accurately enough that the matching engine can reason broadly without inventing qualifications.