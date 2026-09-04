# AMC reliability review — September 4, 2026

## Outcome

The configured catalog key began succeeding during this session, after the
14:15 UTC probe had returned 403/12005. Do not assume why authorization changed.
The approved catalog is now the preferred theater/showtime source. Seating
still uses AMC's normal website; no restricted seating API was called.

**Above 90% end-to-end reliability is NOT established.** Showtime discovery
matched 32/32 independently browser-observed showtimes in this limited sample.
Seat capture appeared successful initially, but comparison with the displayed
map exposed decoding and accessible-seat errors. Those initial seat outcomes
are not accepted as accuracy evidence. V44.7's final corrections pass offline
tests and need a fresh live run.

The user reports no administrator rights on this Windows machine. Browser
testing has stopped; do not ask them to disable protections or install with
administrator privileges. An AMC HTTP 429 was also observed during repeated
seat checks. The relation, if any, to the user's Windows message is unknown.

## Measured discovery evidence

Reference: AMC's displayed movie region, selected theater/date, format heading,
local time, and individual showtime links. Read-only inspection using the
browser skill; no seats were selected, held, or purchased. The engine used the
official catalog client, not a scraped duplicate as its reference.

All cases used The Odyssey and an all-day time window. CityWalk used IMAX 70MM;
Burbank and Century City used ANY, comparing each returned format separately.

| Theater | Date | Expected / found | Reference IDs |
|---|---|---|---|
| CityWalk | 2026-09-04 | 4 / 4 | 145681136, 145681137, 145676929, 145681138 |
| CityWalk | 2026-09-05 | 4 / 4 | 145681139, 145681128, 145676930, 145681129 |
| CityWalk | 2026-09-06 | 4 / 4 | 145681130, 145681131, 145681132, 145681133 |
| CityWalk | 2026-09-12 | 4 / 4 | 145681105, 145681106, 145676932, 145681107 |
| CityWalk | 2026-09-20 | 4 / 4 | 146826321, 146818555, 146818556, 146826322 |
| Burbank 16 | 2026-09-06 | 8 / 8 | 146754179, 146754141, 145901343, 146754140, 145901344, 146754522, 145901345, 146754367 |
| Century City 15 | 2026-09-06 | 4 / 4 | 146601306, 146601305, 146684745, 146684792 |

Formats: CityWalk IMAX 70MM; Burbank plain 70MM, IMAX, PRIME, LASER;
Century City IMAX and LASER. This is one film, three LA theaters and seven
theater/date combinations, not a random national sample or full NEXT BEST run.

Canonical reference pages:

- [CityWalk](https://www.amctheatres.com/movie-theatres/los-angeles/universal-cinema-an-amc-theatre/showtimes)
- [Burbank 16](https://www.amctheatres.com/movie-theatres/los-angeles/amc-burbank-16/showtimes)
- [Century City 15](https://www.amctheatres.com/movie-theatres/los-angeles/amc-century-city-15/showtimes)

The complete theater catalog returned **523 records across three pages**.
Filtering its official coordinates within ten miles of CityWalk returned seven:
CityWalk, Burbank 16, Burbank Town Center 8, Burbank Town Center 6, The Grove 14,
The Americana at Brand 18, Century City 15. All seven were present in AMC's
visible nearby-theater control. The control also listed farther theaters; it
does not prove full-radius recall independently. No national coverage percentage
is claimed. Existing map discovery has a capped Nominatim fallback and guessed
routes; it remains a labeled, unverified fallback, not authoritative coverage.

## Seat findings and V44.7 correction

1. Initial CityWalk September 4–6 checks captured payloads for all 12 showtimes.
   That proved data delivery, NOT accurate availability or valid no-match outcomes.
2. Burbank showtime `146754179` reported D1–D4. The displayed map identified D3
   and D4 as wheelchair spaces and D2 as a wheelchair companion position.
3. A focused comparison found five availability disagreements among 145 displayed
   seats in that Burbank map. For example, A12 was displayed as available but
   parsed as unavailable with coordinates inherited from a preceding gap.
4. The old fallback expression can span unnamed gap objects into the next seat.
   It also replaces type/visibility metadata with defaults. Regression tests
   reproduced both the gap association and escaped `seatName` alias failures.
5. A small structured-object decoding step now precedes the legacy fallback,
   preserving type, row, column, visibility, and aliases. All prior encodings and
   fallbacks remain. Adjacency, position extraction, ranking, time/movie/format
   filters, UI, Activity, and browser handoff implementations are not rewritten.
6. A separate verification step checks every displayed seat against the parsed
   inventory. Unnamed layout gaps are ignored. Missing seats, disagreeing states,
   conflicting physical-seat snapshots, or unavailable maps yield `unavailable`,
   never `captured_no_match`. Parsed raw counts are not treated as seat counts.
7. Wheelchair/companion positions are excluded from ordinary-seat group matching.
   No accessibility-specific preference exists yet; do not claim that use case
   is supported. The existing numeric minimum-row semantics are unchanged.
8. AMC returned HTTP 429 on a repeated Burbank seat request. Live batches were
   stopped. New 403/429 handling disables additional seat requests in that engine
   run, including queued checks once they acquire their slot. Already in-flight
   requests may finish. No automatic retry, proxy, credential or anti-bot bypass.
9. Candidate-response logs now omit query/fragment tokens. Captured browser data,
   queue tokens, and credentials are not committed.

Intermediate map-verification runs correctly rejected the old decoder's output.
The first structured-parser run then exposed repeated unnamed gap records; the
final offline-tested guard ignores those non-seat placeholders. **No final live
pass is claimed after that correction**, because browser testing is parked.

## Provider decision

- Use the approved [AMC Theatre/Showtime catalog](https://developers.amctheatres.com/)
  now that this key succeeds. Preserve official IDs and website URLs through
  normalization; do not reconstruct them from display names.
- AMC's [access policy](https://developers.amctheatres.com/GettingStarted/NewVendorRequest)
  treats seating/ecommerce approval separately. A working catalog key does not
  grant seating permission. Keep the normal browser path and truthful failures.
- [MovieGlu cinemaShowTimes](https://developer.movieglu.com/v2/api-index/cinemashowtimes/)
  is a possible licensed alternate for theater/date discovery. Its documented
  format categories do not establish exact IMAX 70MM separation. Its cinema-day
  boundary is 03:00–02:59, which would need explicit normalization.
  [Purchase links](https://developer.movieglu.com/v2/api-index/purchaseconfirmation/)
  do not supply seat selection. No account, purchase, or integration was created;
  do not replace a now-working AMC catalog with an untested provider.

## Acceptance needed before claiming >90%

Use a predeclared reference set, including successes, published empty dates,
near-horizon dates, multiple films/formats, and sold-out/near-full/available maps.
Target at least 100 scheduled checks over several sessions, three or more theaters
and seven or more dates. Include the original CityWalk NEXT BEST case on Mac.

Report separate denominators; never drop unavailable checks or average a weak
stage into a stronger one:

- Theater recall: correct in-radius AMC identities / independent reference set.
- Showtime recall and precision: exact theater/date/time/format/ID matches versus
  expected and returned sets. Duplicate/wrong-date/wrong-format results fail.
- Seat verification success: complete, agreeing inventory / all scheduled checks.
- Group correctness: ordinary, available, contiguous requested seats, correct
  minimum row and purchase destination; inspect every claimed group initially.
- End-to-end acceptable checks / all scheduled checks must itself exceed 90%.
- Zero technical failures described as verified no-match. A reported unavailable
  is truthful, but still not a successful inventory check.

These are empirical acceptance thresholds, not a statistical guarantee. Also
test window boundaries, midnight/cinema-day semantics, cancellation, full NEXT
BEST exhaustion and Mac scrolling/Activity/handoff. Do not require a fresh
Windows administrator setup to perform this acceptance.
