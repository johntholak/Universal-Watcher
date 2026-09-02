# Universal Watcher Web App

This is the first static foundation for the single user-facing control center.
It is deliberately a front-end preview: it does not start a watcher, call an
API, or persist account data.

## V1 shell surfaces

- module chooser for Movies, Tickets, and Family Deals
- create-watch dialog that creates a clearly labeled local draft
- active-watch and recent-activity areas
- responsive layout with keyboard focus states
- planned-module placeholder without claiming an integration exists

The shell uses plain HTML, CSS, and JavaScript so it can be opened without a
framework or dependency install. Existing module engines remain unchanged.

## Run locally

From the repository root:

```text
python -m http.server 8080 --directory web
```

Open `http://127.0.0.1:8080/` in a browser. Stop the preview with `Ctrl+C`.

## Verify

```text
python -m unittest discover -s web -p "test_*.py" -v
```

The next shell milestone is to connect these surfaces to shared watch/result
contracts after the Movies API deployment and Mac acceptance regression. Do
not represent local drafts as live monitoring.
