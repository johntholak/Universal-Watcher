# Universal Watcher Watch UX Baseline

Status: Approved product direction
Date: September 4, 2026

## Core rule

A Watch is the saved continuation of a search the user already configured. Do not make the user rebuild the criteria when converting a search into a Watch.

Search first. If the desired result is not available, the user can choose to keep watching using the exact same criteria.

## Active Watch view

Show only useful user-facing information:

- search/watch name
- current state (Watching, Found, Paused, Stopped)
- concise summary of the saved criteria
- last checked time
- meaningful coverage/status information when available
- whether a qualifying result currently exists
- Check Now
- Edit Search
- Stop/Pause Watch

Avoid exposing technical logs as the primary experience.

## When a match is found

Prominently show the qualifying result and why it meets the saved criteria.

For Movies this can include theater, showtime, seats, format, row requirement, time requirement, and direct purchase/view action when available.

Primary actions after a match:

- View / act on result
- Keep Watching
- End Watch

## Shared product behavior

A module's normal search remains the primary way to configure criteria. Watching is an optional continuation of that search, not a separate simplified configuration system.
