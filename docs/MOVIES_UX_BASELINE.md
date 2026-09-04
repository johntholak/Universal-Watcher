# Movies UX Baseline

**Status:** Locked starting direction for Universal Watcher Movies
**Date:** September 4, 2026

## Purpose

Universal Watcher Movies must preserve the current Seat Watcher feature set and improve only how those capabilities are organized and presented. Integrating Movies into the Universal Watcher web app must not simplify away working Seat Watcher behavior.

## Core product rule

**Preserve functionality first. Improve presentation second.**

Universal Watcher should wrap the proven Seat Watcher workflow in a clearer web interface. It should not replace that workflow with a generic free-text watch creator or a reduced movie form.

## Movies workflow

The agreed starting layout is:

1. **Choose the Movie**
   - Type/search for a title.
   - Find movies playing nearby.
   - Select from discovered movie options.

2. **Choose Where**
   - Enter city, ZIP code, or address.
   - Use current location where available.
   - Set search radius.
   - Find nearby theaters.
   - Select/deselect individual theaters.
   - Preserve full theater discovery behavior rather than forcing the user to know a theater in advance.

3. **Choose When**
   - Next Best.
   - Specific Date.
   - Date Range.
   - Earliest showtime.
   - Latest showtime.

4. **Seat / Showing Preferences**
   - Seats together.
   - Minimum row.
   - Format selection, including currently supported Seat Watcher formats.
   - Existing ranking priorities such as row, time, distance, and center preference.
   - Existing advanced options remain available rather than being removed for simplicity.

5. **Search for Seats**
   - Run the current Seat Watcher-style discovery and seat search.
   - Show useful matching results and truthful unavailable/no-match states.

6. **Optionally Keep Watching**
   - A search can later be saved/continued as a Watch.
   - Watching is an extension of the search, not a replacement for the search/discovery workflow.

## Functional baseline to preserve

The Movies web experience must retain the currently developed Seat Watcher capabilities, including at minimum:

- movie discovery/search
- theater discovery/search
- multiple theater selection
- location and radius filtering
- fuzzy movie matching where currently supported
- format filtering
- Next Best, Specific Date, and Date Range modes
- earliest/latest showtime filtering
- seats-together requirement
- minimum-row requirement
- adjacent-seat grouping
- ranking/priorities already implemented
- seat inventory checking
- useful-match browser handoff behavior
- truthful distinction between no match and unavailable/incomplete provider data

Do not remove a capability merely to make the Universal Watcher form look simpler.

## Presentation direction

The approved visual starting point is a polished Universal Watcher Movies workspace with:

- clear numbered sections for Movie, Where, When, Seat Preferences, and More Options
- a visible theater-selection list after discovery
- a concise search summary
- one primary **Search for Seats** action
- an optional **Save as Watch / Keep Watching** action
- results shown below the search criteria with theater, format, showtime, seat details, and why the result qualifies
- stronger hierarchy, spacing, depth, and layering than the current Seat Watcher desktop UI

The visual design can evolve later. The functionality above is the constraint.

## Home-page relationship

Universal Watcher Home should show the currently supported modules clearly. Movies should be entered through a visible Movies option rather than pretending Universal Watcher can accept an unlimited open-ended request from the start.

Once inside Movies, the user should be helped to discover the movie and theaters instead of being expected to already know exactly what they want.

## Implementation guardrail

Before any Movies web-shell implementation or refactor:

1. Compare the proposed UI against this document and the current Seat Watcher controls.
2. Confirm that no existing user-facing capability is being dropped.
3. Keep the proven Seat Watcher engine intact until an adapter/boundary can call it safely.
4. Treat UX work as reorganization and presentation unless a deliberate functional change is separately approved.

This document is the current UX baseline for Movies until explicitly revised.