# ChatGPT Project Setup — Automated Job Hunter

Date: September 8, 2026

## Project identity

This ChatGPT Project is for **Automated Job Hunter**, a standalone product. It is not a Universal Watcher module.

## Source of truth

Until a dedicated repository is created, the authoritative bootstrap lives at:

- Repository: `johntholak/Universal-Watcher`
- Branch: `job-hunter-bootstrap`
- Bootstrap commit: `d5aec29e08181ec013a85fc841b55ea71e2b6df2`

Do not treat Universal Watcher `main` as the Job Hunter product source. The branch exists only as a staging home until the project gets its own repository.

## Mandatory startup sequence for future sessions

Read completely, in order:

1. `AGENTS.md`
2. `PRODUCT_VISION.md`
3. `PROJECT_STATUS.md`
4. `RUNBOOK.md`
5. `docs/JOB_UX_BASELINE.md`
6. `docs/JOB_DATA_SOURCE_BASELINE.md`
7. `docs/JOB_MATCHING_BASELINE.md`
8. this file

Then inspect the current branch/repository state before changing anything.

## Product promise

Find jobs that are genuinely worth applying to, explain why they fit, remove noise and duplicates, and give the user a clean decision queue instead of another high-volume job board.

## Locked V1 direction

- Candidate/search profile
- Multi-source job discovery from supported/public/authorized sources
- Normalization and deduplication
- Hard eligibility filtering before fit scoring
- Explainable fit scoring with visible reasons and unknowns
- Review queue: Strong Fit / Maybe / Skip
- Saved searches that can later become watches for newly posted qualifying roles
- Basic application-status tracking

## V1 boundaries

Do not make V1 an auto-application bot.
Do not depend on LinkedIn or Indeed scraping.
Do not bypass access controls.
Do not invent missing compensation, location, seniority, or requirements.
Do not optimize for application count.

## Initial provider evaluation order

1. Greenhouse
2. Lever
3. Ashby
4. SmartRecruiters

Add one provider at a time and prove normalization/deduplication/fit behavior with offline fixtures before expanding.

## Current state

Framework/scaffold exists but is intentionally shelved. No live provider is connected. No application automation exists. Starter tests were written but have not yet been run in a normal development environment.

## Resume point

When active development resumes:

1. Create a dedicated `Automated-Job-Hunter` repository from this bootstrap.
2. Run the existing scaffold tests.
3. Implement one Greenhouse adapter using offline fixtures.
4. Validate normalization, hard filters, deduplication, and explainable fit output.
5. Only then add a second provider.

## Relationship to Universal Watcher

The products may reuse architectural ideas such as:

`Discover -> Normalize -> Filter -> Verify -> Rank -> Monitor -> Alert`

That shared pattern does not merge the products. Universal Watcher and Automated Job Hunter should remain independently scoped, independently documented, and independently executable.
