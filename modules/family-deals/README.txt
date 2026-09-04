HUNT FAMILY DEALS V5.0 - FAST FILTERS + SEMANTIC VERIFIER

CURRENT PLATFORM
macOS is the active development platform. Windows launcher is retained.

RUN ON MAC
1. Extract this entire folder.
2. Double-click start_hunt.command.
3. If macOS blocks the first launch: System Settings > Privacy & Security > Open Anyway.
4. Leave Terminal open while HUNT is running.
5. Press Control+C in Terminal when finished.

You can also launch from Terminal with:
python3 server.py

RUN ON WINDOWS
Double-click start_hunt.bat.

PORTS
HUNT starts at 127.0.0.1:8765 when available and safely tries 8766-8774 if needed.

WHAT V5.0 ADDS
1. Restaurant type filters:
   - Any
   - Independent + local
   - Independent only
   - Chains only

2. Cuisine multi-select:
   - Pizza / Italian
   - Mexican / Latin
   - Asian
   - American
   - BBQ
   - Mediterranean
   - Indian
   - Seafood
   - Other / unknown

3. Chain classification is evidence-based and conservative.
   - Known multi-location brands are tagged Chain.
   - 6+ same-brand/name locations in the radius are tagged Chain.
   - 2-5 same-brand/name locations are tagged Local group unless already known as a chain.
   - A single listing with no structured brand markers is tagged Independent.
   - Ambiguous cases stay Unknown rather than being guessed.
   - "Independent + local" includes Unknown so HUNT does not silently hide a potentially local restaurant.

4. Birthday/event-package rejection.
   - Party rooms, birthday packages, play points, arcade/game packages, etc. are not family dinner deals.
   - A food "party pack" may still qualify when clear take-home/dinner evidence exists.

SPEED CHANGES
The expensive stage is official-site verification, not the radius scan. V5.0 speeds that stage up without reintroducing loose matching:

- Restaurant type and cuisine filters are applied AFTER full-radius discovery but BEFORE website crawling.
  Full geographic coverage is preserved while irrelevant restaurants never enter the expensive verifier.
- Structured Wikidata source resolution runs in parallel instead of mostly serially.
- Up to 24 independent official sources can be checked concurrently (V4.1 used 12).
- HUNT checks a maximum of 3 highly relevant pages per source (V4.1 used 4).
- Adaptive crawl: when a page already proves a qualifying family meal, HUNT stops crawling redundant pages for that source.
- Official-source verification results are cached for 6 hours in ~/.hunt_cache.
- Wikidata homepage resolutions are cached for 7 days.
- A recent full-radius restaurant scan is cached in the browser for 30 minutes.
- Source evidence cache is independent of the dollar budget, so changing $50 to $60 can reuse the same recent source evidence for the same party size.

FIRST RUN VS REPEAT RUN
The first broad "Any / Any cuisine" search can still take time because hundreds of unrelated websites genuinely have to be contacted. Repeat searches, filter changes, and budget changes should become much faster because HUNT can reuse recent work.

FAMILY-SIZE RULE
Family-size means serves 4 through 10. The selected party size is a minimum need, not an exact match. A family of 4 may therefore use a meal that serves 4, 5, 6, 8, or 10.

STRICT VERIFICATION
HUNT rejects unrelated fees, discounts, coupons, side dishes, FAQ prices, uncertain/starting prices, unavailable promos, event packages, and other dollar amounts that are not proven meal totals.

TESTS
Run:
python3 -m unittest discover -s tests -v

Current suite: 19 tests, including conservative dinner-hours parsing.
