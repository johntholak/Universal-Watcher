# Universal Watcher Home UX Baseline

Status: Approved product direction
Date: September 4, 2026

## V1 home purpose

The home screen should make the currently working product capabilities obvious without implying unsupported capabilities.

## Active user-facing modules

V1 Home should show only modules that are active and useful:

- Movies
- Family Deals

Do not show shelved, blocked, unfinished, or placeholder modules merely to make the product appear larger.

Tickets is shelved because stable provider access is not currently viable and should be hidden from user-facing Universal Watcher navigation/module choices until that changes.

## Home hierarchy

1. Product identity / short promise
2. Large Movies and Family Deals entry cards
3. Active Watches, only when watches exist
4. Recent Results, only when results exist

No generic open-ended search box is required for V1. The product should first show users what Universal Watcher can actually do.

## Module cards

### Movies

Purpose: Find movies, theaters, showtimes, formats, and seats that meet the user's criteria.

Primary action: Find Movie Seats

Movies must lead into the approved Seat Watcher-derived Movies workflow documented in `docs/MOVIES_UX_BASELINE.md`.

### Family Deals

Purpose: Find verified family meals near the user that meet party-size, budget, cuisine, restaurant-type, and radius criteria.

Primary action: Find Family Deals

Family Deals must lead into the approved workflow documented in `docs/FAMILY_DEALS_UX_BASELINE.md`.

## Product principle

Universal Watcher is a set of specialized discovery/search tools that can optionally continue monitoring when a suitable result is not available yet.

The shared pattern is:

Discover -> Filter -> Verify -> Rank -> Result -> optionally Watch

Do not force every module to be primarily a persistent watcher. Preserve the natural behavior of each module.
