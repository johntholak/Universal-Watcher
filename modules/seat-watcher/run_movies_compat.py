"""Launch the existing premium Movies UI with the AMC title-discovery compatibility fix."""
import runpy

import seat_watcher_v44 as core
from movie_discovery_compat import discover_movies_for_theaters


# Preserve the V44/V44.7 engine and UI. Only replace the Find Movies discovery
# boundary before the premium interface is loaded.
core.discover_movies_for_theaters = discover_movies_for_theaters

runpy.run_module("seat_watcher_premium", run_name="__main__")
