# PRODUCT_VISION.md — Automated Job Hunter

## One-sentence vision

Automated Job Hunter is a personal career agent that continuously finds relevant jobs, removes noise, explains fit, and helps the user decide what is actually worth applying to.

## The problem

Job search is fragmented across company career pages, ATS platforms, aggregators, recruiters, and stale duplicates. Search results often optimize for volume rather than fit, forcing the user to repeatedly scan the same jobs and re-evaluate the same criteria.

## Product promise

The user defines what a worthwhile job looks like once. The product searches supported sources, filters out obvious misses, ranks credible matches, explains its reasoning, and can keep watching for newly posted opportunities.

## V1 workflow

1. Candidate/search profile
2. Job discovery
3. Normalization and deduplication
4. Hard eligibility filtering
5. Fit scoring and explanation
6. Review queue: Strong Fit / Maybe / Skip
7. Save search as a watch
8. Basic application status tracking

## Candidate/search profile

The framework should support:

- target titles / role families
- seniority range
- location and commute radius
- remote / hybrid / onsite preferences
- employment type
- minimum compensation when known
- industries / company types
- required and preferred skills
- travel tolerance
- must-have criteria
- exclusion criteria

Candidate history and resume content may later enrich fit scoring, but the system should not require a perfect structured resume before it can search.

## Fit philosophy

A fit score is an explanation aid, not an oracle. It should be decomposable into dimensions such as role match, seniority/scope, experience/skills, industry/domain, location/work arrangement, compensation, and explicit requirements.

Hard disqualifiers should not be hidden inside a weighted score. Unknown data should remain unknown rather than being treated as a pass or fail.

## Result experience

Each result should make it easy to answer:

- What is the job?
- Why does it fit me?
- What might be a problem?
- What information is missing?
- How fresh is the posting?
- Where did it come from?
- What should I do next?

## V1 boundaries

Do not make V1 an auto-application bot. Do not depend on LinkedIn/Indeed scraping or bypass access controls. Do not invent missing facts. Do not optimize for application count.

The product should first become excellent at finding and prioritizing the right opportunities. Application assistance, resume tailoring, outreach, interview prep, and automation can be separate later phases.

## Reusable pattern

The architecture can reuse the same conceptual pattern proven elsewhere:

`Discover -> Normalize -> Filter -> Verify -> Rank -> Monitor -> Alert`

That architectural similarity does not make Job Hunter part of Universal Watcher. They are separate products.
