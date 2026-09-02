from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..matcher import event_similarity
from ..models import Listing, WatchConfig


class TicketmasterSource:
    name = "Ticketmaster"
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    def __init__(self, api_key: str) -> None:
        if not api_key or api_key == "your_key_here":
            raise ValueError("Add a Ticketmaster API key to .env")
        self.api_key = api_key

    def search(self, config: WatchConfig) -> list[Listing]:
        params: dict[str, Any] = {
            "apikey": self.api_key,
            "keyword": config.event,
            "size": 100,
            "sort": "relevance,desc",
        }
        if config.city:
            params["city"] = config.city
        if config.state_code:
            params["stateCode"] = config.state_code
        if config.latitude is not None and config.longitude is not None and config.radius_miles is not None:
            params["geoPoint"] = encode_geohash(config.latitude, config.longitude)
            params["radius"] = int(round(config.radius_miles))
            params["unit"] = "miles"
        if config.start_date:
            params["startDateTime"] = _api_datetime(config.start_date, end=False)
        if config.end_date:
            params["endDateTime"] = _api_datetime(config.end_date, end=True)
        request = Request(f"{self.base_url}?{urlencode(params)}", headers={"User-Agent": "TicketWatcher/0.1"})
        try:
            with urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ticketmaster returned HTTP {exc.code}: {detail[:240]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not reach Ticketmaster: {exc.reason}") from exc
        events = payload.get("_embedded", {}).get("events", [])
        return [self._listing(event, config) for event in events]

    def _listing(self, event: dict[str, Any], config: WatchConfig) -> Listing:
        venue = (event.get("_embedded", {}).get("venues") or [{}])[0]
        price_ranges = event.get("priceRanges") or []
        minimums = [p.get("min") for p in price_ranges if isinstance(p.get("min"), (int, float))]
        currencies = [p.get("currency") for p in price_ranges if p.get("currency")]
        date_text = event.get("dates", {}).get("start", {}).get("dateTime")
        starts_at = datetime.fromisoformat(date_text.replace("Z", "+00:00")) if date_text else None
        return Listing(
            source=self.name,
            event_id=str(event.get("id", "")),
            event_name=event.get("name", "Unknown event"),
            event_url=event.get("url", ""),
            venue=venue.get("name", "Unknown venue"),
            city=venue.get("city", {}).get("name", ""),
            starts_at=starts_at,
            currency=currencies[0] if currencies else "USD",
            price_each=min(minimums) if minimums else None,
            fees_included=None,
            event_match=event_similarity(config.event, event.get("name", "")),
            distance_miles=_number(event.get("distance")),
        )


def _api_datetime(value: str, end: bool) -> str:
    if "T" in value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = datetime.fromisoformat(value + ("T23:59:59" if end else "T00:00:00"))
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def encode_geohash(latitude: float, longitude: float, precision: int = 9) -> str:
    alphabet = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    bits = (16, 8, 4, 2, 1)
    output: list[str] = []
    bit_index = char_value = 0
    use_longitude = True
    while len(output) < precision:
        current_range = lon_range if use_longitude else lat_range
        value = longitude if use_longitude else latitude
        midpoint = sum(current_range) / 2
        if value >= midpoint:
            char_value |= bits[bit_index]
            current_range[0] = midpoint
        else:
            current_range[1] = midpoint
        use_longitude = not use_longitude
        if bit_index < 4:
            bit_index += 1
        else:
            output.append(alphabet[char_value])
            bit_index = char_value = 0
    return "".join(output)
