# Automated Job Hunter

Standalone product bootstrap. This branch is a staging home only; the product is intentionally separate from Universal Watcher and should become its own repository when active development resumes.

## Product promise

Find jobs that are genuinely worth applying to, explain why they fit, keep watching for better ones, and give the user a clean decision queue instead of another noisy job board.

## V1 shape

1. Define a candidate/search profile.
2. Discover jobs from supported public/authorized ATS sources.
3. Normalize and deduplicate postings.
4. Apply hard filters before scoring.
5. Score fit with visible reasons and unknowns.
6. Sort into Strong Fit, Maybe, and Skip.
7. Save searches as watches for newly posted qualifying jobs.

V1 does not auto-apply, scrape blocked sites, or pretend unknown compensation/location/requirements are known.

## Start here

Read in order:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`
5. `docs/JOB_UX_BASELINE.md`
6. `docs/JOB_DATA_SOURCE_BASELINE.md`
7. `docs/JOB_MATCHING_BASELINE.md`

Current state: framework/scaffold only, deliberately shelved after this checkpoint.
