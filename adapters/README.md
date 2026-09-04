# Universal Watcher adapters

Adapters keep proven module engines behind the shared control-plane
contracts. They should translate module-specific job records into
`WatchResult` and `Evidence` values without rewriting discovery or verification
logic.

## Family Deals

`family_deals.py` normalizes the existing Family Deals V5 job output. Verified
meal results become `match` results with official-source evidence. Missing
hours or capacity become `unavailable` results, and incomplete source coverage
stays visible through the shared `coverage` field. The adapter accepts an
injected job provider; it does not start the standalone Family Deals server or
make live requests yet.

Verify it from the repository root:

```text
python -m unittest discover -s adapters -p "test_*.py" -v
```

## Tickets

`tickets.py` normalizes existing Ticket Watcher `Match` records. A fully
specified offer can be marked verified; event-level prices, unknown fees, and
unconfirmed adjacency remain an unverified match with the source limitation
shown as the reason. In-progress, failed, and incomplete-source runs stay
separate from a truthful `no_match` result.

The adapter accepts an injected job provider. It does not start the
Ticketmaster watcher, contact Ticketmaster, or alter the working browser path.
