# Job Data Source Baseline

## V1 source strategy

Use public or authorized structured job sources. Do not make hostile-site scraping a dependency.

Initial provider candidates:

1. Greenhouse public job-board data
2. Lever public postings
3. Ashby public job postings
4. SmartRecruiters public postings

Each provider gets an isolated adapter that emits the same normalized `JobPosting` model.

## Required normalized fields

- source name
- source job ID when available
- source URL / apply URL
- company
- title
- location text
- work arrangement when explicitly provided
- employment type when explicitly provided
- compensation range when explicitly provided
- description / requirements text
- posted / updated timestamps when available
- retrieval timestamp
- raw provenance sufficient for offline fixture testing

## Evidence rules

- Missing salary is unknown, not zero.
- Missing remote status is unknown, not onsite.
- Missing sponsorship data is unknown.
- Provider errors mean source unavailable/incomplete, not “no jobs.”
- Preserve original URL and source identity through deduplication.

## Deduplication

Prefer exact provider/company IDs where possible. Cross-provider duplicates may use normalized company + title + location + canonical URL / requisition identifiers. Do not merge low-confidence candidates merely because titles look similar.

## Expansion rule

Do not add a provider until the prior adapter has fixtures, normalization tests, pagination/error behavior, and provenance handling. LinkedIn and Indeed are not V1 dependencies.
