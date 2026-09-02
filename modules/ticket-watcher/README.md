# Ticket Watcher

Ticket Watcher continuously searches Ticketmaster for an event and alerts when an event's advertised price range satisfies your filters. It is structured so additional marketplaces can be added independently later.

## What Version 1 does

- Searches by event/artist/team name
- Filters by city/state or a true latitude radius, plus venue, date range, ticket quantity, per-ticket price, and order total
- Fuzzy-ranks event names so minor misspellings still work
- Rechecks continuously at a configurable interval
- Saves every matching result to `data/matches.jsonl`
- Sounds an alert and can open the best purchase page
- Supports a safe demo mode without an API key

Ticketmaster's Discovery API reports event-level price ranges, not exact live seat rows, seat adjacency, fees, or checkout totals. Those fields are represented in the shared model but are only enforced when a source supplies them. The console clearly labels estimated and unknown values.

The included `watch.json` is preconfigured for four Celtics vs. Lakers tickets within 30 miles of West Hills, with a maximum advertised price of $150 per ticket.

## Ticketmaster browser diagnostic

The Discovery API may omit event pricing. To test whether the public event page exposes usable listing data:

1. Double-click `SETUP_BROWSER.bat` once.
2. Double-click `RUN_TICKETMASTER_DIAGNOSTIC.bat`.
3. Leave the fresh browser open until it closes automatically after 75 seconds.
4. Do not sign in or enter payment information during the diagnostic.

The diagnostic saves a local report in `data/ticketmaster_diagnostic.json` and prints a privacy-conscious summary with query strings removed from captured endpoint URLs.

After the diagnostic succeeds, run `RUN_4_TICKET_TEST.bat`. It changes the event page from Ticketmaster's default quantity to the quantity in `watch.json`, captures the refreshed quick-picks inventory, and prints the cheapest fee-inclusive options. This is a controlled extraction test, not yet the continuous watcher.

## Live browser watcher

Version 1.9 uses the working Ticketmaster API only to locate the correct event, then reads the event's live four-ticket inventory using an offscreen browser. Ticketmaster does not serve the complete purchase interface to a true headless browser for this event, so the default Windows configuration renders Chromium far outside the visible desktop. The watcher confirms quantity from Ticketmaster's refreshed `qty=4` inventory request rather than requiring an offscreen label to be visibly rendered. Run `RUN_HEADLESS_TEST.bat` first. If it reports four-ticket offers, use `START_TICKET_WATCHER.bat` for continuous monitoring. The watcher stops, sounds an alert, and opens the Ticketmaster event page when an all-in offer satisfies `max_price_each`.

## StubHub source diagnostic

`RUN_STUBHUB_DIAGNOSTIC.bat` opens a fresh unsigned-in StubHub window for two minutes. Manually search for and open the target event while it captures listing-related JSON responses. It removes URL queries and common session/credential fields from the saved `data/stubhub_diagnostic.json` report. This is an independent source diagnostic and does not modify the working Ticketmaster watcher.

After event discovery, `RUN_STUBHUB_EVENT_DIAGNOSTIC.bat` opens the known StubHub event `161689730` directly and captures listing inventory for two minutes. If the page shows a ticket-quantity selector, set it to four. The saved report is `data/stubhub_event_diagnostic.json`.

## Windows setup

1. Install Python 3.11 or newer.
2. Open Command Prompt in this folder.
3. Run:

```bat
python -m venv .venv
.venv\Scripts\activate
copy .env.example .env
```

4. Create a free Ticketmaster developer key at https://developer.ticketmaster.com/
5. Open `.env` and replace `your_key_here` with that key.
6. Edit `watch.json` with your event and price preferences.
7. Start the watcher:

```bat
python app.py
```

After setup, you can also double-click `START_TICKET_WATCHER.bat`.

Try the built-in demo first:

```bat
python app.py --demo --once
```

Validate your configuration without contacting Ticketmaster:

```bat
python app.py --check-config
```

## Key price behavior

`max_price_each` is compared against the lowest advertised Ticketmaster event price. `max_order_total` uses that price multiplied by `quantity`. Because the public API does not expose checkout fees, `require_fees_included: true` rejects Ticketmaster Discovery results rather than pretending fees are known.

## Tests

```bat
python -m unittest discover -s tests -v
```
