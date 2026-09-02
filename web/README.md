# Universal Watcher Web App

This is the first static foundation for the single user-facing control center.
It is deliberately a front-end preview: it does not start a watcher, call an
API, or persist account data.

## V1 shell surfaces

- module chooser for Movies, Tickets, and Family Deals
- create-watch dialog that creates a clearly labeled local draft
- active-watch and recent-activity areas
- local draft lifecycle controls: start, pause, resume, and stop
- responsive layout with keyboard focus states
- planned-module placeholder without claiming an integration exists

The shell uses plain HTML, CSS, and JavaScript so it can be opened without a
framework or dependency install. Existing module engines remain unchanged.

`server.py` adds a small in-memory preview API. It accepts draft watch
definitions and lifecycle transitions through the shared `core.contracts`
types and serves the same static assets. No live watcher, authentication,
persistence, or external API call is involved.

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

The next shell milestone is to connect these surfaces to shared watch/result
contracts after the Movies API deployment and Mac acceptance regression. Do
not represent local drafts as live monitoring.
