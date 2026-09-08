# Job Seed Employer Universe V1

## Purpose

The Source Registry needs a meaningful day-one employer universe before dynamic discovery has had time to grow coverage.

The seed universe is not a permanent whitelist and must not become a hidden limitation on search. It is a bootstrap layer that gives Job Hunter immediate breadth while the registry expands through live searches, official-career-page discovery, result-driven discovery, and scheduled coverage sweeps.

The seed must be personalized from the user's resume/profile and search preferences rather than being one generic list for every user.

## Locked product rule

The seed universe should maximize the chance that the user's first real search finds worthwhile opportunities without requiring a mature registry.

Therefore the bootstrap should intentionally over-cover plausible employer categories and role families, then let the normal matching engine decide which individual postings are worthwhile.

Do not pre-filter employers so aggressively that the seed itself becomes a source of false negatives.

## Two-layer seed model

### Layer A — Global provider bootstrap

Maintain a reusable base of verified public ATS boards across supported providers.

This layer is not user-specific and exists to accelerate every new user's first search.

Useful global coverage dimensions include:

- major employers using Greenhouse, Lever, Ashby, and later SmartRecruiters
- high-volume employers
- employers with broad remote hiring
- employers with meaningful US hiring volume
- employers across common professional functions
- employers repeatedly discovered through prior searches

This global registry should grow over time and should not be recreated per user.

### Layer B — User-specific priority universe

When a resume/profile is created, derive a prioritized employer universe using:

- direct role families
- adjacent role families
- transferable role families
- industries/domains in the resume
- location/radius preferences
- remote/hybrid/onsite preferences
- seniority band
- compensation preferences when known
- company-type preferences/exclusions
- explicitly named target companies
- previously saved/applied/interviewed employers when available

This layer controls refresh/discovery priority, not whether a company is allowed to appear.

## Initial user-specific coverage lanes for this bootstrap

The current Job Hunter bootstrap should intentionally cover employers likely to contain roles aligned with the preserved career profile in `CHATGPT_PROJECT_SEED.md`.

### Lane 1 — Events and experiential leadership

Employer types:

- companies with large internal event organizations
- experiential marketing agencies
- brand experience agencies
- conference/event production companies
- corporate event management companies
- large trade-show/conference organizers
- event strategy/production consultancies

Representative role families:

- Director / Head / VP of Events
- Event Operations Director
- Experiential Marketing Director
- Event Strategy leadership
- Senior Event Manager
- Global Events leadership

### Lane 2 — Media, entertainment, streaming, sports, and live experiences

Employer types:

- studios
- streaming/media platforms
- television/media networks
- music/live entertainment organizations
- sports/venue organizations
- gaming/interactive entertainment companies
- consumer entertainment brands

Why this lane matters:

These companies frequently combine events, premieres, launches, experiential work, technical production, talent/executive coordination, sponsorship, partner events, and large-scale operations.

### Lane 3 — Technology companies with major events/field-marketing organizations

Employer types:

- enterprise software/SaaS
- cloud/infrastructure
- cybersecurity
- developer platforms
- fintech
- AI/technology companies
- high-growth B2B technology companies

Relevant functions:

- global events
- field marketing
- customer events
- partner events
- experiential/brand programs
- executive events
- user conferences
- program/operations leadership

This lane should not require prior SaaS title history when the underlying responsibilities are strongly equivalent.

### Lane 4 — Event technology, AV, broadcast, production, and managed services

Employer types:

- event-technology companies
- AV integrators
- hotel/convention AV providers
- broadcast/production technology companies
- live-production vendors
- managed technology/service providers
- registration/event-platform companies

Relevant roles:

- Site Manager / Managed Technology
- Director of Event Technology
- Technical Operations leadership
- Production Operations
- Technical Program/Project Management
- venue/hotel technology leadership

### Lane 5 — Hospitality, venues, convention, and destination organizations

Employer types:

- hotel groups
- convention centers
- venue operators
- destination/event organizations
- large conference properties
- hospitality technology/service organizations

Relevant strengths:

- hotel AV/event-technology operations
- staffing
- client service
- event sales/operations
- vendor coordination
- technical delivery
- onsite management

### Lane 6 — Brand marketing and field activation organizations

Employer types:

- automotive
- consumer technology
- consumer packaged goods
- retail
- lifestyle brands
- financial services
- healthcare/biotech where event scope fits
- other companies with significant field/experiential programs

Relevant roles:

- experiential marketing
- field marketing operations
- brand activation
- sponsorship/events
- customer/partner experiences
- launch/program management

Industry mismatch alone must not exclude a company from this lane.

### Lane 7 — Program, project, and operations transfer opportunities

Employer types:

- companies with complex field operations
- companies running multi-site launches/deployments
- hardware/robotics/mobility organizations
- operationally intensive technology companies
- companies with cross-functional program offices
- companies needing vendor/logistics-heavy program leadership

Relevant roles may include:

- Senior Program Manager
- Technical Program Manager where technical depth is credible
- Operations Director
- Field Operations Director
- Program Operations
- Launch Operations
- Project/Program leadership

The matcher must evaluate responsibility/scope rather than assuming every generic Program Manager role is relevant.

### Lane 8 — Select Chief of Staff / business operations adjacency

Do not broadly seed every Chief of Staff role.

Prioritize organizations/functions where the role is adjacent to:

- marketing
- events/experiences
- operations
- go-to-market execution
- field programs
- executive program management

The source universe can include these employers, but role-level matching must remain conservative because Chief of Staff titles vary dramatically.

## Geography lanes

### Local / Southern California priority

The preserved profile is based in West Hills, California and has considered local and remote opportunities.

For the bootstrap user, prioritize discovery and refresh for employers with meaningful hiring presence across:

- West Los Angeles / San Fernando Valley
- Los Angeles
- Burbank / Glendale
- Santa Monica / Playa Vista / Culver City
- Hollywood / Universal City
- El Segundo / South Bay
- Pasadena / greater Los Angeles
- other Southern California locations that fall within explicit user-selected radius rules

Do not convert this priority geography into an implicit hard radius. The search controls remain authoritative.

### Remote US priority

Maintain strong coverage of employers that publish US-remote roles relevant to direct, adjacent, or transferable role lanes.

Remote coverage is especially important because the user's search may explicitly enable remote roles even when local radius is narrow.

## Seed priority tiers

### Tier 1 — Must cover immediately

Sources strongly connected to:

- explicit target companies
- direct resume role families
- prior application/interview targets when user-provided
- local major employers in relevant functions
- high-probability remote employers in relevant functions

These should be verified/refreshed first.

### Tier 2 — Strong adjacency

Sources likely to contain:

- experiential/field marketing roles
- partner/customer event roles
- technical event/production roles
- senior program/operations roles with strong responsibility overlap

### Tier 3 — Transferable exploration

Sources that may produce credible but less obvious transitions.

These are useful for `Include Transferable Roles` searches but should not consume the same refresh priority as Tier 1 unless they repeatedly produce good matches.

## Provisional bootstrap size

Do not start with only a few dozen hand-picked employers.

A practical initial goal is:

- approximately 250 verified employers/sources in the first useful seed
- diversified across the lanes above rather than concentrated in one industry
- expansion toward 1,000+ verified employers/sources through discovery as the product matures

These are coverage goals, not product limits or promises of exhaustive coverage.

A smaller seed is acceptable during early adapter testing, but production-style validation should not be performed against a tiny employer universe.

## Employer selection scoring

The seed-builder can assign an internal employer-priority score using evidence such as:

- direct-role-family likelihood
- adjacent-role-family likelihood
- transferable-role-family likelihood
- local geographic presence
- remote hiring presence
- historical relevant posting frequency
- company size/hiring volume
- prior user interest
- prior high-quality matches
- source freshness/reliability

This priority score controls registry discovery/refresh effort only.

It must never become a hidden job-fit score.

## Named-company handling

If the user explicitly names a company:

1. add it to the user-specific priority universe
2. discover/verify all supported public career sources for that employer
3. refresh those sources during relevant searches
4. do not assume the company uses only one board/provider

Likewise, employers previously saved/applied/interviewed may receive higher discovery priority if the user chooses to retain that history.

## Avoiding seed bias

A personalized seed creates useful focus but can also reinforce old career patterns.

Protect against this by:

- keeping adjacent/transferable lanes
- maintaining global registry coverage outside the user's obvious industries
- dynamically discovering employers from actual matching roles
- tracking manually found missed jobs
- adding source-level false negatives to registry regression tests
- allowing natural-language searches to trigger employer discovery outside the seed

The system should not conclude `this company is irrelevant to you` merely because it was not in the initial seed.

## Seed creation workflow

When ProfileVersion is ready:

1. read direct/adjacent/transferable role families
2. read geography/work-arrangement preferences
3. generate employer-category search lanes
4. merge matching entries already in the global Source Registry
5. prioritize relevant known boards
6. discover missing high-value companies/boards
7. verify source ownership
8. populate/refresh the local corpus
9. record seed-generation version and reasons

The seed universe should be reproducible from the same profile/preferences/version.

## Seed provenance

For each user-prioritized employer, preserve why it was prioritized.

Example reason types:

- explicit_user_target
- direct_role_lane
- adjacent_role_lane
- transferable_role_lane
- local_market_priority
- remote_market_priority
- historical_positive_feedback
- validation_miss_recovery
- dynamic_discovery

This makes the coverage strategy inspectable.

## Validation requirements

Before trusting the seed strategy:

1. verify representation across every major role lane
2. verify both local and remote coverage when enabled
3. ensure no single industry dominates the seed without evidence
4. run broad retrieval against the seed and inspect relevant-job diversity
5. compare manually found worthwhile jobs against seed/registry coverage
6. add missed employers/sources to the discovery regression suite

## Core product rule

The seed exists to make Job Hunter useful on day one, not to define the boundaries of the user's career.

The intended behavior is:

> Start with a broad, resume-informed employer universe, then continuously expand it whenever the market or the user's interests reveal something new.
