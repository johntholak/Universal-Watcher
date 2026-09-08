# AGENTS.md — Automated Job Hunter

## Startup

Before work, read `AGENTS.md`, `PRODUCT_VISION.md`, `PROJECT_STATUS.md`, and `RUNBOOK.md`, then the three baselines in `docs/`.

## Product rule

Automated Job Hunter is a standalone product, not a Universal Watcher module.

## Core principles

- Prioritize relevant jobs over large result counts.
- Use hard filters before fit scoring.
- Unknown is not the same as no.
- Explain why a job was scored the way it was.
- Preserve source URL, source name, retrieval time, and evidence used for every result.
- Deduplicate the same role across ATS mirrors without losing provenance.
- Prefer public/authorized structured sources and official company career data.
- Do not make bypassing anti-bot controls a requirement.
- Do not auto-apply, submit forms, or contact employers without explicit user authorization in a future approved phase.
- Do not fabricate salary, remote status, seniority, sponsorship, or qualifications.

## V1 scope

V1 is discovery, normalization, filtering, fit scoring, decision queue, saved searches/watches, and basic application tracking.

Out of scope for V1: automatic applications, resume rewriting at scale, recruiter outreach, interview automation, LinkedIn scraping, and stealth browser automation.

## Architecture direction

`Sources -> Normalize -> Deduplicate -> Hard Filter -> Fit Score -> Explain -> Queue -> Watch`

Provider-specific logic belongs in adapters. Shared code should consume normalized job records.

## Engineering discipline

Make narrow changes, add offline fixtures/tests for provider parsing and scoring, keep credentials out of Git, preserve reproducibility, and update `PROJECT_STATUS.md` whenever behavior or priorities change.
