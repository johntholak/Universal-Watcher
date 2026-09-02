AMC SEAT WATCHER V44 — RECONSTRUCTED POST-CODEX BUILD

This package was reconstructed from the user's V44 Depth/Layering baseline
using the August 28, 2026 Codex handoff as the change specification.

It is NOT claimed to be a byte-for-byte copy of lost Git commit 7a19015.

RECONSTRUCTED CHANGES
- macOS project-local launch path and pinned requirements
- platform-aware browser user agent
- macOS afplay sound fallback
- AMC live select[name="date"] date selection instead of stale ?date= URLs
- progressive Next Best scanning
- closest-format ancestor classification
- standalone 70MM classification and matching
- Mac precision-trackpad scroll handling
- Universal CityWalk canonical route
- runtime theater cleanup / deduplication
- expanded nine-test offline regression contract

MAC SETUP
Easiest first run: double-click setup_and_run_v44.command.
It creates .venv, installs the pinned packages, installs Playwright Chromium,
runs the offline tests, and then starts Seat Watcher.

After setup, normal launches can use run_v44.command.

MAC TESTS
.venv/bin/python -m unittest discover -s tests -v

WINDOWS
The original run_v44.bat and setup_and_run_v44.bat are preserved.
A fresh Windows live regression is still recommended.

IMPORTANT
The AMC seat-response parsing and grouping code remains inherited from the
proven V44 baseline and should not be casually rewritten.
