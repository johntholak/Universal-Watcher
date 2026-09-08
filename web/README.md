# Universal Watcher Web App

This is the first static foundation for the single user-facing control center.
It is deliberately a front-end preview: it does not start a watcher or persist
account data. When served through `server.py`, it calls only the local,
in-memory preview API.

## Current status

Home and Movies now implement the approved dark layered visual direction. Home
shows only Movies and Family Deals and conditionally reveals Watches/Results.
Movies preserves the approved five-step control hierarchy and saves the exact
configured criteria as an in-memory Watch draft. Provider-facing buttons remain
offline while AMC access is blocked; unavailable is never shown as no match.
Family Deals and the complete shared Watches experience are the next web work.
`/api/modules` and new drafts allow only Movies and Family Deals. Existing
Tickets engine/contracts remain preserved and hidden.

## Current preview surfaces

- module chooser for Movies and Family Deals only; Tickets is shelved/hidden
- approved Movies search workspace and live criteria summary
- exact-criteria Movies Save as Watch flow
- active-watch and recent-activity areas
- module-neutral matches and evidence area (honest empty state until an adapter publishes results)
- local draft lifecycle controls: start, pause, resume, and stop
- responsive layout with keyboard focus states
- no shelved or future-module placeholder cards

The shell uses plain HTML, CSS, and JavaScript so it can be opened without a
framework or dependency install. Existing module engines remain unchanged.

`server.py` adds a small in-memory preview API. It accepts draft watch
definitions and lifecycle transitions through the shared `core.contracts`
types and serves the same static assets. `GET /api/results` exposes the same
normalized result/evidence shape for future adapters, and is empty until a
module publishes a result. No live watcher, authentication, persistence, or
external API call is involved.

## Run locally

Preferred preview with the local contract boundary, from the repository root:

```text
python web/server.py
```

Open `http://127.0.0.1:8080/` in a browser. Stop the preview with `Ctrl+C`.

The static-only fallback remains available when an API is not needed:

```text
python -m http.server 8080 --directory web
```

In that mode drafts stay in the browser session and are still labeled as
non-monitoring previews.

## Verify

```text
python -m unittest discover -s web -p "test_*.py" -v
```

The shell reads the shared watch/result contracts at the preview boundary. The
next presentation milestone is Family Deals, followed by complete shared Watch
views. Live module integration remains gated on the documented acceptance work.
Do not represent local drafts or an unavailable source as live monitoring or a
verified match.
