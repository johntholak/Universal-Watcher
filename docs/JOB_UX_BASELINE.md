# Job UX Baseline

## Main workspace

The home screen should answer one question: **Which jobs are actually worth my time?**

Primary sections:

1. Search Profile
2. Strong Fits
3. Maybe
4. Saved / Watching
5. Applications

## Search profile

User-configurable fields:

- target roles
- seniority
- location / commute radius
- remote / hybrid / onsite
- minimum compensation when known
- employment type
- industries / company types
- must-have criteria
- exclusions
- travel tolerance

Primary action: **Find Jobs**
Secondary action after a search: **Keep Watching**

## Job card

Each card should show:

- title
- company
- location / work arrangement
- compensation if provided
- posting freshness
- source
- overall fit bucket
- concise “Why it fits” bullets
- concise “Watch-outs” bullets
- unknown / missing information
- direct application link

Primary actions:

- View Job
- Save
- Mark Applied
- Skip

## Fit buckets

### Strong Fit
Meets hard requirements and scores strongly across the important dimensions.

### Maybe
No known hard disqualifier, but one or more meaningful uncertainties or weaker dimensions remain.

### Skip
Known mismatch or user-dismissed result. Skip should feed dedupe/history so the same posting is not repeatedly resurfaced.

## Watch behavior

A watch saves the exact search profile and alerts only on new or materially changed qualifying postings. The user should not need to rebuild the criteria.

## Application tracking

Basic states:

- Saved
- Applied
- Interviewing
- Rejected
- Offer
- Archived

V1 tracking is user-controlled. Automatic application submission is not part of this baseline.
