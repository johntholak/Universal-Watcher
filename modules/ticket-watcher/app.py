from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ticket_watcher.config import load_config, load_dotenv
from ticket_watcher.models import Listing
from ticket_watcher.sources.ticketmaster import TicketmasterSource
from ticket_watcher.watcher import run


class DemoSource:
    name = "Demo Marketplace"

    def search(self, config):
        return [Listing(
            source=self.name,
            event_id="demo-1",
            event_name=config.event,
            event_url="https://www.ticketmaster.com/",
            venue=config.venue or "Demo Arena",
            city=config.city or "Los Angeles",
            starts_at=datetime.now(timezone.utc) + timedelta(days=30),
            currency="USD",
            price_each=min(config.max_price_each or 150, 125),
            quantity_available=8,
            seats_together=True,
            fees_included=True,
            section="112",
            row="8",
            event_match=1.0,
            distance_miles=min(config.radius_miles or 12, 12),
        )]


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuously watch ticket sources for matching events and prices.")
    parser.add_argument("--config", default="watch.json", help="Path to watcher JSON configuration")
    parser.add_argument("--once", action="store_true", help="Run one search cycle and exit")
    parser.add_argument("--demo", action="store_true", help="Use built-in sample inventory; no API key needed")
    parser.add_argument("--check-config", action="store_true", help="Validate configuration and exit")
    args = parser.parse_args()

    project = Path(__file__).resolve().parent
    os.chdir(project)
    load_dotenv(project / ".env")
    try:
        config = load_config(Path(args.config))
        if args.check_config:
            print("Configuration is valid.")
            return 0
        sources = [DemoSource()] if args.demo else [TicketmasterSource(os.getenv("TICKETMASTER_API_KEY", ""))]
        run(config, sources, once=args.once)
        return 0
    except KeyboardInterrupt:
        print("\nWatcher stopped.")
        return 0
    except Exception as exc:
        print(f"SETUP ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
