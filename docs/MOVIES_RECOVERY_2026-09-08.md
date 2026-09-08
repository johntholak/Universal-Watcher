# Movies recovery checkpoint — September 8, 2026

## What went wrong

The recovered Universal Watcher Movies module already contained the original V44 on-demand movie discovery in `seat_watcher_v44.py`. During Mac acceptance on September 8, a temporary `movie_discovery_compat.py` layer and `run_movies_compat.py` launcher were added in an attempt to adapt AMC page markup. That wrapper could try multiple AMC theater routes per selected theater and was not part of the proven V44 flow. After repeated attempts, the user encountered AMC's `Sorry, you have been blocked` page.

## Recovery decision

Return the normal Movies launcher to the proven V44 entrypoint and stop using the temporary compatibility layer.

`manage.py run movies` now launches:

```text
modules/seat-watcher/seat_watcher_premium.py
```

That UI inherits the existing V44 `find_movies` callback and uses the original `discover_movies_for_theaters()` implementation already present in `seat_watcher_v44.py`.

The temporary compatibility launcher, compatibility discovery module, and compatibility-specific tests were removed from `main`. Git history preserves those experiments if they ever need forensic review.

A root regression test now locks the Movies launcher to `seat_watcher_premium.py` so a compatibility wrapper cannot silently replace the proven entrypoint again.

## Evidence recovered from prior project material

The preserved Seat Watcher V44 bundle contains a 5,486-line `seat_watcher_v44.py` with the same V29 on-demand movie-discovery flow: one selected AMC theater page per theater, `a[href*="/movies/"]` title extraction, normalization/deduplication, and population of the movie combo.

The later post-Codex reconstruction bundle preserved the same movie-discovery implementation while adding the Mac/date/format/theater fixes. Historical handoff documentation identifies the working Mac state as the post-migration V44 line and records movie discovery, fuzzy matching, multiple theaters, and the Odyssey/IMAX 70MM end-to-end path as working.

## Protected work that remains

Do not roll back the V44.7 seat-decoder/map-verification fixes that were live-proven at CityWalk on September 8. The recovery only changes the user-facing Movies launch path and removes the temporary movie-discovery wrapper.

Do not add a new showtimes API merely to work around this incident unless recovery of the original flow is conclusively shown to be impossible.

## Mac retest result

After pulling the restored launcher path, the user made one controlled `Find Movies` attempt and AMC still served the `Sorry, you have been blocked` page. Treat this as current AMC access state on the Mac/session, not evidence that the restored V44 callback is wrong. Do not issue more repeated AMC browser requests during this block window and do not redesign the Movies architecture in response to the block.

The September 8 CityWalk V44.7 seat-map/decoder comparison remains valid evidence: the protected seat decoder captured and verified the displayed map and excluded accessibility-specific positions from ordinary-seat groups.

## Next Mac acceptance step

Wait until AMC no longer serves the block page, then perform one controlled normal-flow acceptance run. The application already allows an editable free-form movie title, so `Find Movies` remains a convenience/discovery action rather than the only way to enter a film.

Commands from the repository root when retesting is appropriate:

```bash
cd "/Users/holakhomac/Desktop/Universal Watcher GitHub"
git pull --ff-only
.venv/bin/python manage.py test
.venv/bin/python manage.py run movies
```

Acceptance order after the block is no longer present:

1. Existing four local theaters remain selected/discoverable.
2. `Find Movies` populates the movie combo using the restored V44 callback.
3. The Odyssey can be selected or typed and fuzzy matched.
4. Continue the ordinary-seat Burbank comparison.
5. Keep the already-passed CityWalk V44.7 seat-map/decoder evidence.

Nothing is considered fully accepted until the normal user flow works end to end again. While AMC access is blocked, Universal Watcher platform/UI work may continue without altering the protected Movies engine.
