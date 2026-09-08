# Job Hunter Validation + Calibration V1

## Purpose

Job Hunter should not earn the right to hide large numbers of jobs merely because its scoring logic looks reasonable on paper.

It must be validated against human judgments on real job postings.

The primary failure to prevent is a false negative: a job the user would seriously consider applying to that Job Hunter failed to surface.

## Human labels

For calibration, the user reviews real jobs without seeing Job Hunter's final recommendation first when practical.

Primary labels:

- `Definitely Apply`
- `Probably Apply`
- `Maybe`
- `No`

Optional reason tags:

- excellent role fit
- strong transferable fit
- wrong seniority
- wrong function
- compensation
- location/work arrangement
- industry/domain
- required qualification gap
- company preference
- travel/schedule
- other

## Primary metric

### Worthwhile-job recall

Treat `Definitely Apply` + `Probably Apply` as worthwhile jobs.

Metric:

`worthwhile jobs surfaced / total worthwhile jobs reviewed`

Provisional V1 target before aggressive hiding: **95% or better** on a representative held-out validation set.

A miss in `Definitely Apply` is more serious than a miss in `Probably Apply` and should be reviewed individually.

## Secondary metrics

### Excellent/Strong precision

Of jobs classified as Excellent or Strong, how many does the user consider Definitely/Probably Apply?

This measures ranking usefulness but is secondary to recall during early V1.

### Worth-a-Look burden

How many low-value jobs are being preserved merely to protect recall?

The goal is not zero extra jobs; the goal is a manageable review queue without sacrificing strong opportunities.

### False hard-filter rate

Any job the user would consider worthwhile that was removed by a hard filter must be treated as a serious defect unless the user explicitly configured that filter and accepts the outcome.

### Bucket ordering quality

Pairwise question:

> When comparing two jobs, does the user generally prefer the one Job Hunter ranked higher?

Useful for tuning ranking inside buckets.

### Explanation agreement

Do `Why it fits`, `Watch-outs`, `Gaps`, and `Unknowns` match the user's understanding of their background and the posting?

### Coverage miss rate

Separate matching misses from source-discovery misses.

For any worthwhile job not surfaced, classify the root cause:

- source never discovered
- posting retrieved but broad screening dropped it
- hard filter removed it
- deep matcher underrated it
- practical-fit handling suppressed it
- dedupe incorrectly merged/removed it
- stale/closed verification mistake
- UI/result threshold hid it

This distinction is essential because scoring improvements cannot fix jobs the source layer never saw.

## Calibration dataset design

Do not build a validation set made only of obvious direct-title jobs.

Include a representative mix:

- direct role matches
- adjacent titles
- transferable opportunities
- title looks good but responsibilities do not fit
- title looks unfamiliar but responsibilities fit strongly
- high salary but weak career fit
- strong career fit with salary unknown
- remote/hybrid/onsite variants
- slightly senior stretch
- slightly junior role
- industry-switch opportunities
- real required-credential blockers
- preferred-qualification gaps
- sparse postings
- detailed postings
- stale/duplicate/reposted jobs

## Calibration phases

### Phase 1: Small development set

Use approximately 30-50 real jobs to expose obvious model mistakes quickly.

The goal is debugging, not measuring final quality.

### Phase 2: Calibration set

Use a broader reviewed set to tune:

- evidence interpretation
- score dimension weights
- recommendation thresholds
- broad screening rules
- transferable-role behavior

Do not report this set as unbiased final performance after tuning on it.

### Phase 3: Held-out validation set

Use jobs not used to tune the system.

This set determines whether the 95% worthwhile-job recall target is actually met.

### Phase 4: Ongoing production review

Continue sampling surfaced and filtered jobs after launch.

Watch especially for:

- worthwhile jobs discovered only after user finds them elsewhere
- repeated Not Interested reasons
- high-scoring jobs never saved/applied
- low-confidence jobs frequently upgraded by the user

## Review interface

A simple calibration UI should support:

- job title/company
- job description/direct link
- user label
- optional reason tags
- optional note

During blind calibration, hide Job Hunter's bucket/score until after the user labels the job.

Then reveal:

- Job Hunter bucket
- Career Fit
- Practical Fit
- Confidence
- evidence explanation

This avoids anchoring the human label to the model's answer.

## Miss review

Every missed `Definitely Apply` or `Probably Apply` job should generate a structured miss record:

- job id
- human label
- model bucket/filter outcome
- root-cause stage
- model explanation
- corrected expected behavior
- whether the fix is generalizable
- regression test added

Do not patch the system with one-off title rules unless the behavior represents a general pattern.

## Regression suite

Promote representative calibration mistakes into deterministic regression fixtures where possible.

Examples:

- equivalent responsibility under different title must remain eligible
- missing salary must not fail a minimum-pay search unless strict known-salary policy is enabled
- preferred degree must not become required
- explicit required license known missing must cap/filter appropriately
- provider failure must not become no jobs
- same requisition mirrored on two sources must not appear twice
- recently updated old posting must not automatically become `posted in last 24 hours`

## Threshold tuning

Initial scoring thresholds are guide rails, not sacred values.

Tune thresholds only with evidence from reviewed jobs.

Changes should record:

- scoring model version
- old threshold/weight
- new threshold/weight
- reason
- effect on calibration recall/precision

Do not optimize only for a prettier smaller result list.

## Match Style validation

Validate each user mode separately.

### Best Matches Only

Primary expectation: very high precision among shown jobs while retaining access to hidden Worth-a-Look results.

### Best + Good Stretches

Primary expectation: strong worthwhile-job recall across direct and adjacent roles.

### Include Transferable Roles

Primary expectation: improved recall of credible career pivots without flooding the queue with speculative unrelated work.

## Source coverage validation

Maintain a separate set of known real openings from supported ATS providers.

Measure:

- board discovery rate
- posting retrieval rate
- freshness correctness
- detail enrichment correctness
- duplicate handling

A perfect ranker with poor board discovery must fail V1 acceptance.

## V1 acceptance gate

Do not enable aggressive automatic hiding by default until:

1. held-out worthwhile-job recall is at least 95%
2. no systemic false hard-filter pattern remains
3. source-coverage misses are measured separately and are within an accepted range for supported sources
4. explanations reliably identify major strengths/gaps/unknowns
5. transferable-role tests show useful expansion without uncontrolled noise
6. duplicate/freshness regressions pass

If recall is below target, widen surfacing rather than hiding more jobs.

## Product rule

When ranking quality is uncertain, show the user one extra plausible job rather than silently discard a job they may have wanted.
