# Seat Watcher V44 Reconstructed Post-Codex Build

This package was created on September 1, 2026 from the user's uploaded
`Seat_Watcher_V44_DEPTH_LAYERING` baseline.

The actual source tree from Git commit `7a19015` was not recoverable from the
available Library. A detailed August 28 Codex handoff was available and was
used as the implementation specification.

Therefore this package should be treated as:

**a careful reconstruction of the documented post-Codex state, not the exact
original Git commit.**

## Reconstructed functional changes

- macOS requirements and launcher
- platform-specific Chrome user-agent token
- macOS `afplay` alert fallback
- AMC `select[name="date"]` navigation with stale-content rejection
- progressive one-day-at-a-time NEXT BEST scanning
- 3-empty-days / 14-initial-days stopping contract
- nearest relevant format ancestor
- standalone 70MM detection/matching
- Universal CityWalk canonical URL handling
- runtime theater cleanup / deduplication
- Mac wheel/touchpad scroll handling
- nine offline regression tests

## Preserved

The sensitive V44 seat response interception, decoding, seat-position parsing,
adjacent-seat grouping, ranking, and browser handoff code were left in place
rather than rewritten.

## Verification limit

Offline syntax and helper regression tests can be run in this environment.
A live AMC end-to-end test must still be performed on the user's Mac because
this build environment does not have the user's browser/runtime setup or live
internet access.
