# Job Hunter Data Model V1

## Purpose

This document defines the conceptual V1 domain model needed to implement resume-first search, explainable scoring, source coverage, watches, and application tracking.

The current bootstrap models are intentionally minimal and will need to evolve toward this structure after the project is moved into its dedicated repository and baseline tests are rerun.

## Design rules

- Preserve raw/direct-source provenance.
- Version resume/profile and scoring inputs.
- Separate facts from inferences.
- Separate user preferences from resume facts.
- Separate provider postings from logical deduplicated jobs.
- Preserve unknown values as unknown.
- Keep hard-filter decisions and scoring evidence auditable.
- Never require a single opaque `match_score` to reconstruct why a job was shown.

## Core identifiers

Use stable internal IDs for:

- resume document
- profile version
- source registry entry
- provider posting observation
- logical job
- search run
- watch
- application record
- scoring model version

Provider IDs/URLs remain external identifiers and are preserved separately.

## ResumeDocument

Represents an uploaded source resume.

Fields:

- `id`
- `filename`
- `media_type`
- `uploaded_at`
- `content_hash`
- `original_file_reference`
- `extraction_status`
- `extracted_text_reference`
- `parser_version`
- `extraction_errors`

Do not treat a partial/failed extraction as a successful resume profile.

## EvidenceReference

Traceable evidence supporting an extracted or inferred profile fact.

Fields:

- `resume_document_id`
- `section`
- `role_id` when applicable
- `text_reference` or normalized excerpt reference
- `evidence_state`
- `confidence`

Evidence states:

- explicit
- strongly_derived
- tentative_inference
- user_confirmed

## RoleExperience

Represents one employment/leadership experience entry.

Fields:

- `id`
- `employer`
- `original_title`
- `normalized_title_families`
- `start_date`
- `end_date`
- `is_current`
- `location`
- `employment_type`
- `summary`
- `responsibilities`
- `accomplishments`
- `team_scope`
- `budget_scope`
- `geographic_scope`
- `clients_brands_business_units`
- `tools_technologies`
- `industries_domains`
- `evidence_refs`

Dates and numeric scope values may include confidence/range metadata when the resume is ambiguous.

## CapabilityEvidence

Represents evidence that the user possesses a capability.

Fields:

- `capability_id/name`
- `canonical_family`
- `strength`
- `evidence_state`
- `supporting_role_ids`
- `supporting_evidence_refs`
- `recency`
- `scale_signals`
- `confidence`

Examples include event operations, vendor management, budget ownership, program management, technical production, people leadership, etc.

## RoleFamilySuggestion

Represents a search lane generated from the profile.

Fields:

- `name`
- `lane_type`: direct / adjacent / transferable
- `reason`
- `supporting_capabilities`
- `supporting_role_ids`
- `confidence`
- `user_state`: accepted / removed / unreviewed

## ProfileVersion

Immutable working candidate profile used for search/scoring.

Fields:

- `id`
- `created_at`
- `resume_document_id`
- `role_history`
- `capabilities`
- `seniority_band`
- `career_level_signals`
- `direct_role_families`
- `adjacent_role_families`
- `transferable_role_families`
- `education_certifications`
- `user_confirmed_overrides`
- `profile_builder_version`

A new material resume/profile edit creates a new ProfileVersion.

## SearchPreferences

User intent/preferences are not resume facts.

Fields:

- `reference_location`
- `radius_miles`
- `accepted_work_arrangements`
- `employment_types`
- `minimum_compensation`
- `strict_known_salary_required`
- `freshness_window`
- `match_style`
- `included_titles`
- `excluded_titles`
- `included_companies`
- `blocked_companies`
- `industries`
- `seniority_range`
- `travel_tolerance`
- `required_skills`
- `excluded_terms`
- `credential_authorization_constraints`

Optional/unknown preference fields remain null/unset rather than receiving guessed defaults except for explicitly documented UI defaults.

## SourceRegistryEntry

Represents a discovered company/provider board.

Fields:

- `id`
- `canonical_company_name`
- `company_domain`
- `provider`
- `provider_identifier`
- `public_board_url`
- `endpoint_reference`
- `discovery_method`
- `discovery_confidence`
- `first_discovered_at`
- `last_verified_at`
- `last_successful_fetch_at`
- `last_failure`
- `status`

Status examples:

- active
- inactive
- moved
- temporarily_unavailable
- invalid

One transient error must not permanently invalidate a source.

## ProviderPosting

One provider/source representation of a posting.

Fields:

- `id`
- `source_registry_entry_id`
- `provider`
- `provider_posting_id`
- `provider_job_id`
- `requisition_id`
- `company`
- `title`
- `location_text`
- `structured_locations`
- `work_arrangement`
- `employment_type`
- `compensation`
- `description_raw/reference`
- `description_normalized`
- `department`
- `team`
- `published_at`
- `updated_at`
- `retrieved_at`
- `job_url`
- `apply_url`
- `raw_provenance_reference`
- `source_confidence`

Do not overwrite published time with update time.

## Compensation

Fields:

- `minimum`
- `maximum`
- `currency`
- `period`
- `compensation_type`
- `location_tier`
- `raw_text`
- `source`

Unknown bounds remain null.

## LogicalJob

Deduplicated user-facing job identity.

Fields:

- `id`
- `canonical_company`
- `canonical_title`
- `canonical_locations`
- `provider_posting_ids`
- `canonical_apply_destination`
- `dedupe_confidence`
- `first_seen_at`
- `last_seen_at`
- `active_state`
- `material_change_version`

A LogicalJob preserves all provider/source lineage.

## JobObservation

Snapshot of a LogicalJob at a point in time.

Fields:

- `logical_job_id`
- `observed_at`
- `active_sources`
- `best_current_posting_id`
- `material_fields_hash`
- `published_at_best_evidence`
- `freshness_confidence`
- `compensation_snapshot`
- `location/work arrangement snapshot`
- `active_state`

Used by watches to distinguish genuinely new/materially changed jobs from repeated observations.

## JobRequirement

Structured requirement/responsibility extracted from a posting.

Fields:

- `id`
- `type`
- `text/reference`
- `importance`: required / preferred / responsibility / contextual
- `canonical_capability`
- `minimum_years` when explicit
- `credential/license/authorization` when explicit
- `confidence`

## EvidenceMatch

Maps one JobRequirement or scoring dimension to profile evidence.

Fields:

- `requirement_id`
- `evidence_type`: direct / equivalent / transferable / gap / unknown
- `profile_evidence_refs`
- `strength`
- `reason`
- `confidence`

This is the core audit trail for matching.

## FitDimensionAssessment

Fields:

- `dimension`
- `weight`
- `score`
- `reason`
- `evidence_matches`
- `unknowns`
- `material_gaps`

## FitAssessment

Fields:

- `logical_job_id`
- `profile_version_id`
- `search_run_id`
- `scoring_model_version`
- `career_fit_score`
- `career_dimensions`
- `practical_fit_score`
- `practical_dimensions`
- `practical_coverage`
- `confidence_level`
- `confidence_score/internal`
- `hard_blockers`
- `material_gaps`
- `unknowns`
- `recommendation_bucket`
- `why_it_fits`
- `watch_outs`
- `transferable_reasoning`
- `created_at`

Recommendation buckets:

- excellent_match
- strong_match
- worth_a_look
- transferable_interesting
- filtered_out

## FilterDecision

Fields:

- `logical_job_id`
- `search_run_id`
- `filter_name`
- `outcome`: pass / fail / unknown / not_applicable
- `reason`
- `evidence`

A failed hard filter must be reconstructable later.

## SearchRun

Immutable search execution record.

Fields:

- `id`
- `mode`
- `started_at`
- `completed_at`
- `profile_version_id`
- `preferences_snapshot`
- `manual_query_intent`
- `generated_role_lanes`
- `scoring_model_version`
- `status`
- `source_coverage_report`
- `raw_posting_count`
- `deduped_count`
- `plausible_count`
- `deep_assessment_count`
- `surfaced_count`
- `result_ids/order`

## SourceCoverageReport

Fields:

- `providers_attempted`
- `boards_attempted`
- `boards_succeeded`
- `boards_failed`
- `new_boards_discovered`
- `failure_details`
- `raw_postings_by_provider`
- `coverage_started_at`
- `coverage_completed_at`

## SearchResult

Connects a search to a job/assessment.

Fields:

- `search_run_id`
- `logical_job_id`
- `fit_assessment_id/reference`
- `rank_within_bucket`
- `visible_bucket`
- `surfaced`
- `filtered_reason`

## Watch

Fields:

- `id`
- `name`
- `created_at`
- `enabled`
- `profile_version_id`
- `profile_policy`
- `preferences_snapshot`
- `manual_query_intent`
- `role_lanes`
- `match_style`
- `minimum_buckets/threshold`
- `source_scope`
- `last_run_at`
- `last_successful_run_at`

Default profile policy: pinned profile version.

## WatchJobState

Tracks one logical job relative to one watch.

Fields:

- `watch_id`
- `logical_job_id`
- `first_qualified_at`
- `last_qualified_at`
- `last_seen_material_change_version`
- `last_notified_material_change_version`
- `current_bucket`
- `dismissed`

Prevents duplicate alerts.

## ApplicationRecord

Fields:

- `id`
- `logical_job_id`
- `state`
- `saved_at`
- `applied_at`
- `state_updated_at`
- `notes`
- `source/apply_url_used`

States:

- saved
- applied
- interviewing
- rejected
- offer
- archived

Application history remains even if the posting closes.

## UserJobFeedback

Fields:

- `logical_job_id`
- `search_run_id`
- `action`
- `reason_category`
- `free_text_note`
- `created_at`

Actions may include:

- save
- apply
- not_interested
- mark_worth_a_look

Explicit user filters always outrank learned feedback.

## Versioning requirements

Version at minimum:

- profile builder/parser
- ProfileVersion
- scoring model
- provider adapter/normalizer when output semantics change materially

SearchRun records the relevant versions.

## Privacy/data minimization

Store only career/search information needed for product behavior.

Do not derive or store protected/sensitive characteristics for job matching.

Resume evidence should support professional qualification analysis only.

## Migration from bootstrap models

The existing bootstrap `JobPosting`, `SearchProfile`, `FitAssessment`, and `ApplicationRecord` are useful minimal placeholders.

When implementation resumes, evolve them incrementally rather than performing a giant untested rewrite.

Recommended implementation order:

1. add provenance/freshness fields to provider posting model
2. add SourceRegistryEntry
3. add resume/ProfileVersion/evidence models
4. add LogicalJob + dedupe lineage
5. add SearchPreferences/SearchRun/CoverageReport
6. expand scoring evidence models
7. add Watch/WatchJobState
8. connect ApplicationRecord to LogicalJob

Every step should have offline tests before the next large model expansion.

## Acceptance criteria

The V1 model is sufficient when the system can answer from stored data:

- Which resume/profile version produced this recommendation?
- Which sources contained this job?
- When was it first published vs last updated/retrieved?
- Why were duplicate postings merged?
- Which hard filters passed/failed?
- Which resume evidence supports each major requirement?
- Which gaps and unknowns remain?
- Why is the job in this recommendation bucket?
- Has this watch already notified the user about this logical job/version?
- Has the user already saved/applied/dismissed it?

If those questions cannot be answered without rerunning opaque reasoning, the model is not sufficiently auditable.
