# Job Matching Fixtures V1

## Purpose

This document defines the offline fixture suite used to validate Job Hunter's matching and scoring behavior before aggressive result narrowing is trusted.

The fixtures are designed around the core product risk:

> A worthwhile job must not disappear merely because its title, industry, or vocabulary differs from the resume.

The suite therefore tests direct fits, equivalent fits, transferable fits, real gaps, unknowns, hard blockers, and misleading keyword overlap.

## Test architecture

Use synthetic or anonymized candidate profiles and job postings so tests are reproducible and safe to commit.

Recommended structure:

```text
fixtures/
  matching/
    profiles/
      direct_events_leader.json
      equivalent_program_operator.json
      transferable_operations_leader.json
      sparse_profile.json
    jobs/
      direct_event_director.json
      equivalent_field_marketing.json
      transferable_program_manager.json
      misleading_keyword_overlap.json
      hard_blocker_license.json
      unknown_salary.json
      salary_below_floor.json
      title_mismatch_scope_match.json
      title_match_scope_mismatch.json
      preferred_gap_only.json
      required_gap.json
      sparse_posting.json
    cases/
      case_*.json
```

A case ties one profile + one search preference snapshot + one job to expected filter and recommendation behavior.

## Candidate profiles

### Profile A: direct event leader

Evidence includes:

- full-lifecycle event strategy and execution
- multimillion-dollar budget ownership
- vendor/RFP/contracts
- direct people leadership
- large cross-functional teams
- executive stakeholders
- conferences, launches, activations
- technical production exposure

Expected direct lanes:

- Director of Events
- Event Operations
- Experiential leadership

Expected adjacent lanes:

- Field Marketing Operations
- Program Management
- Production Operations

Expected transferable lanes:

- selected Operations leadership
- selected Chief of Staff / strategic operations roles only when responsibilities align

### Profile B: equivalent program operator

Titles do not explicitly say `Program Manager`, but evidence includes:

- multiple workstreams
- schedules/milestones
- budget ownership
- cross-functional delivery
- stakeholder management
- vendor dependencies
- risk/issue management

Purpose: ensure equivalent experience can score near direct title experience.

### Profile C: transferable operations leader

Evidence includes:

- field execution
- distributed teams
- logistics
- staffing
- vendor networks
- complex budgets
- operational troubleshooting
- leadership

No exact target operations title.

Purpose: ensure transferable operations roles can surface when scope is credible.

### Profile D: sparse profile

Contains limited bullets and few metrics.

Purpose: ensure low information reduces confidence rather than silently converting unknowns into gaps.

## Core job fixtures

### 1. Direct event director

Job asks for:

- enterprise event strategy
- budget ownership
- vendor management
- people leadership
- executive stakeholders

Expected with Profile A:

- no hard blocker
- strong direct evidence
- Career Fit normally Excellent range
- at least medium confidence when posting detail is complete

### 2. Equivalent field marketing operations role

Job title differs from resume but responsibilities include:

- regional event programs
- vendor operations
- cross-functional campaign execution
- budget ownership
- field team leadership

Expected with Profile A:

- not filtered by title
- direct/equivalent evidence across responsibilities
- Strong or Worth a Look depending on marketing-specific requirements
- explicit watch-out if demand-generation ownership is required and unsupported

### 3. Transferable senior program manager

Responsibilities include:

- multi-workstream planning
- schedules/dependencies
- executive reporting
- budgets
- vendor coordination
- operational delivery

Expected with Profiles A/B:

- equivalent or transferable evidence is meaningful
- should surface if no major specialist requirement exists
- exact prior `Program Manager` title is not required

### 4. Misleading keyword overlap

Job contains words like `events`, `operations`, and `vendors`, but is actually a specialized licensed clinical operations role.

Expected:

- keywords do not produce a high Career Fit
- required clinical/license gap is surfaced
- hard filter only if the license is explicitly required and known unsatisfied under user rules
- otherwise low-value/filtered outcome with clear reasoning

### 5. Required license blocker

Job is otherwise a high role/scope match but requires a current professional license the profile explicitly lacks.

Expected:

- hard blocker
- cannot be Excellent/Strong regardless of numeric fit
- FilterDecision records exact requirement/evidence

### 6. Unknown salary above-minimum search

Search minimum: $150k.

Posting salary: not published.

Expected:

- no hard salary failure by default
- compensation practical dimension unknown/uncovered
- confidence/practical coverage reflects missing data
- job may still surface

### 7. Known salary below minimum

Search minimum: $150k.

Posting max: $130k.

Expected:

- hard filter fail
- reason = known compensation below required floor
- never surfaced unless user changes the search criteria

### 8. Title mismatch, scope match

Resume title: Manager.

Job title: Director.

Resume evidence shows larger team/budget/scope than the job requires.

Expected:

- seniority scoring uses scope rather than title alone
- role is not downgraded merely because prior title is Manager

### 9. Title match, scope mismatch

Resume title exactly matches job title, but resume evidence shows narrow execution scope while job requires global strategy, large team leadership, and major budget authority.

Expected:

- title overlap does not create Excellent fit
- seniority/scale gaps are explicit

### 10. Preferred qualification missing

Job says MBA preferred, not required.

Profile has no MBA.

Expected:

- missing MBA is not a hard blocker
- small preferred-qualification deduction/watch-out at most
- otherwise strong role can remain Strong/Excellent depending on total evidence

### 11. Material required capability gap

Job requires ownership of a specialized capability central to the role and profile lacks direct/equivalent/credible transferable evidence.

Expected:

- gap is explicit
- recommendation bucket may be capped
- high scores in unrelated dimensions cannot hide the gap

### 12. Sparse posting

Posting has title/location and two vague sentences.

Expected:

- provisional Career Fit may be possible
- confidence is low
- unknowns are prominent
- job remains eligible for Worth a Look if plausible
- system does not invent requirements

### 13. Industry mismatch with strong scope overlap

Candidate has events/operations background; role is in another industry but asks for comparable program scope.

Expected:

- industry dimension lower
- responsibility/scope evidence remains strong
- role can still surface

### 14. Industry match with weak responsibility overlap

Same industry, but function is materially different.

Expected:

- domain similarity does not overpower weak functional evidence

### 15. Remote status unknown

User accepts Remote or Hybrid, rejects Onsite.

Posting location text is city-based but work arrangement is not explicit.

Expected:

- unknown work arrangement is not automatically onsite
- no hard failure until contradictory evidence exists
- practical confidence/coverage reduced

### 16. Explicit onsite conflict

Same search as above; posting explicitly requires 5 days onsite.

Expected:

- hard work-arrangement fail

### 17. Freshness unknown

User selects Last 7 days.

Provider update time is recent but publication time is unavailable.

Expected:

- do not treat update time as publication time
- freshness outcome = unknown by default
- candidate remains eligible unless strict-known-freshness policy exists

### 18. Old published date

User selects Last 7 days.

`published_at` = 18 days ago.

Expected:

- hard freshness filter fail

## Evidence type expectations

Each case should assert the dominant evidence state for important requirements.

Examples:

### Direct

Job: `Own event budgets above $1M`
Profile: explicit $4.5M event budget ownership.
Expected evidence type: direct.

### Equivalent

Job: `Lead integrated field programs across regions`
Profile: explicit multi-market activations with staffing, vendor, schedule, and budget ownership under a Producer title.
Expected evidence type: equivalent when scope aligns.

### Transferable

Job: `Run distributed operational programs across multiple sites`
Profile: event operations across many markets with comparable logistics/teams/vendors but not same business function.
Expected evidence type: transferable.

### Gap

Job: `Active CPA required`
Profile: no CPA and user confirms none.
Expected evidence type: gap / hard blocker under credential rules.

### Unknown

Job: `Experience with internal tool X preferred`
Profile: no evidence either way.
Expected: unknown or minor unsupported preferred qualification, not an invented no.

## Score relationship assertions

Avoid brittle exact-score tests for language-model-assisted dimensions.

Prefer assertions such as:

- direct_fit Career Fit > title_match_scope_mismatch
- equivalent_scope_match remains within a reasonable band of direct_fit
- transferable_credible > unrelated_keyword_overlap
- known hard blocker never surfaces regardless of score
- missing preferred qualification has materially smaller impact than missing required capability
- industry mismatch alone cannot erase strong responsibility/scope match

Deterministic dimensions such as compensation hard filters may use exact assertions.

## Bucket assertions

Fixtures should assert allowed bucket sets when exact boundaries may evolve.

Example:

```json
{
  "case": "equivalent_field_marketing",
  "allowed_buckets": ["strong_match", "worth_a_look"],
  "forbidden_buckets": ["filtered_out"],
  "must_include_reason": "equivalent"
}
```

For hard blockers, exact bucket should be `filtered_out`.

## Ranking set tests

In addition to one-job cases, create multi-job ranking sets.

### Ranking Set 1: direct vs weak direct-title vs equivalent

Jobs:

- A: direct title + strong scope match
- B: direct title + weak scope match
- C: different title + excellent responsibility/scope match

Expected:

- A and C outrank B
- C may outrank B despite title mismatch

### Ranking Set 2: career fit vs practical fit

Jobs:

- A: Career Fit 90-ish, long commute but within allowed radius
- B: Career Fit 82-ish, ideal remote/practical fit

Expected:

- both may surface
- system preserves Career Fit and Practical Fit separately
- configured ranking policy determines ordering without hiding the distinction

### Ranking Set 3: uncertainty

Jobs:

- A: strong evidence, medium score
- B: very sparse posting with provisional high score

Expected:

- confidence affects ordering/explanation
- sparse job is not presented with false certainty

## False-negative protection tests

Create at least 20 synthetic jobs containing a mix of:

- direct roles
- adjacent roles
- transferable roles
- irrelevant jobs

Human-label them before tuning as:

- Definitely Apply
- Probably Apply
- Maybe
- No

The automated surfacing logic should be evaluated on the same primary metric as production validation:

> Recall of Definitely Apply + Probably Apply.

Before aggressive hiding logic is enabled in V1, the combined fixture/held-out validation process should meet the provisional 95% worthwhile-job recall target.

## Anti-overfitting rule

Do not tune every threshold until the fixture suite becomes perfect while real jobs fail.

Maintain:

- development fixtures used during implementation
- held-out validation jobs not used to tune thresholds

A scoring-model version change should rerun both.

## Explanation assertions

Every surfaced test job should produce structured explanation content that includes, where applicable:

- strongest evidence
- equivalent/transferable reasoning
- watch-outs
- material gaps
- unknowns
- hard filter status

Tests should verify the explanation is grounded in actual profile/job evidence rather than checking exact prose wording.

## Regression cases from user feedback

When a real search misses a job the user says is worthwhile, create a minimized anonymized regression fixture capturing the failure pattern.

Examples:

- unusual job title
- misleading industry vocabulary
- hidden transferable requirement
- salary parsing issue
- location/work arrangement ambiguity

Once added, that regression should remain in the suite.

## Acceptance gates

Do not trust aggressive narrowing until:

1. direct fits reliably surface
2. equivalent responsibility matches are not punished for title differences
3. credible transferable roles surface under the appropriate match style
4. real required gaps are visible and can cap buckets
5. preferred gaps do not behave like required gaps
6. unknown salary/work arrangement/freshness do not silently become failures
7. hard blockers beat numeric scores
8. title match cannot hide scope mismatch
9. industry match cannot overpower weak functional fit
10. worthwhile-job recall meets the provisional target on held-out validation

## Core rule

The matching system is successful when it recognizes evidence of capability, not merely vocabulary similarity.