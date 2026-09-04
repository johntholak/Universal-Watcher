import asyncio
import json
import math
import os
import platform
import queue
import re
import sys
import subprocess
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from urllib.parse import urlparse
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import webbrowser
from difflib import SequenceMatcher
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None

from playwright.async_api import async_playwright
from amc_showtime_api import (
    AmcApiError,
    AmcShowtimeClient,
    AmcUnauthorizedVendorKey,
)


APP_NAME = "Universal Watcher | Movies"
APP_VERSION = "V44.7 RECONSTRUCTED"

# ============================================================
# PORTABLE APP PATHS
# ============================================================

def app_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

BASE_DIR = app_base_dir()
SETTINGS_FILE = BASE_DIR / "settings.json"


def load_amc_vendor_key():
    configured = os.environ.get("AMC_VENDOR_KEY", "").strip()
    if configured:
        return configured
    env_file = BASE_DIR / ".env"
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == "AMC_VENDOR_KEY":
                return value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""

# If a bundled/local Chromium folder exists, Playwright will use it.
LOCAL_BROWSERS = BASE_DIR / "browsers"
if LOCAL_BROWSERS.exists():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(LOCAL_BROWSERS)

# Force Unicode-safe output on Windows.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_SETTINGS = {
    "movie": "Spider-Man: Brand New Day",
    "format": "ANY",
    "earliest_time": "1:00pm",
    "latest_time": "7:15pm",
    "seats_required": 4,
    "minimum_row": 5,
    "search_radius_miles": 10,
    "check_interval": 30,
    "sound_alert": True,
    "alert_beeps": 5,
    "open_browser_on_match": True,
    "search_center_name": "Woodland Hills, CA",
    "location_query": "Woodland Hills, CA",
    "movie_options": [],
    "date_mode": "NEXT BEST",
    "date_start": "",
    "date_end": "",
    "next_best_days": 7,
    "search_lat": 34.1577,
    "search_lon": -118.6056,
    "showtime_refresh_cycles": 5,
    "enabled_theaters": [
        "AMC Topanga 12",
        "AMC Fallbrook 7",
        "AMC Northridge 10",
        "AMC Porter Ranch 9",
    ],
}

THEATERS = [
    {"name": "AMC Topanga 12", "slug": "amc-topanga-12", "lat": 34.1577, "lon": -118.6056},
    {"name": "AMC Fallbrook 7", "slug": "amc-fallbrook-7", "lat": 34.2007, "lon": -118.6237},
    {"name": "AMC Northridge 10", "slug": "amc-northridge-10", "lat": 34.2383, "lon": -118.5364},
    {"name": "AMC Porter Ranch 9", "slug": "amc-porter-ranch-9", "lat": 34.2827, "lon": -118.5502},
    {"name": "AMC Universal CityWalk 19", "slug": "universal-cinema-an-amc-theatre", "lat": 34.1381, "lon": -118.3529},
    {"name": "AMC Santa Monica 7", "slug": "amc-santa-monica-7", "lat": 34.0259, "lon": -118.4896},
    {"name": "AMC Burbank Town Center 8", "slug": "amc-burbank-town-center-8", "lat": 34.1845, "lon": -118.3135},
    {"name": "AMC Burbank 16", "slug": "amc-burbank-16", "lat": 34.1867, "lon": -118.3128},
    {"name": "AMC Santa Anita 16", "slug": "amc-santa-anita-16", "lat": 34.1417, "lon": -118.0467},
    {"name": "AMC Montebello 10", "slug": "amc-montebello-10", "lat": 34.0334, "lon": -118.1248},
    {"name": "AMC Marina Pacifica 12", "slug": "amc-marina-pacifica-12", "lat": 33.7758, "lon": -118.1154},
    {"name": "AMC Victoria Gardens 12", "slug": "amc-victoria-gardens-12", "lat": 34.1097, "lon": -117.5365},
]

# Advanced settings preserved from V18
MOVIE_MATCH_THRESHOLD = 0.70
DISCOVERY_TIMEOUT = 30000
DISCOVERY_WAIT_MS = 700
SEAT_RESPONSE_TIMEOUT = 5.0
SEAT_CAPTURE_WAIT_SECONDS = 10.0
MAX_CONCURRENT_SEAT_CHECKS = 17
MAX_CONCURRENT_DISCOVERY = 6
HEADLESS_SEARCH = True


# ============================================================
# HELPERS
# ============================================================

def load_settings():
    data = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)
        except Exception:
            pass
    return data


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def time_to_minutes(value):
    if not value:
        return None
    value = str(value).lower().strip()
    match = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)", value)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3)
    if period == "am" and hour == 12:
        hour = 0
    elif period == "pm" and hour != 12:
        hour += 12
    return hour * 60 + minute


def extract_first_time(text):
    if not text:
        return None
    match = re.search(
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)\b",
        str(text).lower()
    )
    return match.group(0).replace(" ", "") if match else None



MAX_DATE_RANGE_DAYS = 14
NEXT_BEST_MAX_SCAN_DAYS = 35
NEXT_BEST_EMPTY_DAYS_TO_STOP = 3  # retained for settings/history compatibility


def next_best_should_stop(found_any_showtimes, consecutive_empty_days, scanned_dates):
    """Safety stop only. Normal NEXT BEST stopping follows AMC date availability."""
    return scanned_dates >= NEXT_BEST_MAX_SCAN_DAYS


def chrome_user_agent():
    """Return a Chrome-like user agent with the current OS platform token."""
    system = platform.system().lower()
    if system == "darwin":
        platform_token = "Macintosh; Intel Mac OS X 10_15_7"
    elif system == "windows":
        platform_token = "Windows NT 10.0; Win64; x64"
    else:
        platform_token = "X11; Linux x86_64"
    return (
        "Mozilla/5.0 (" + platform_token + ") "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )


def parse_date_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
    ):
        try:
            return datetime.strptime(
                value,
                fmt
            ).date()
        except ValueError:
            continue

    return None




def resolve_date_option_value(options, search_date, today_value=None):
    """Return the AMC date-option value matching an ISO search date.

    AMC has changed option values/labels over time. Prefer exact ISO values,
    then tolerate ISO embedded in a value, then match human-readable labels.
    """
    target = parse_date_value(search_date)
    if target is None:
        return None

    if today_value is None:
        today_value = date.today()

    if target == today_value:
        for option in options or []:
            value = str(option.get("value", "") or "").strip()
            text = str(option.get("text", "") or "").strip().lower()
            if value == "" or "today" in text:
                return value

    iso = target.strftime("%Y-%m-%d")
    for option in options or []:
        value = str(option.get("value", "") or "").strip()
        if value == iso or iso in value:
            return value

    label_formats = (
        "%a, %b %d",
        "%a %b %d",
        "%b %d",
        "%m/%d",
    )
    for option in options or []:
        value = str(option.get("value", "") or "").strip()
        text = re.sub(r"\s+", " ", str(option.get("text", "") or "").strip())
        cleaned = re.sub(r"^(today|tomorrow)\s*[-–—:]?\s*", "", text, flags=re.I)
        for fmt in label_formats:
            try:
                parsed = datetime.strptime(f"{cleaned} {target.year}", f"{fmt} %Y").date()
                if parsed == target:
                    return value
            except ValueError:
                continue

    return None


def extract_date_option_dates(options, today_value=None):
    """Parse every calendar date represented by AMC's date selector options."""
    if today_value is None:
        today_value = date.today()

    parsed_dates = []
    seen = set()

    for option in options or []:
        value = str(option.get("value", "") or "").strip()
        text = re.sub(r"\s+", " ", str(option.get("text", "") or "").strip())
        lower_text = text.lower()

        candidate = None
        if value == "" and "today" in lower_text:
            candidate = today_value
        elif "tomorrow" in lower_text and not value:
            candidate = today_value + timedelta(days=1)
        else:
            candidate = parse_date_value(value)
            if candidate is None:
                iso_match = re.search(r"(20\d{2}-\d{2}-\d{2})", value)
                if iso_match:
                    candidate = parse_date_value(iso_match.group(1))

        if candidate is None:
            cleaned = re.sub(r"^(today|tomorrow)\s*[-–—:]?\s*", "", text, flags=re.I)
            label_formats = (
                "%a, %b %d, %Y",
                "%a %b %d %Y",
                "%b %d, %Y",
                "%m/%d/%Y",
                "%a, %b %d",
                "%a %b %d",
                "%b %d",
                "%m/%d",
            )
            for fmt in label_formats:
                candidates = [cleaned] if "%Y" in fmt else [
                    f"{cleaned} {today_value.year}",
                    f"{cleaned} {today_value.year + 1}",
                ]
                parse_fmt = fmt if "%Y" in fmt else f"{fmt} %Y"
                for raw in candidates:
                    try:
                        d = datetime.strptime(raw, parse_fmt).date()
                    except ValueError:
                        continue
                    if today_value - timedelta(days=1) <= d <= today_value + timedelta(days=370):
                        candidate = d
                        break
                if candidate is not None:
                    break

        if candidate is not None and candidate not in seen:
            seen.add(candidate)
            parsed_dates.append(candidate)

    return sorted(parsed_dates)


def results_fingerprint(text, hrefs):
    """Stable fingerprint for rendered AMC results, including showtime links."""
    normalized_text = re.sub(r"\s+", " ", str(text or "")).strip()
    normalized_hrefs = "|".join(str(h or "").strip() for h in (hrefs or []))
    return normalized_text + "||" + normalized_hrefs


def showtime_results_are_meaningful(text, hrefs):
    """True when AMC has rendered showtime links or an explicit empty state."""
    if hrefs:
        return True
    normalized = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return any(
        phrase in normalized
        for phrase in (
            "no showtimes",
            "no movies playing",
            "showtimes are not available",
            "there are no showtimes",
        )
    )


def summarize_inventory_results(results):
    """Separate valid negatives from technical inventory-capture failures."""
    matches = []
    captured_without_match = 0
    unavailable = 0
    errors = 0
    for result in results or []:
        if isinstance(result, Exception):
            errors += 1
            unavailable += 1
        elif not isinstance(result, dict):
            unavailable += 1
        elif result.get("inventory_status") == "match":
            matches.append(result)
        elif result.get("inventory_status") == "captured_no_match":
            captured_without_match += 1
        else:
            unavailable += 1
    return matches, captured_without_match, unavailable, errors


def verify_seats_against_rendered_map(seats, controls):
    """Require a complete, agreeing visible map before any positive/negative claim.

    Keep the proven payload decoder and grouping untouched. The displayed map
    supplies the seat-type labels lost by the legacy escaped-JSON fallback.
    Accessible spaces/companions are not ordinary seats; accessibility-specific
    matching needs an explicit future preference, not an automatic assumption.
    """
    if not controls:
        raise ValueError("Seat map not available to verify captured inventory")
    by_name = {}
    visible_names = {str(c.get("name") or "").strip().upper() for c in controls}
    for seat in seats:
        name = str(seat.get("name", "")).strip().upper()
        if not name or name not in visible_names:
            continue  # Layout gaps are not physical seats and may share blank names.
        if name in by_name and any(by_name[name].get(key) != seat.get(key)
                                   for key in ("available", "row", "column")):
            raise ValueError("Conflicting captured seat snapshots")
        by_name[name] = seat
    verified, seen = [], set()
    for control in controls:
        name = str(control.get("name") or "").strip().upper()
        label = str(control.get("label") or "").strip()
        disabled = control.get("disabled")
        if not name or not label or name in seen or type(disabled) is not bool:
            raise ValueError("Incomplete rendered seat identity/state")
        seen.add(name)
        seat = by_name.get(name)
        if seat is None or seat.get("available") is not (not disabled):
            raise ValueError("Captured inventory disagrees with the displayed seat map")
        copy = dict(seat)
        copy["display_label"] = label
        if "wheelchair" in label.lower() or "companion" in label.lower():
            copy["available"] = False
        verified.append(copy)
    return verified


def diagnostic_url(url):
    """Log provider routes, never queue/session/query tokens."""
    return urlparse(str(url))._replace(query="", fragment="").geturl()


def dated_request_was_blocked(responses, search_date):
    return any(
        status_code == 403 and f"date={search_date}" in response_url
        for status_code, response_url in responses or []
    )


def normalize_amc_api_showtimes(
    records, theater, search_date, movie, requested_format,
    earliest_minutes, latest_minutes,
):
    """Normalize approved AMC Showtime API records into the existing engine shape."""
    results = []
    seen = set()
    for record in records or []:
        if not isinstance(record, dict) or record.get("isCanceled") is True:
            continue
        title = str(
            record.get("movieName")
            or record.get("sortableMovieName")
            or record.get("sortableTitleName")
            or ""
        )
        if movie_similarity(movie, title) < MOVIE_MATCH_THRESHOLD:
            continue
        local_value = str(record.get("showDateTimeLocal") or "")
        try:
            local_time = datetime.fromisoformat(local_value.replace("Z", "+00:00"))
        except ValueError:
            continue
        suffix = "am" if local_time.hour < 12 else "pm"
        hour = local_time.hour % 12 or 12
        showtime = f"{hour}:{local_time.minute:02d}{suffix}"
        minutes = time_to_minutes(showtime)
        if minutes is None or not earliest_minutes <= minutes <= latest_minutes:
            continue
        attributes = record.get("attributes") or []
        context = " ".join(
            " ".join(
                str(attribute.get(key, ""))
                for key in ("code", "name", "description")
            )
            for attribute in attributes
            if isinstance(attribute, dict)
        )
        actual_format = identify_format(context)
        if not format_matches(requested_format, actual_format):
            continue
        showtime_id = str(record.get("id") or "").strip()
        if not showtime_id or showtime_id in seen:
            continue
        seen.add(showtime_id)
        results.append({
            "id": showtime_id,
            "time": showtime,
            "format": actual_format,
            "theater": theater["name"],
            "distance": theater.get("distance", 999999),
            "date": search_date,
            "url": f"https://www.amctheatres.com/showtimes/{showtime_id}/seats",
            "discovery_source": "AMC Showtime API",
        })
    results.sort(key=lambda item: time_to_minutes(item["time"]))
    return results

def display_date(value):
    parsed = parse_date_value(
        value
    )

    if parsed is None:
        return str(value)

    return parsed.strftime(
        "%m/%d/%Y"
    )


def input_date_display(value):
    parsed = parse_date_value(
        value
    )

    if parsed is None:
        return str(value or "")

    return parsed.strftime(
        "%m/%d/%Y"
    )


def inclusive_date_strings(
    start_value,
    end_value
):
    values = []
    current = start_value

    while current <= end_value:
        values.append(
            current.strftime(
                "%Y-%m-%d"
            )
        )

        current += timedelta(
            days=1
        )

    return values


def normalize_movie_name(value):
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = value.lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def movie_similarity(requested, actual):
    a = normalize_movie_name(requested)
    b = normalize_movie_name(actual)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def normalize_format(value):
    if not value:
        return ""
    value = str(value).upper().replace("-", " ")
    return re.sub(r"\s+", " ", value).strip()


def format_matches(requested, actual):
    requested = normalize_format(requested)
    actual = normalize_format(actual)

    if requested == "ANY":
        return True
    if requested == "IMAX 70MM":
        return "IMAX" in actual and "70MM" in actual
    if requested == "70MM":
        return "70MM" in actual and "IMAX" not in actual
    if requested == "IMAX":
        return "IMAX" in actual and "70MM" not in actual
    if requested == "DOLBY":
        return "DOLBY" in actual
    if requested == "PRIME":
        return "PRIME" in actual
    if requested == "LASER":
        return "LASER" in actual
    return requested in actual


def identify_format(text):
    if not text:
        return "STANDARD"

    upper = normalize_format(text)

    if "IMAX" in upper and "70MM" in upper:
        return "IMAX 70MM"
    if "IMAX" in upper:
        return "IMAX"
    if "70MM" in upper:
        return "70MM"
    if "DOLBY" in upper:
        return "DOLBY"
    if "PRIME" in upper:
        return "PRIME"
    if "LASER" in upper:
        return "LASER"
    if "REALD 3D" in upper or "3D" in upper:
        return "3D"
    if "DIGITAL" in upper:
        return "DIGITAL"

    return "STANDARD"


def haversine_miles(lat1, lon1, lat2, lon2):
    radius = 3958.7613

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radius * c


def build_amc_url(slug):
    return (
        "https://www.amctheatres.com/"
        "movie-theatres/los-angeles/"
        f"{slug}/showtimes"
    )



# ============================================================
# V28 ON-DEMAND LOCATION / THEATER DISCOVERY
# ============================================================

def lookup_current_location():
    """Get an approximate current location from the computer's public IP.

    No GPS permission is required. This is intended to get the user into the
    right local theater area quickly, not determine a street-level position.
    """

    # Primary service
    try:
        request = urllib.request.Request(
            "https://ipapi.co/json/",
            headers={
                "User-Agent":
                    "SeatWatcher/33 personal desktop application"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        city = str(
            data.get(
                "city",
                ""
            )
        ).strip()

        region = str(
            data.get(
                "region_code",
                data.get(
                    "region",
                    ""
                )
            )
        ).strip()

        postal = str(
            data.get(
                "postal",
                ""
            )
        ).strip()

        lat = data.get(
            "latitude"
        )
        lon = data.get(
            "longitude"
        )

        parts = [
            value
            for value in (
                city,
                region
            )
            if value
        ]

        query = ", ".join(
            parts
        )

        if postal:
            query = (
                f"{query} {postal}"
                if query
                else postal
            )

        if query:
            return {
                "query": query,
                "city": city,
                "region": region,
                "postal": postal,
                "lat": lat,
                "lon": lon,
            }

    except Exception:
        pass

    # Fallback service
    try:
        request = urllib.request.Request(
            "https://ipwho.is/",
            headers={
                "User-Agent":
                    "SeatWatcher/33 personal desktop application"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

        if data.get(
            "success",
            True
        ) is False:
            raise RuntimeError(
                "Location lookup failed."
            )

        city = str(
            data.get(
                "city",
                ""
            )
        ).strip()

        region = str(
            data.get(
                "region_code",
                data.get(
                    "region",
                    ""
                )
            )
        ).strip()

        postal = str(
            data.get(
                "postal",
                ""
            )
        ).strip()

        parts = [
            value
            for value in (
                city,
                region
            )
            if value
        ]

        query = ", ".join(
            parts
        )

        if postal:
            query = (
                f"{query} {postal}"
                if query
                else postal
            )

        if not query:
            raise RuntimeError(
                "Current location could not be determined."
            )

        return {
            "query": query,
            "city": city,
            "region": region,
            "postal": postal,
            "lat": data.get(
                "latitude"
            ),
            "lon": data.get(
                "longitude"
            ),
        }

    except Exception as exc:
        raise RuntimeError(
            "Could not determine your current location. "
            "Enter a ZIP code, city or address instead."
        ) from exc


def geocode_location(query):
    """Resolve a city, ZIP or address to latitude/longitude.

    Uses OpenStreetMap Nominatim only when the user explicitly asks
    to find theatres. Normal watcher cycles do not call this.
    """
    query = str(query).strip()

    if not query:
        raise ValueError("Enter a city, ZIP code or address.")

    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "countrycodes": "us",
        }
    )

    request = urllib.request.Request(
        "https://nominatim.openstreetmap.org/search?"
        + params,
        headers={
            "User-Agent":
                "SeatWatcher/28 personal desktop application"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    if not data:
        raise ValueError(
            f"Could not find location: {query}"
        )

    return (
        float(data[0]["lat"]),
        float(data[0]["lon"]),
        data[0].get("display_name", query)
    )


def slugify_theater_name(name):
    value = normalize_movie_name(name)

    # Known AMC naming exception.
    lower = value.lower()

    if (
        "universal" in lower
        and
        (
            "cinema" in lower
            or
            "citywalk" in lower
        )
    ):
        return "universal-cinema-an-amc-theatre"

    return value.replace(" ", "-")


def build_dynamic_amc_url(slug):
    # Universal CityWalk uses a non-mechanical canonical AMC route.
    if slug == "universal-cinema-an-amc-theatre":
        return (
            "https://www.amctheatres.com/"
            "movie-theatres/los-angeles/"
            "universal-cinema-an-amc-theatre"
        )

    # AMC currently accepts the "undefined" market segment for many
    # direct theater routes.
    return (
        "https://www.amctheatres.com/"
        "movie-theatres/undefined/"
        f"{slug}"
    )


def clean_theater_list(theaters):
    """Normalize theater records without rewriting the user's saved data."""
    cleaned_by_slug = {}
    order = []

    generic_names = {
        "amc",
        "amc theater",
        "amc theatre",
        "amc theaters",
        "amc theatres",
        "amc cinema",
        "amc cinemas",
    }

    for theater in theaters or []:
        if not isinstance(theater, dict):
            continue

        name = str(theater.get("name", "")).strip()
        normalized_name = normalize_movie_name(name)
        if not name or normalized_name in generic_names:
            continue

        try:
            lat = float(theater.get("lat"))
            lon = float(theater.get("lon"))
        except (TypeError, ValueError):
            continue

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        copy = dict(theater)
        copy["name"] = name
        copy["lat"] = lat
        copy["lon"] = lon
        copy["slug"] = str(copy.get("slug") or slugify_theater_name(name)).strip()
        if slugify_theater_name(name) == "universal-cinema-an-amc-theatre":
            copy["slug"] = "universal-cinema-an-amc-theatre"

        existing_url = str(copy.get("theater_url", "") or "").strip()
        if copy["slug"] == "universal-cinema-an-amc-theatre":
            copy["theater_url"] = build_dynamic_amc_url(copy["slug"])
        elif existing_url:
            copy["theater_url"] = existing_url.rstrip("/")
        else:
            copy["theater_url"] = build_dynamic_amc_url(copy["slug"])

        slug = copy["slug"]
        if slug not in cleaned_by_slug:
            cleaned_by_slug[slug] = copy
            order.append(slug)
            continue

        current = cleaned_by_slug[slug]
        current_distance = current.get("distance")
        new_distance = copy.get("distance")

        try:
            current_distance = float(current_distance)
        except (TypeError, ValueError):
            current_distance = None

        try:
            new_distance = float(new_distance)
        except (TypeError, ValueError):
            new_distance = None

        if (
            new_distance is not None
            and
            (
                current_distance is None
                or
                new_distance < current_distance
            )
        ):
            cleaned_by_slug[slug] = copy

    return [cleaned_by_slug[slug] for slug in order]


def overpass_find_amc_theaters(
    center_lat,
    center_lon,
    radius_miles
):
    radius_meters = max(
        1609,
        int(
            float(radius_miles)
            * 1609.344
        )
    )

    query = f"""
[out:json][timeout:20];
(
  nwr["amenity"="cinema"]["name"~"AMC",i](around:{radius_meters},{center_lat},{center_lon});
  nwr["amenity"="cinema"]["brand"~"AMC",i](around:{radius_meters},{center_lat},{center_lon});
  nwr["amenity"="cinema"]["operator"~"AMC",i](around:{radius_meters},{center_lat},{center_lon});
);
out center tags;
"""

    payload = urllib.parse.urlencode(
        {
            "data": query
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=payload,
        headers={
            "User-Agent":
                "SeatWatcher/28 personal desktop application",
            "Content-Type":
                "application/x-www-form-urlencoded",
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=25
    ) as response:
        data = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    results = []

    for element in data.get(
        "elements",
        []
    ):
        tags = element.get(
            "tags",
            {}
        )

        name = str(
            tags.get(
                "name",
                ""
            )
        ).strip()

        brand = str(
            tags.get(
                "brand",
                ""
            )
        ).strip()

        operator = str(
            tags.get(
                "operator",
                ""
            )
        ).strip()

        combined = (
            f"{name} {brand} {operator}"
        ).upper()

        if "AMC" not in combined:
            continue

        lat = element.get(
            "lat"
        )
        lon = element.get(
            "lon"
        )

        if (
            lat is None
            or
            lon is None
        ):
            center = element.get(
                "center",
                {}
            )

            lat = center.get(
                "lat"
            )
            lon = center.get(
                "lon"
            )

        if (
            lat is None
            or
            lon is None
        ):
            continue

        if not name:
            continue

        results.append(
            {
                "name": name,
                "lat": float(lat),
                "lon": float(lon),
            }
        )

    return results


def nominatim_fallback_amc_theaters(
    center_lat,
    center_lon,
    radius_miles
):
    # Fallback if Overpass is unavailable.
    # This searches only inside a bounding box around the requested point.
    miles = max(
        1.0,
        float(radius_miles)
    )

    lat_delta = miles / 69.0

    cos_lat = max(
        0.2,
        math.cos(
            math.radians(
                center_lat
            )
        )
    )

    lon_delta = miles / (
        69.0
        * cos_lat
    )

    left = center_lon - lon_delta
    right = center_lon + lon_delta
    top = center_lat + lat_delta
    bottom = center_lat - lat_delta

    params = urllib.parse.urlencode(
        {
            "q": "AMC cinema",
            "format": "jsonv2",
            "limit": 30,
            "countrycodes": "us",
            "bounded": 1,
            "viewbox":
                f"{left},{top},{right},{bottom}",
        }
    )

    request = urllib.request.Request(
        "https://nominatim.openstreetmap.org/search?"
        + params,
        headers={
            "User-Agent":
                "SeatWatcher/28 personal desktop application"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:
        data = json.loads(
            response.read().decode(
                "utf-8"
            )
        )

    results = []

    for item in data:
        display = str(
            item.get(
                "display_name",
                ""
            )
        )

        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            name = display.split(
                ",",
                1
            )[0].strip()

        if "AMC" not in (
            name + " " + display
        ).upper():
            continue

        try:
            results.append(
                {
                    "name": name,
                    "lat": float(
                        item["lat"]
                    ),
                    "lon": float(
                        item["lon"]
                    ),
                }
            )
        except Exception:
            continue

    return results


def normalize_amc_api_theaters(records, center_lat, center_lon, radius_miles):
    """Use AMC identities/coordinates without guessing names or market routes."""
    theaters = []
    for record in records:
        if record.get("isClosed") is True:
            continue
        try:
            location = record["location"]
            lat, lon = float(location["latitude"]), float(location["longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("invalid coordinates")
            distance = haversine_miles(center_lat, center_lon, lat, lon)
            if distance > float(radius_miles):
                continue
            slug = str(record["slug"]).strip()
            name = str(record.get("name") or record.get("longName") or "").strip()
            url = str(record["websiteUrl"]).rstrip("/")
            parsed = urlparse(url)
            if (not name or not slug or parsed.scheme != "https"
                    or parsed.hostname != "www.amctheatres.com"
                    or not parsed.path.startswith("/movie-theatres/")
                    or parsed.path.rsplit("/", 1)[-1] != slug):
                raise ValueError("invalid AMC identity/route")
            theaters.append({
                "name": name, "slug": slug, "amc_theatre_id": int(record["id"]),
                "lat": lat, "lon": lon, "distance": distance,
                "theater_url": url, "discovery_source": "AMC Theatre API",
            })
        except (KeyError, ValueError, TypeError) as exc:
            raise AmcApiError("AMC theater catalog could not establish full-radius coverage") from exc
    return sorted(clean_theater_list(theaters), key=lambda item: item["distance"])


async def discover_amc_theaters_for_location(
    location_query,
    radius_miles,
    emit=None
):
    """V28 on-demand geographic AMC theatre discovery.

    This intentionally does NOT depend on AMC's visible theatre-search box.
    It runs only when the user clicks Find theaters.
    """

    def say(message):
        if emit:
            emit(message)

    center_lat, center_lon, display_name = await asyncio.to_thread(
        geocode_location,
        location_query
    )

    say(
        f"Location found: {display_name}"
    )

    say(
        f"Finding AMC theaters within {float(radius_miles):.1f} miles..."
    )

    vendor_key = load_amc_vendor_key()
    if vendor_key:
        try:
            records = await asyncio.to_thread(AmcShowtimeClient(vendor_key).list_theatres)
            discovered = normalize_amc_api_theaters(
                records, center_lat, center_lon, radius_miles
            )
            say(f"AMC catalog: {len(discovered)} open theaters within the selected radius "
                f"({len(records)} catalog records checked; no top-N cap).")
            return {"theaters": discovered, "lat": center_lat, "lon": center_lon,
                    "display_name": display_name, "location_query": location_query}
        except AmcApiError as exc:
            say(f"AMC theater catalog unavailable: {exc}. Using map candidates; "
                "their completeness and current AMC identity are not verified.")

    raw_candidates = []

    try:
        raw_candidates = await asyncio.to_thread(
            overpass_find_amc_theaters,
            center_lat,
            center_lon,
            radius_miles
        )

        if raw_candidates:
            say(
                f"Map search returned {len(raw_candidates)} AMC theater candidates."
            )

    except Exception as e:
        say(
            "Primary map search unavailable; trying fallback..."
        )

    if not raw_candidates:
        try:
            raw_candidates = await asyncio.to_thread(
                nominatim_fallback_amc_theaters,
                center_lat,
                center_lon,
                radius_miles
            )

            if raw_candidates:
                say(
                    f"Fallback search returned {len(raw_candidates)} AMC theater candidates."
                )

        except Exception:
            raw_candidates = []

    if not raw_candidates:
        raise RuntimeError(
            "No AMC theaters were found near that location. "
            "Try a larger radius or use 'City, State' instead of only a ZIP code."
        )

    discovered = []
    seen = set()

    for item in raw_candidates:
        name = str(
            item.get(
                "name",
                ""
            )
        ).strip()

        if not name:
            continue

        # Normalize some map-provider naming variants.
        upper = name.upper()

        if (
            "AMC" not in upper
            and
            "UNIVERSAL CINEMA" not in upper
        ):
            continue

        lat = float(
            item["lat"]
        )
        lon = float(
            item["lon"]
        )

        distance = haversine_miles(
            center_lat,
            center_lon,
            lat,
            lon
        )

        if distance > float(
            radius_miles
        ):
            continue

        slug = slugify_theater_name(
            name
        )

        key = (
            slug,
            round(lat, 4),
            round(lon, 4)
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        discovered.append(
            {
                "name": name,
                "slug": slug,
                "lat": lat,
                "lon": lon,
                "distance": distance,
                "theater_url":
                    build_dynamic_amc_url(
                        slug
                    ),
            }
        )

    discovered = clean_theater_list(discovered)

    discovered.sort(
        key=lambda item:
        item["distance"]
    )

    if not discovered:
        raise RuntimeError(
            "AMC locations were found, but none were inside "
            f"the selected {radius_miles}-mile radius."
        )

    say(
        f"Found {len(discovered)} map-listed AMC candidates within the selected radius; "
        "map coverage and current AMC identity are not verified."
    )

    for theater in discovered:
        say(
            f"  {theater['name']} - {theater['distance']:.1f} mi"
        )

    return {
        "location_query": location_query,
        "display_name": display_name,
        "lat": center_lat,
        "lon": center_lon,
        "theaters": discovered,
    }



# ============================================================
# V29 ON-DEMAND MOVIE DISCOVERY
# ============================================================

async def discover_movies_at_theater(
    browser,
    theater,
    semaphore,
    emit=None
):
    async with semaphore:

        def say(message):
            if emit:
                emit(message)

        page = None

        try:
            page = await browser.new_page()

            theater_url = theater.get(
                "theater_url"
            )

            if theater_url:
                theater_url = (
                    theater_url.rstrip("/")
                    + "/showtimes"
                )
            else:
                theater_url = build_amc_url(
                    theater["slug"]
                )

            say(
                f"Checking movies: {theater['name']}"
            )

            await page.goto(
                theater_url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            await page.wait_for_timeout(
                900
            )

            links = page.locator(
                'a[href*="/movies/"]'
            )

            count = await links.count()

            movies = []

            for i in range(count):
                try:
                    link = links.nth(i)

                    text = (
                        await link.inner_text()
                    ).strip()

                    if not text:
                        continue

                    # Keep only compact movie-title-like link text.
                    if len(text) > 140:
                        continue

                    lines = [
                        line.strip()
                        for line in text.splitlines()
                        if line.strip()
                    ]

                    if not lines:
                        continue

                    # The actual title is normally the first useful line.
                    title = lines[0]

                    # Skip obvious navigation/non-title text.
                    bad = {
                        "movies",
                        "showtimes",
                        "tickets",
                        "learn more",
                        "view details",
                    }

                    if title.lower() in bad:
                        continue

                    if len(title) < 2:
                        continue

                    movies.append(
                        title
                    )

                except Exception:
                    continue

            return movies

        except Exception:
            return []

        finally:
            try:
                if page:
                    await page.close()
            except Exception:
                pass


async def discover_movies_for_theaters(
    theaters,
    emit=None
):
    """Discover currently listed movies only when user clicks Find Movies."""

    if not theaters:
        raise ValueError(
            "Select at least one theater first."
        )

    def say(message):
        if emit:
            emit(message)

    say(
        f"Finding movies across {len(theaters)} selected theaters..."
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True
        )

        try:
            semaphore = asyncio.Semaphore(
                min(
                    MAX_CONCURRENT_DISCOVERY,
                    max(
                        1,
                        len(theaters)
                    )
                )
            )

            tasks = [
                discover_movies_at_theater(
                    browser,
                    theater,
                    semaphore,
                    emit=emit
                )
                for theater in theaters
            ]

            results = await asyncio.gather(
                *tasks,
                return_exceptions=True
            )

        finally:
            await browser.close()

    unique = {}

    for result in results:
        if not isinstance(
            result,
            list
        ):
            continue

        for title in result:
            normalized = normalize_movie_name(
                title
            )

            if not normalized:
                continue

            # First encountered capitalization wins.
            unique.setdefault(
                normalized,
                title.strip()
            )

    movies = sorted(
        unique.values(),
        key=lambda value:
        value.lower()
    )

    if not movies:
        raise RuntimeError(
            "No movie titles were found at the selected theaters."
        )

    say(
        f"Found {len(movies)} unique movies."
    )

    return movies


# ============================================================
# V18 ENGINE, NOW PARAMETERIZED FOR V20 GUI
# ============================================================

class WatcherEngine:
    def __init__(self, settings, emit, status, stop_event, match_callback):
        self.settings = settings
        self.emit = emit
        self.status = status
        self.stop_event = stop_event
        self.match_callback = match_callback

        self.earliest_minutes = time_to_minutes(
            settings["earliest_time"]
        )

        self.latest_minutes = time_to_minutes(
            settings["latest_time"]
        )

        self.search_dates = self.get_search_dates()
        self.latest_available_dates = {}
        self.discovery_failures = []
        vendor_key = load_amc_vendor_key()
        self.amc_api_client = AmcShowtimeClient(vendor_key) if vendor_key else None
        self.amc_theatre_ids = {}
        self.seat_access_block = None

    def get_search_dates(self):
        mode = str(
            self.settings.get(
                "date_mode",
                "NEXT BEST"
            )
        ).upper().strip()

        today_value = date.today()

        if mode == "NEXT BEST":
            days = int(
                self.settings.get(
                    "next_best_days",
                    7
                )
            )

            days = max(
                1,
                min(
                    MAX_DATE_RANGE_DAYS,
                    days
                )
            )

            return [
                (
                    today_value
                    + timedelta(
                        days=offset
                    )
                ).strftime(
                    "%Y-%m-%d"
                )
                for offset in range(days)
            ]

        start_value = parse_date_value(
            self.settings.get(
                "date_start",
                ""
            )
        )

        if mode == "SPECIFIC DATE":
            if start_value is None:
                raise ValueError(
                    "Enter a valid specific date."
                )

            return [
                start_value.strftime(
                    "%Y-%m-%d"
                )
            ]

        if mode == "DATE RANGE":
            end_value = parse_date_value(
                self.settings.get(
                    "date_end",
                    ""
                )
            )

            if (
                start_value is None
                or
                end_value is None
            ):
                raise ValueError(
                    "Enter valid start and end dates."
                )

            if end_value < start_value:
                raise ValueError(
                    "End date must be on or after start date."
                )

            span = (
                end_value - start_value
            ).days + 1

            if span > MAX_DATE_RANGE_DAYS:
                raise ValueError(
                    f"Date range is limited to "
                    f"{MAX_DATE_RANGE_DAYS} days."
                )

            return inclusive_date_strings(
                start_value,
                end_value
            )

        raise ValueError(
            f"Unknown date mode: {mode}"
        )

    def get_local_theaters(self):
        nearby = []
        enabled = set(self.settings["enabled_theaters"])

        theater_source = self.settings.get("theaters") or THEATERS

        for theater in theater_source:
            if theater["name"] not in enabled:
                continue

            distance = haversine_miles(
                self.settings["search_lat"],
                self.settings["search_lon"],
                theater["lat"],
                theater["lon"]
            )

            copy = dict(theater)
            copy["distance"] = distance

            if distance <= self.settings["search_radius_miles"]:
                nearby.append(copy)

        nearby.sort(key=lambda x: x["distance"])
        return nearby

    async def find_movie_container(self, page):
        try:
            links = page.locator('a[href*="/movies/"]')
            count = await links.count()
        except Exception:
            return None

        best = None
        best_score = 0.0

        for i in range(count):
            if self.stop_event.is_set():
                return None

            try:
                link = links.nth(i)
                text = (await link.inner_text()).strip()

                if not text:
                    continue

                if len(text) > 150:
                    continue

                score = movie_similarity(
                    self.settings["movie"],
                    text
                )

                if score > best_score:
                    best_score = score
                    best = link

            except Exception:
                continue

        if best is None or best_score < MOVIE_MATCH_THRESHOLD:
            return None

        element = best

        for _ in range(15):
            try:
                element = element.locator("xpath=..")
                text = await element.inner_text(timeout=3000)

                if not text:
                    continue

                if len(text) > 50:
                    if (
                        "Reserved Seating" in text
                        or
                        "AMC Signature Recliners" in text
                    ):
                        return element

            except Exception:
                break

        return None

    async def find_format_section(self, link):
        element = link

        for _ in range(12):
            try:
                element = element.locator("xpath=..")
                text = await element.inner_text(timeout=1500)

                if not text or len(text) > 2500:
                    continue

                upper = text.upper()

                if any(
                    x in upper
                    for x in (
                        "IMAX",
                        "70MM",
                        "DOLBY",
                        "PRIME",
                        "LASER",
                        "REALD",
                        "DIGITAL"
                    )
                ):
                    # Stop at the closest useful ancestor. Continuing upward
                    # can merge neighboring AMC format groups.
                    return text

            except Exception:
                break

        return ""

    async def get_showtime_context(self, link):
        element = link
        best_text = ""

        for _ in range(10):
            try:
                element = element.locator("xpath=..")
                text = await element.inner_text(timeout=1500)

                if not text:
                    continue

                if len(text) <= 1500:
                    best_text = text

                upper = text.upper()

                if any(
                    word in upper
                    for word in (
                        "IMAX",
                        "70MM",
                        "DOLBY",
                        "PRIME",
                        "LASER",
                        "REALD",
                        "DIGITAL"
                    )
                ):
                    return text

            except Exception:
                break

        return best_text

    async def discover_showtimes(self, page, theater, search_date):
        container = await self.find_movie_container(page)

        if container is None:
            return []

        try:
            links = container.locator('a[href*="/showtimes/"]')
            link_count = await links.count()
        except Exception:
            return []

        results = []
        seen = set()

        for i in range(link_count):
            if self.stop_event.is_set():
                break

            try:
                link = links.nth(i)

                href = (
                    await link.get_attribute("href")
                    or ""
                )

                match = re.search(
                    r"/showtimes/(\d+)",
                    href
                )

                if not match:
                    continue

                showtime_id = match.group(1)

                link_text = (
                    await link.inner_text()
                ).strip()

                showtime = extract_first_time(
                    link_text
                )

                if not showtime:
                    try:
                        parent = link.locator("xpath=..")
                        parent_text = await parent.inner_text()
                        showtime = extract_first_time(parent_text)
                    except Exception:
                        pass

                if not showtime:
                    element = link

                    for _ in range(5):
                        try:
                            element = element.locator("xpath=..")

                            ancestor_text = await element.inner_text(
                                timeout=1000
                            )

                            candidate = extract_first_time(
                                ancestor_text
                            )

                            if candidate:
                                showtime = candidate
                                break

                        except Exception:
                            break

                if not showtime:
                    continue

                minutes = time_to_minutes(showtime)

                if minutes is None:
                    continue

                if not (
                    self.earliest_minutes
                    <= minutes
                    <= self.latest_minutes
                ):
                    continue

                context = await self.find_format_section(link)

                if not context:
                    context = await self.get_showtime_context(link)

                actual_format = identify_format(context)

                if not format_matches(
                    self.settings["format"],
                    actual_format
                ):
                    continue

                key = (
                    showtime_id,
                    showtime,
                    actual_format
                )

                if key in seen:
                    continue

                seen.add(key)

                results.append(
                    {
                        "id": showtime_id,
                        "time": showtime,
                        "format": actual_format,
                        "theater": theater["name"],
                        "distance": theater["distance"],
                        "date": search_date,
                        "url": (
                            "https://www.amctheatres.com"
                            f"/showtimes/{showtime_id}/seats"
                        )
                    }
                )

            except Exception:
                continue

        results.sort(
            key=lambda x: time_to_minutes(
                x["time"]
            )
        )

        return results

    def walk_json(self, value, output):
        if isinstance(value, dict):
            if (
                all(key in value for key in ("available", "column", "row"))
                and ("name" in value or "seatName" in value)
            ):
                try:
                    output.append(
                        {
                            "available": bool(
                                value["available"]
                            ),
                            "column": int(
                                value["column"]
                            ),
                            "row": int(
                                value["row"]
                            ),
                            "name": str(
                                value.get("name", value.get("seatName", ""))
                            ),
                            "type": str(
                                value.get(
                                    "type",
                                    ""
                                )
                            ),
                            "seatTier": str(
                                value.get(
                                    "seatTier",
                                    ""
                                )
                            ),
                            "shouldDisplay": bool(
                                value.get(
                                    "shouldDisplay",
                                    True
                                )
                            ),
                        }
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    pass

            for child in value.values():
                self.walk_json(child, output)

        elif isinstance(value, list):
            for child in value:
                self.walk_json(child, output)

    def parse_seats_from_bytes(self, raw):
        if not raw:
            return []

        try:
            data = json.loads(raw)

            seats = []
            self.walk_json(
                data,
                seats
            )

            if seats:
                return seats

        except Exception:
            pass

        encodings = [
            "utf-8",
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "latin-1"
        ]

        for encoding in encodings:
            try:
                text = raw.decode(
                    encoding,
                    errors="replace"
                )

                if not text:
                    continue

                try:
                    data = json.loads(text)

                    seats = []
                    self.walk_json(
                        data,
                        seats
                    )

                    if seats:
                        return seats

                except Exception:
                    pass

                cleaned = text.replace(
                    '\\"',
                    '"'
                )

                # AMC embeds escaped seat objects in its streamed HTML. Decode
                # each whole flat object before the legacy text fallback: the
                # latter can cross an unnamed aisle/gap into the following seat
                # and loses type/visibility metadata. Keep all encoding and
                # fallback paths; the rendered-map guard rejects partial reads.
                seats = []
                for fragment in re.finditer(
                    r'\{[^{}]*"available"\s*:\s*(?:true|false)[^{}]*\}', cleaned, re.I
                ):
                    try:
                        self.walk_json(json.loads(fragment.group()), seats)
                    except (ValueError, TypeError):
                        continue
                if seats:
                    return seats

                pattern = re.compile(
                    r'"available"\s*:\s*'
                    r'(true|false).*?'
                    r'"column"\s*:\s*(\d+).*?'
                    r'"row"\s*:\s*(\d+).*?'
                    r'"name"\s*:\s*"([^"]+)"',
                    re.I | re.S
                )

                seats = []

                for match in pattern.finditer(
                    cleaned
                ):
                    try:
                        seats.append(
                            {
                                "available": (
                                    match.group(1).lower()
                                    == "true"
                                ),
                                "column": int(
                                    match.group(2)
                                ),
                                "row": int(
                                    match.group(3)
                                ),
                                "name": match.group(4),
                                "type": "",
                                "seatTier": "",
                                "shouldDisplay": True,
                            }
                        )

                    except Exception:
                        continue

                if seats:
                    return seats

            except Exception:
                continue

        return []

    def promising_response(self, response):
        url = response.url.lower()

        if "amctheatres.com" not in url:
            return False

        path = url.split("?", 1)[0]

        ignored_extensions = (
            ".js",
            ".css",
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".woff",
            ".woff2",
            ".ico",
            ".gif",
            ".webp",
            ".map",
            ".avif"
        )

        if path.endswith(
            ignored_extensions
        ):
            return False

        try:
            content_type = (
                response.headers
                .get(
                    "content-type",
                    ""
                )
                .lower()
            )

        except Exception:
            content_type = ""

        if any(
            word in url
            for word in (
                "seat",
                "availability",
                "reservation",
                "ticket"
            )
        ):
            return True

        if "json" in content_type:
            return True

        return False

    def get_seat_position(self, seat):
        name = str(
            seat.get(
                "name",
                ""
            )
        ).strip().upper()

        match = re.match(
            r"^([A-Z]+)\s*0*(\d+)$",
            name
        )

        if not match:
            return None

        return (
            match.group(1),
            int(match.group(2))
        )

    def find_consecutive_seats(self, seats):
        unique = {}

        for seat in seats:
            name = str(
                seat.get(
                    "name",
                    ""
                )
            ).strip().upper()

            if not name:
                continue

            if name not in unique:
                unique[name] = seat

            else:
                if (
                    seat.get("available") is True
                    and
                    unique[name].get(
                        "available"
                    ) is not True
                ):
                    unique[name] = seat

        eligible = []

        for seat in unique.values():
            try:
                if seat.get(
                    "available"
                ) is not True:
                    continue

                if seat.get(
                    "shouldDisplay",
                    True
                ) is not True:
                    continue

                numeric_row = int(
                    seat.get(
                        "row",
                        -1
                    )
                )

                if numeric_row < self.settings["minimum_row"]:
                    continue

                position = self.get_seat_position(
                    seat
                )

                if position is None:
                    continue

                row_label, seat_number = position

                copy = dict(seat)
                copy["_row_label"] = row_label
                copy["_seat_number"] = seat_number

                eligible.append(copy)

            except Exception:
                continue

        rows = {}

        for seat in eligible:
            rows.setdefault(
                seat["_row_label"],
                []
            ).append(seat)

        for row_label in sorted(rows):
            row_seats = rows[row_label]

            row_seats.sort(
                key=lambda s: s["_seat_number"]
            )

            for i in range(
                len(row_seats)
                - self.settings["seats_required"]
                + 1
            ):
                group = row_seats[
                    i:
                    i + self.settings["seats_required"]
                ]

                numbers = [
                    s["_seat_number"]
                    for s in group
                ]

                expected = list(
                    range(
                        numbers[0],
                        numbers[0]
                        + self.settings["seats_required"]
                    )
                )

                if numbers == expected:
                    return group

        return None

    def calculate_center_score(self, group):
        if not group:
            return 0.0

        numbers = []

        for seat in group:
            try:
                numbers.append(
                    int(
                        seat.get(
                            "_seat_number",
                            0
                        )
                    )
                )
            except Exception:
                pass

        if not numbers:
            return 0.0

        center = (
            min(numbers)
            + max(numbers)
        ) / 2.0

        maximum = max(
            20,
            max(numbers)
        )

        map_center = maximum / 2.0

        distance = abs(
            center - map_center
        )

        score = 1.0 - (
            distance
            / max(
                1.0,
                map_center
            )
        )

        return max(
            0.0,
            min(
                1.0,
                score
            )
        )

    def ranking_key(self, match):
        row = int(
            match.get(
                "seat_row",
                0
            )
        )

        minutes = (
            time_to_minutes(
                match.get(
                    "time",
                    ""
                )
            )
            or 9999
        )

        match_date = str(
            match.get(
                "date",
                "9999-12-31"
            )
        )

        distance = float(
            match.get(
                "distance",
                999999
            )
        )

        center = float(
            match.get(
                "center_score",
                0
            )
        )

        return (
            -row,
            match_date,
            minutes,
            distance,
            -center
        )

    async def check_showtime(
        self,
        browser,
        showtime,
        semaphore
    ):
        async with semaphore:
            if self.stop_event.is_set():
                return None

            if self.seat_access_block:
                self.emit(f"  Seat inventory unavailable: {self.seat_access_block}")
                return dict(showtime, inventory_status="unavailable", reason=self.seat_access_block)

            context = None
            page = None

            all_seats = []
            response_tasks = set()
            response_handler = None

            try:
                context = await browser.new_context(
                    user_agent=chrome_user_agent()
                )
                page = await context.new_page()

                self.emit(
                    f"Seat check: {showtime['theater']} | "
                    f"{showtime.get('date', '')} | {showtime['time']} | "
                    f"{showtime['format']}"
                )

                response_diagnostics = []

                async def capture_response(response):
                    if self.stop_event.is_set():
                        return

                    if not self.promising_response(
                        response
                    ):
                        return

                    if response.status >= 400:
                        if response.status in (403, 429):
                            self.seat_access_block = (
                                f"AMC returned HTTP {response.status}; further seat requests "
                                "are disabled for this run. Retry later after access is available."
                            )
                        response_diagnostics.append(
                            (diagnostic_url(response.url), 0, 0, f"HTTP {response.status}")
                        )
                        return

                    try:
                        raw = await asyncio.wait_for(
                            response.body(),
                            timeout=SEAT_RESPONSE_TIMEOUT
                        )

                        seats = self.parse_seats_from_bytes(
                            raw
                        )

                        if seats:
                            all_seats.extend(
                                seats
                            )

                        response_diagnostics.append(
                            (diagnostic_url(response.url), len(raw), len(seats), "")
                        )

                    except Exception as exc:
                        response_diagnostics.append(
                            (diagnostic_url(response.url), 0, 0, f"{type(exc).__name__}: body capture failed")
                        )

                def handle_response(response):
                    task = asyncio.create_task(capture_response(response))
                    response_tasks.add(task)
                    task.add_done_callback(response_tasks.discard)

                response_handler = handle_response
                page.on(
                    "response",
                    handle_response
                )

                try:
                    await page.goto(
                        showtime["url"],
                        wait_until="domcontentloaded",
                        timeout=30000
                    )
                except Exception:
                    pass

                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

                capture_deadline = time.monotonic() + SEAT_CAPTURE_WAIT_SECONDS
                while not all_seats and time.monotonic() < capture_deadline:
                    if self.stop_event.is_set() or self.seat_access_block:
                        break
                    if response_tasks:
                        await asyncio.wait(
                            list(response_tasks), timeout=0.5,
                            return_when=asyncio.FIRST_COMPLETED
                        )
                    else:
                        await page.wait_for_timeout(250)

                if response_tasks:
                    await asyncio.wait(list(response_tasks), timeout=SEAT_RESPONSE_TIMEOUT)

                if not all_seats or self.seat_access_block:
                    self.emit(
                        f"  Seat inventory unavailable for {showtime['theater']} "
                        f"at {showtime['time']} (capture failed after "
                        f"{SEAT_CAPTURE_WAIT_SECONDS:.0f}s)."
                    )
                    if response_diagnostics:
                        for url, byte_count, seat_count, error in response_diagnostics[-3:]:
                            detail = error or f"{byte_count} bytes; {seat_count} seats parsed"
                            self.emit(f"    Candidate response: {url} | {detail}")
                    else:
                        self.emit("    No candidate AMC seat/availability JSON response was observed.")
                    return {
                        "inventory_status": "unavailable",
                        "theater": showtime["theater"],
                        "date": showtime.get("date", ""),
                        "time": showtime["time"],
                        "url": showtime["url"],
                    }

                if self.settings.get("diagnostic_logging"):
                    for url, byte_count, seat_count, error in response_diagnostics:
                        if seat_count:
                            self.emit(
                                f"    Captured inventory response: {url} | "
                                f"{byte_count} bytes; {seat_count} seats parsed"
                            )

                seat_map = page.get_by_role("grid", name="Seat Selection Map", exact=True)
                await seat_map.wait_for(state="visible", timeout=5000)
                controls = await seat_map.get_by_role("checkbox").evaluate_all(
                    """els => els.map(el => ({
                        name: el.getAttribute('name'),
                        label: el.getAttribute('aria-label'),
                        disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true'
                    }))"""
                )
                all_seats = verify_seats_against_rendered_map(all_seats, controls)
                inventory_count = len(all_seats)
                self.emit(f"    Verified {inventory_count} seats against the displayed map; "
                          "wheelchair/companion positions excluded from ordinary-seat groups.")

                group = self.find_consecutive_seats(
                    all_seats
                )

                if not group:
                    self.emit(
                        f"  No group of {self.settings['seats_required']} qualifying "
                        f"seats found at {showtime['theater']} {showtime['time']}."
                    )
                    return {
                        "inventory_status": "captured_no_match",
                        "inventory_seat_count": inventory_count,
                        "theater": showtime["theater"],
                        "date": showtime.get("date", ""),
                        "time": showtime["time"],
                        "url": showtime["url"],
                    }

                group = sorted(
                    group,
                    key=lambda seat:
                    seat["_seat_number"]
                )

                names = [
                    seat["name"]
                    for seat in group
                ]

                group_row = max(
                    int(
                        seat.get(
                            "row",
                            0
                        )
                    )
                    for seat in group
                )

                center_score = (
                    self.calculate_center_score(
                        group
                    )
                )

                return {
                    "inventory_status": "match",
                    "inventory_seat_count": inventory_count,
                    "theater": showtime["theater"],
                    "date": showtime.get(
                        "date",
                        ""
                    ),
                    "time": showtime["time"],
                    "format": showtime["format"],
                    "seats": names,
                    "seat_row": group_row,
                    "distance": showtime.get(
                        "distance",
                        999999
                    ),
                    "center_score": center_score,
                    "url": showtime["url"]
                }

            except Exception as exc:
                self.emit(
                    f"  Seat check error at {showtime.get('theater', 'unknown theater')} "
                    f"{showtime.get('time', '')}: {type(exc).__name__}: {exc}"
                )
                return {
                    "inventory_status": "unavailable",
                    "theater": showtime.get("theater", "unknown theater"),
                    "date": showtime.get("date", ""),
                    "time": showtime.get("time", ""),
                    "url": showtime.get("url", ""),
                }

            finally:
                if page and response_handler:
                    page.remove_listener("response", response_handler)
                for task in response_tasks:
                    task.cancel()
                if response_tasks:
                    await asyncio.gather(*response_tasks, return_exceptions=True)
                try:
                    if page:
                        await page.close()
                except Exception:
                    pass

                try:
                    if context:
                        await context.close()
                except Exception:
                    pass

    def discovery_unavailable(self, theater, search_date, reason):
        self.discovery_failures.append((theater.get("name", "unknown theater"), search_date, reason))
        self.emit(f"  SHOWTIME DISCOVERY UNAVAILABLE: {theater.get('name', 'unknown theater')} "
                  f"| {search_date} | {reason}")
        return []

    async def discover_theater(
        self,
        browser,
        theater,
        search_date,
        semaphore
    ):
        async with semaphore:
            if self.stop_event.is_set():
                return []

            if self.amc_api_client is not None:
                slug = theater.get("slug", "")
                try:
                    theatre_id = theater.get("amc_theatre_id")
                    if theatre_id is None:
                        theatre_id = self.amc_theatre_ids.get(slug)
                    if theatre_id is None:
                        theatre_id = await asyncio.to_thread(
                            self.amc_api_client.resolve_theatre_id, slug
                        )
                        self.amc_theatre_ids[slug] = theatre_id
                    records = await asyncio.to_thread(
                        self.amc_api_client.list_showtimes,
                        theatre_id,
                        search_date,
                    )
                    results = normalize_amc_api_showtimes(
                        records,
                        theater,
                        search_date,
                        self.settings["movie"],
                        self.settings["format"],
                        self.earliest_minutes,
                        self.latest_minutes,
                    )
                    self.emit(
                        f"Checking via approved AMC Showtime API: "
                        f"{theater['name']} | {search_date} | {len(results)} qualifying"
                    )
                    return results
                except AmcUnauthorizedVendorKey:
                    self.emit(
                        "  AMC rejected the configured vendor key (HTTP 403 / 12005). "
                        "The reason is not established; confirm catalog access with AMC. "
                        "API discovery is disabled for this run; falling back to the website."
                    )
                    self.amc_api_client = None
                except (AmcApiError, ValueError, KeyError) as exc:
                    self.emit(
                        f"  AMC Showtime API unavailable for {theater['name']} "
                        f"on {search_date}: {exc}. Falling back to the website."
                    )

            context = None
            page = None

            try:
                context = await browser.new_context(
                    user_agent=chrome_user_agent()
                )
                page = await context.new_page()

                self.emit(
                    f"Checking: {theater['name']} | {search_date}"
                )

                theater_url = theater.get("theater_url")
                if theater_url:
                    theater_url = theater_url.rstrip("/") + "/showtimes"
                else:
                    theater_url = build_amc_url(
                        theater["slug"]
                    )

                # AMC no longer reliably honors ?date=YYYY-MM-DD.
                # Load the theater page, then drive its real date selector.
                navigation = await page.goto(
                    theater_url,
                    wait_until="domcontentloaded",
                    timeout=DISCOVERY_TIMEOUT
                )
                if navigation is not None and navigation.status >= 400:
                    return self.discovery_unavailable(
                        theater, search_date, f"Theater page returned HTTP {navigation.status}"
                    )

                selector = page.locator('select[name="date"]')
                await selector.wait_for(
                    state="attached",
                    timeout=DISCOVERY_TIMEOUT
                )

                # Give React a brief opportunity to attach behavior/options.
                try:
                    await page.wait_for_function(
                        """() => {
                            const el = document.querySelector('select[name="date"]');
                            if (!el || !el.options || !el.options.length) return false;
                            const keys = Object.keys(el);
                            return keys.some(k => k.startsWith('__reactProps') || k.startsWith('__reactFiber'));
                        }""",
                        timeout=min(DISCOVERY_TIMEOUT, 5000)
                    )
                except Exception:
                    # Option presence is the hard requirement; React's private
                    # property names can change.
                    pass

                # AMC's date options can arrive after the <select> itself.
                # Poll briefly for the requested date instead of snapshotting once.
                desired_value = None
                option_records = []
                option_deadline = time.monotonic() + min(10.0, DISCOVERY_TIMEOUT / 1000)
                while time.monotonic() < option_deadline and desired_value is None:
                    option_records = await selector.locator("option").evaluate_all(
                        "(opts) => opts.map(o => ({value: o.value, text: (o.textContent || '').trim()}))"
                    )
                    desired_value = resolve_date_option_value(
                        option_records,
                        search_date
                    )
                    if desired_value is None:
                        await page.wait_for_timeout(250)

                available_dates = extract_date_option_dates(option_records)
                if available_dates:
                    theater_key = theater.get("slug") or theater.get("name") or theater_url
                    self.latest_available_dates[theater_key] = max(available_dates)

                if desired_value is None:
                    latest_text = ""
                    if available_dates:
                        latest_text = f" Latest selectable AMC date: {display_date(max(available_dates))}."
                    self.emit(
                        f"  AMC date option not available for {search_date}.{latest_text}"
                    )
                    return self.discovery_unavailable(theater, search_date, "Requested date not selectable")

                results_box = page.locator("#showtime-results")

                async def read_results_fingerprint():
                    try:
                        state = await page.evaluate(
                            """() => {
                                const results = document.querySelector('#showtime-results');
                                if (!results) return {text: '', hrefs: []};
                                return {
                                    text: results.innerText || '',
                                    hrefs: Array.from(
                                        results.querySelectorAll('a[href*="/showtimes/"]')
                                    ).map(a => a.href || a.getAttribute('href') || '')
                                };
                            }"""
                        )
                        return results_fingerprint(
                            state.get("text", ""),
                            state.get("hrefs", [])
                        )
                    except Exception:
                        return ""

                async def read_results_state():
                    try:
                        return await page.evaluate(
                            """() => {
                                const select = document.querySelector('select[name="date"]');
                                const results = document.querySelector('#showtime-results');
                                return {
                                    selected: select ? select.value : '',
                                    text: results ? (results.innerText || '') : '',
                                    hrefs: results ? Array.from(
                                        results.querySelectorAll('a[href*="/showtimes/"]')
                                    ).map(a => a.href || a.getAttribute('href') || '') : []
                                };
                            }"""
                        )
                    except Exception:
                        return {"selected": "", "text": "", "hrefs": []}

                old_fingerprint = await read_results_fingerprint()
                current_value = await selector.input_value()
                discovery_responses = []

                def note_discovery_response(response):
                    url = str(response.url)
                    lower = url.lower()
                    if "amctheatres" in lower and any(
                        word in lower
                        for word in ("showtime", "graphql", "api", "date=")
                    ):
                        discovery_responses.append((response.status, url))

                page.on("response", note_discovery_response)

                if current_value != desired_value:
                    await selector.select_option(value=desired_value)

                    try:
                        await page.wait_for_function(
                            """(desired) => {
                                const select = document.querySelector('select[name="date"]');
                                return !!select && select.value === desired;
                            }""",
                            arg=desired_value,
                            timeout=min(DISCOVERY_TIMEOUT, 5000)
                        )
                    except Exception:
                        self.emit(
                            f"  AMC did not accept date selection for {search_date}."
                        )
                        return self.discovery_unavailable(theater, search_date, "Date selection not accepted")

                    # Same visible times can repeat on consecutive dates, so text
                    # alone is not enough. Showtime href/IDs are part of the
                    # fingerprint and should change when the requested day loads.
                    refresh_deadline = time.monotonic() + min(15.0, DISCOVERY_TIMEOUT / 1000)
                    refreshed = False
                    stable_fingerprint = None
                    stable_since = None
                    while time.monotonic() < refresh_deadline:
                        await page.wait_for_timeout(250)
                        state = await read_results_state()
                        new_fingerprint = results_fingerprint(state["text"], state["hrefs"])
                        meaningful = showtime_results_are_meaningful(state["text"], state["hrefs"])
                        if (
                            state["selected"] == desired_value
                            and new_fingerprint != old_fingerprint
                            and meaningful
                        ):
                            if new_fingerprint != stable_fingerprint:
                                stable_fingerprint = new_fingerprint
                                stable_since = time.monotonic()
                            elif time.monotonic() - stable_since >= 1.5:
                                refreshed = True
                                break

                    if not refreshed:
                        self.emit(
                            f"  AMC date changed to {search_date}, but its live results stayed stale; "
                            "retrying with a full dated-page reload."
                        )
                        self.emit(
                            "    Date control diagnostic: "
                            f"desired={desired_value!r}; page={diagnostic_url(page.url)}; options="
                            + repr(option_records[:5])
                        )
                        if discovery_responses:
                            for status_code, response_url in discovery_responses[-8:]:
                                self.emit(
                                    f"    Date response: {status_code} {diagnostic_url(response_url)}"
                                )
                        else:
                            self.emit("    Date response: no relevant AMC request observed.")
                        blocked = dated_request_was_blocked(
                            discovery_responses, search_date
                        )
                        if blocked:
                            return self.discovery_unavailable(theater, search_date, "Dated request HTTP 403")
                        try:
                            dated_url = page.url
                            await page.goto(
                                dated_url,
                                wait_until="domcontentloaded",
                                timeout=DISCOVERY_TIMEOUT
                            )
                        except Exception as exc:
                            self.emit(
                                f"  AMC dated-page reload failed for {search_date}: "
                                f"{type(exc).__name__}: {exc}"
                            )
                            return self.discovery_unavailable(theater, search_date, "Dated reload failed")

                        reload_deadline = time.monotonic() + min(
                            15.0, DISCOVERY_TIMEOUT / 1000
                        )
                        stable_fingerprint = None
                        stable_since = None
                        while time.monotonic() < reload_deadline:
                            try:
                                state = await page.evaluate(
                                    """() => {
                                        const results = document.querySelector('#showtime-results');
                                        return {
                                            text: results ? (results.innerText || '') : '',
                                            hrefs: results ? Array.from(
                                                results.querySelectorAll('a[href*="/showtimes/"]')
                                            ).map(a => a.href || a.getAttribute('href') || '') : []
                                        };
                                    }"""
                                )
                            except Exception:
                                state = {"text": "", "hrefs": []}
                            fingerprint = results_fingerprint(
                                state["text"], state["hrefs"]
                            )
                            if (
                                f"date={search_date}" in page.url
                                and showtime_results_are_meaningful(
                                    state["text"], state["hrefs"]
                                )
                            ):
                                if fingerprint != stable_fingerprint:
                                    stable_fingerprint = fingerprint
                                    stable_since = time.monotonic()
                                elif time.monotonic() - stable_since >= 1.5:
                                    refreshed = True
                                    break
                            await page.wait_for_timeout(250)

                        if not refreshed:
                            self.emit(
                                f"  AMC dated-page reload did not produce verified "
                                f"results for {search_date}."
                            )
                            return self.discovery_unavailable(theater, search_date, "Dated reload not verified")

                else:
                    # The requested option can be selected before AMC finishes
                    # asynchronously rendering that date's results.
                    ready_deadline = time.monotonic() + min(15.0, DISCOVERY_TIMEOUT / 1000)
                    stable_fingerprint = None
                    stable_since = None
                    while time.monotonic() < ready_deadline:
                        state = await read_results_state()
                        fingerprint = results_fingerprint(state["text"], state["hrefs"])
                        if (
                            state["selected"] == desired_value
                            and showtime_results_are_meaningful(state["text"], state["hrefs"])
                        ):
                            if fingerprint != stable_fingerprint:
                                stable_fingerprint = fingerprint
                                stable_since = time.monotonic()
                            elif time.monotonic() - stable_since >= 1.5:
                                break
                        await page.wait_for_timeout(250)
                    else:
                        self.emit(
                            f"  AMC results did not settle for selected date {search_date}."
                        )
                        return self.discovery_unavailable(theater, search_date, "Selected-date results did not settle")

                await page.wait_for_timeout(DISCOVERY_WAIT_MS)

                return await self.discover_showtimes(
                    page,
                    theater,
                    search_date
                )

            except Exception as exc:
                self.emit(
                    f"  Showtime discovery error at {theater.get('name', 'unknown theater')} "
                    f"for {search_date}: {type(exc).__name__}: {exc}"
                )
                return self.discovery_unavailable(theater, search_date, f"Discovery error: {type(exc).__name__}")

            finally:
                try:
                    if page:
                        await page.close()
                except Exception:
                    pass
                try:
                    if context:
                        await context.close()
                except Exception:
                    pass

    async def discover_all_theaters(
        self,
        browser,
        theaters
    ):
        self.discovery_failures = []
        semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_DISCOVERY
        )

        tasks = [
            self.discover_theater(
                browser,
                theater,
                search_date,
                semaphore
            )
            for theater in theaters
            for search_date in self.search_dates
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        all_showtimes = []

        checks = [(theater, search_date) for theater in theaters for search_date in self.search_dates]
        for (theater, search_date), result in zip(checks, results):
            if isinstance(result, list):
                all_showtimes.extend(result)
            else:
                self.discovery_unavailable(theater, search_date, "Discovery task failed")

        unique = {}

        for item in all_showtimes:
            unique[
                (
                    item["id"],
                    item.get(
                        "date",
                        ""
                    )
                )
            ] = item

        all_showtimes = list(
            unique.values()
        )

        theater_order = {
            theater["name"]: index
            for index, theater
            in enumerate(theaters)
        }

        all_showtimes.sort(
            key=lambda x: (
                x.get(
                    "date",
                    "9999-12-31"
                ),
                theater_order.get(
                    x["theater"],
                    999
                ),
                time_to_minutes(
                    x["time"]
                )
            )
        )

        return all_showtimes

    def alert_user(self):
        if not self.settings["sound_alert"]:
            return

        beeps = int(self.settings.get("alert_beeps", 5))

        if winsound is not None:
            for _ in range(beeps):
                try:
                    winsound.Beep(1200, 500)
                except Exception:
                    pass
                time.sleep(0.15)
            return

        if sys.platform == "darwin":
            sound = "/System/Library/Sounds/Glass.aiff"
            for _ in range(beeps):
                try:
                    subprocess.run(
                        ["/usr/bin/afplay", sound],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass
            return

    async def open_match(
        self,
        playwright,
        match
    ):
        if not self.settings[
            "open_browser_on_match"
        ]:
            return

        try:
            browser = await playwright.chromium.launch(
                headless=False
            )

            page = await browser.new_page()

            await page.goto(
                match["url"],
                wait_until="domcontentloaded",
                timeout=60000
            )

            self.status("SEATS FOUND - BROWSER OPEN")
            self.emit("")
            self.emit("Purchase browser is open.")
            self.emit("Close that browser when you are finished.")

            while not page.is_closed():
                if self.stop_event.is_set():
                    break

                await asyncio.sleep(
                    1
                )

            try:
                await browser.close()
            except Exception:
                pass

        except Exception as e:
            self.status("SEATS FOUND - BROWSER OPEN FAILED")
            self.emit(
                f"Could not open purchase browser: {e}"
            )
            self.emit(
                f"Open manually: {match['url']}"
            )

    async def countdown(self, seconds):
        end = time.time() + seconds

        while time.time() < end:
            if self.stop_event.is_set():
                return False

            remaining = max(
                0,
                int(end - time.time())
            )

            self.status(
                f"Next search in {remaining}s"
            )

            await asyncio.sleep(
                0.25
            )

        return True

    async def run_next_best(self):
        """Progress chronologically until a match or AMC schedule exhaustion."""
        theaters = self.get_local_theaters()

        if not theaters:
            raise ValueError(
                "No selected AMC theaters are within the radius."
            )

        self.emit(
            f"{APP_NAME} {APP_VERSION}"
        )
        self.emit(
            f"Movie: {self.settings['movie']}"
        )
        self.emit(
            f"Format: {self.settings['format']}"
        )
        self.emit("Date mode: NEXT BEST")
        self.emit("Dates: progressive, one calendar day at a time until AMC has no later selectable dates")
        self.emit("Priority: row > time > distance > center")
        self.emit("")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=HEADLESS_SEARCH
            )

            found_any_showtimes = False
            consecutive_empty_days = 0
            scanned_dates = 0
            total_inventory_unavailable = 0
            total_inventory_captured_no_match = 0
            total_discovery_unavailable = 0
            current_date = date.today()

            try:
                while not self.stop_event.is_set():
                    search_date = current_date.strftime("%Y-%m-%d")
                    scanned_dates += 1
                    cycle_start = time.perf_counter()

                    self.search_dates = [search_date]
                    self.status(
                        f"Next Best: {display_date(search_date)}"
                    )
                    self.emit("=" * 58)
                    self.emit(
                        f"NEXT BEST DATE #{scanned_dates}: "
                        f"{display_date(search_date)}"
                    )
                    self.emit("=" * 58)

                    all_showtimes = await self.discover_all_theaters(
                        browser,
                        theaters
                    )
                    date_discovery_failures = len(self.discovery_failures)
                    total_discovery_unavailable += date_discovery_failures
                    if date_discovery_failures:
                        self.emit(
                            f"SHOWTIME DISCOVERY UNAVAILABLE: {date_discovery_failures} "
                            "theater/date checks could not be verified."
                        )

                    self.emit(
                        f"QUALIFYING SHOWTIMES: {len(all_showtimes)}"
                    )

                    if all_showtimes:
                        found_any_showtimes = True
                        consecutive_empty_days = 0

                        self.status("Checking seats...")
                        self.emit(
                            f"Checking seat inventory for {len(all_showtimes)} showtimes..."
                        )
                        seat_semaphore = asyncio.Semaphore(
                            MAX_CONCURRENT_SEAT_CHECKS
                        )
                        tasks = [
                            self.check_showtime(
                                browser,
                                showtime,
                                seat_semaphore
                            )
                            for showtime in all_showtimes
                        ]
                        results = await asyncio.gather(
                            *tasks,
                            return_exceptions=True
                        )

                        candidates, captured_no_match, unavailable, task_errors = (
                            summarize_inventory_results(results)
                        )
                        total_inventory_unavailable += unavailable
                        total_inventory_captured_no_match += captured_no_match
                        for result in candidates:
                            self.emit(
                                f"FOUND: "
                                f"{result['theater']} | "
                                f"{result.get('date', '')} | "
                                f"{result['time']} | "
                                f"ROW {result['seat_row']} | "
                                f"{' '.join(result['seats'])}"
                            )

                        if candidates:
                            ranked = sorted(
                                candidates,
                                key=self.ranking_key
                            )

                            self.emit("")
                            self.emit("SMART MATCH RANKING:")
                            for rank, candidate in enumerate(
                                ranked[:10],
                                start=1
                            ):
                                self.emit(
                                    f"#{rank} "
                                    f"{candidate['theater']} | "
                                    f"{candidate.get('date', '')} | "
                                    f"{candidate['time']} | "
                                    f"ROW {candidate['seat_row']} | "
                                    f"{' '.join(candidate['seats'])} | "
                                    f"{candidate['distance']:.2f} mi | "
                                    f"CENTER {candidate['center_score']:.2f}"
                                )

                            found = ranked[0]
                            self.emit("")
                            self.emit("BEST MATCH SELECTED:")
                            self.emit(
                                f"{found['theater']} | "
                                f"{found.get('date', '')} | "
                                f"{found['time']} | "
                                f"ROW {found['seat_row']} | "
                                f"{' '.join(found['seats'])}"
                            )
                            self.emit(
                                f"Search date time: "
                                f"{time.perf_counter() - cycle_start:.1f}s"
                            )

                            self.match_callback(found)
                            await asyncio.to_thread(self.alert_user)

                            try:
                                await browser.close()
                            except Exception:
                                pass

                            await self.open_match(
                                playwright,
                                found
                            )
                            return

                        if unavailable:
                            self.emit(
                                f"SEAT INVENTORY UNAVAILABLE: {unavailable} of "
                                f"{len(all_showtimes)} showtimes could not be verified."
                            )
                            if task_errors:
                                self.emit(f"  Seat-check task errors: {task_errors}")
                        if captured_no_match:
                            self.emit(
                                f"NO QUALIFYING SEATS FOUND in {captured_no_match} "
                                "showtimes with captured inventory."
                            )

                    else:
                        consecutive_empty_days += 1

                    self.emit(
                        f"Search date time: "
                        f"{time.perf_counter() - cycle_start:.1f}s"
                    )

                    theater_keys = [
                        theater.get("slug") or theater.get("name")
                        for theater in theaters
                    ]
                    known_latest = [
                        self.latest_available_dates.get(key)
                        for key in theater_keys
                        if self.latest_available_dates.get(key) is not None
                    ]

                    if len(known_latest) == len(theater_keys) and known_latest:
                        latest_amc_date = max(known_latest)
                        if current_date >= latest_amc_date:
                            if total_discovery_unavailable:
                                message = (
                                    "Reached the last selectable AMC date currently listed "
                                    f"({display_date(latest_amc_date)}), but showtime discovery "
                                    f"was unavailable for {total_discovery_unavailable} checks; "
                                    "the run cannot conclude that no qualifying showtimes or seats exist."
                                )
                            elif total_inventory_unavailable:
                                message = (
                                    "Reached the last selectable AMC date currently listed "
                                    f"({display_date(latest_amc_date)}). Seat inventory was "
                                    f"unavailable for {total_inventory_unavailable} showtimes; "
                                    "the run cannot conclude that no qualifying seats exist."
                                )
                            elif total_inventory_captured_no_match:
                                message = (
                                    "Reached the last selectable AMC date currently listed "
                                    f"({display_date(latest_amc_date)}). No qualifying seats were "
                                    f"found in {total_inventory_captured_no_match} showtimes with "
                                    "successfully captured inventory."
                                )
                            else:
                                message = (
                                    "Reached the last selectable AMC date currently listed "
                                    f"({display_date(latest_amc_date)}). No qualifying showtimes "
                                    "were discovered within the selected filters."
                                )
                            self.status(message)
                            self.emit(message)
                            return

                    if next_best_should_stop(
                        found_any_showtimes,
                        consecutive_empty_days,
                        scanned_dates
                    ):
                        message = (
                            "Stopped at the Next Best safety ceiling after "
                            f"{NEXT_BEST_MAX_SCAN_DAYS} calendar days because AMC's "
                            "date selector did not provide a reliable earlier endpoint."
                        )
                        self.status(message)
                        self.emit(message)
                        return

                    current_date += timedelta(days=1)

            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

    async def run(self):
        if (
            self.earliest_minutes is None
            or
            self.latest_minutes is None
        ):
            raise ValueError(
                "Check earliest/latest time."
            )

        if (
            self.earliest_minutes
            > self.latest_minutes
        ):
            raise ValueError(
                "Earliest time must be before latest time."
            )

        mode = str(
            self.settings.get("date_mode", "NEXT BEST")
        ).upper().strip()

        if mode == "NEXT BEST":
            await self.run_next_best()
            return

        theaters = self.get_local_theaters()

        if not theaters:
            raise ValueError(
                "No selected AMC theaters are within the radius."
            )

        self.emit(
            f"{APP_NAME} {APP_VERSION}"
        )
        self.emit(
            f"Movie: {self.settings['movie']}"
        )
        self.emit(
            f"Format: {self.settings['format']}"
        )
        self.emit(
            f"Date mode: "
            f"{self.settings.get('date_mode', 'NEXT BEST')}"
        )
        self.emit(
            "Dates: "
            + ", ".join(
                self.search_dates
            )
        )
        self.emit(
            "Priority: row > time > distance > center"
        )
        self.emit("")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=HEADLESS_SEARCH
            )

            cycle_number = 0
            cached_showtimes = []

            try:
                while not self.stop_event.is_set():
                    cycle_number += 1
                    cycle_start = time.perf_counter()

                    self.status(
                        f"Search cycle #{cycle_number}"
                    )

                    self.emit(
                        "=" * 58
                    )
                    self.emit(
                        f"NEW SEARCH CYCLE #{cycle_number}"
                    )
                    self.emit(
                        "=" * 58
                    )

                    refresh_showtimes = (
                        cycle_number == 1
                        or
                        (
                            self.settings[
                                "showtime_refresh_cycles"
                            ] > 0
                            and
                            (
                                (
                                    cycle_number - 1
                                )
                                %
                                self.settings[
                                    "showtime_refresh_cycles"
                                ]
                                ==
                                0
                            )
                        )
                    )

                    if refresh_showtimes:
                        self.status(
                            "Refreshing showtimes..."
                        )

                        self.emit(
                            "Refreshing showtimes from AMC..."
                        )

                        cached_showtimes = (
                            await self.discover_all_theaters(
                                browser,
                                theaters
                            )
                        )

                        if self.discovery_failures:
                            self.emit(
                                f"SHOWTIME DISCOVERY UNAVAILABLE: "
                                f"{len(self.discovery_failures)} theater/date checks "
                                "could not be verified."
                            )

                        self.emit(
                            f"Showtime cache refreshed: "
                            f"{len(cached_showtimes)} qualifying showtimes."
                        )

                    else:
                        self.emit(
                            "Using cached showtimes."
                        )

                    all_showtimes = list(
                        cached_showtimes
                    )

                    self.emit(
                        f"QUALIFYING SHOWTIMES: "
                        f"{len(all_showtimes)}"
                    )

                    if not all_showtimes:
                        cycle_time = (
                            time.perf_counter()
                            - cycle_start
                        )

                        self.emit(
                            f"Search cycle time: "
                            f"{cycle_time:.1f}s"
                        )

                        if not await self.countdown(
                            self.settings[
                                "check_interval"
                            ]
                        ):
                            return

                        continue

                    self.status(
                        "Checking seats..."
                    )
                    self.emit(
                        f"Checking seat inventory for {len(all_showtimes)} showtimes..."
                    )

                    seat_semaphore = asyncio.Semaphore(
                        MAX_CONCURRENT_SEAT_CHECKS
                    )

                    tasks = [
                        self.check_showtime(
                            browser,
                            showtime,
                            seat_semaphore
                        )
                        for showtime in all_showtimes
                    ]

                    results = await asyncio.gather(
                        *tasks,
                        return_exceptions=True
                    )

                    candidates, captured_no_match, unavailable, task_errors = (
                        summarize_inventory_results(results)
                    )

                    for result in candidates:
                        self.emit(
                            f"FOUND: "
                            f"{result['theater']} | "
                            f"{result.get('date', '')} | "
                            f"{result['time']} | "
                            f"ROW {result['seat_row']} | "
                            f"{' '.join(result['seats'])}"
                        )

                    cycle_time = (
                        time.perf_counter()
                        - cycle_start
                    )

                    if candidates:
                        ranked = sorted(
                            candidates,
                            key=self.ranking_key
                        )

                        self.emit("")
                        self.emit(
                            "SMART MATCH RANKING:"
                        )

                        for rank, candidate in enumerate(
                            ranked[:10],
                            start=1
                        ):
                            self.emit(
                                f"#{rank} "
                                f"{candidate['theater']} | "
                                f"{candidate.get('date', '')} | "
                                f"{candidate['time']} | "
                                f"ROW {candidate['seat_row']} | "
                                f"{' '.join(candidate['seats'])} | "
                                f"{candidate['distance']:.2f} mi | "
                                f"CENTER {candidate['center_score']:.2f}"
                            )

                        found = ranked[0]

                        self.emit("")
                        self.emit(
                            "BEST MATCH SELECTED:"
                        )
                        self.emit(
                            f"{found['theater']} | "
                            f"{found.get('date', '')} | "
                            f"{found['time']} | "
                            f"ROW {found['seat_row']} | "
                            f"{' '.join(found['seats'])}"
                        )

                        self.emit(
                            f"Search cycle time: "
                            f"{cycle_time:.1f}s"
                        )

                        self.match_callback(
                            found
                        )

                        await asyncio.to_thread(
                            self.alert_user
                        )

                        try:
                            await browser.close()
                        except Exception:
                            pass

                        await self.open_match(
                            playwright,
                            found
                        )

                        return

                    self.emit(
                        f"Search cycle time: "
                        f"{cycle_time:.1f}s"
                    )

                    if unavailable:
                        self.emit(
                            f"SEAT INVENTORY UNAVAILABLE: {unavailable} of "
                            f"{len(all_showtimes)} showtimes could not be verified."
                        )
                        if task_errors:
                            self.emit(f"  Seat-check task errors: {task_errors}")
                    if captured_no_match:
                        self.emit(
                            f"NO QUALIFYING SEATS FOUND in {captured_no_match} "
                            "showtimes with captured inventory."
                        )

                    if not await self.countdown(
                        self.settings[
                            "check_interval"
                        ]
                    ):
                        return

            finally:
                try:
                    await browser.close()
                except Exception:
                    pass



# ============================================================
# V22 MODERN GUI
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SeatWatcherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("1180x900")
        self.root.minsize(760, 680)

        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        self.current_best_match = None
        self.details_visible = False

        self.saved = load_settings()

        self.movie = tk.StringVar(value=self.saved["movie"])

        saved_movie_options = self.saved.get(
            "movie_options",
            []
        )

        self.movie_options = [
            str(value)
            for value in saved_movie_options
            if str(value).strip()
        ]

        if (
            self.movie.get().strip()
            and
            self.movie.get().strip()
            not in self.movie_options
        ):
            self.movie_options.insert(
                0,
                self.movie.get().strip()
            )
        self.format = tk.StringVar(value=self.saved["format"])
        self.earliest_time = tk.StringVar(value=self.saved["earliest_time"])
        self.latest_time = tk.StringVar(value=self.saved["latest_time"])

        today_value = date.today()

        default_end_value = (
            today_value
            + timedelta(
                days=6
            )
        )

        self.date_mode = tk.StringVar(
            value=self.saved.get(
                "date_mode",
                "NEXT BEST"
            )
        )

        self.date_start = tk.StringVar(
            value=input_date_display(
                self.saved.get(
                    "date_start",
                    ""
                )
                or
                today_value.strftime(
                    "%m/%d/%Y"
                )
            )
        )

        self.date_end = tk.StringVar(
            value=input_date_display(
                self.saved.get(
                    "date_end",
                    ""
                )
                or
                default_end_value.strftime(
                    "%m/%d/%Y"
                )
            )
        )
        self.seats_required = tk.IntVar(value=self.saved["seats_required"])
        self.minimum_row = tk.IntVar(value=self.saved["minimum_row"])
        self.search_radius = tk.DoubleVar(value=self.saved["search_radius_miles"])
        self.check_interval = tk.IntVar(value=self.saved["check_interval"])
        self.sound_alert = tk.BooleanVar(value=self.saved["sound_alert"])
        self.open_browser = tk.BooleanVar(value=self.saved["open_browser_on_match"])
        self.location_query = tk.StringVar(
            value=self.saved.get(
                "location_query",
                self.saved.get(
                    "search_center_name",
                    "Woodland Hills, CA"
                )
            )
        )

        self.dynamic_theaters = clean_theater_list(
            self.saved.get("theaters")
            or [dict(t) for t in THEATERS]
        )

        enabled = set(self.saved["enabled_theaters"])
        self.theater_vars = {
            t["name"]: tk.BooleanVar(
                value=t["name"] in enabled
            )
            for t in self.dynamic_theaters
        }

        self.status_text = tk.StringVar(value="Ready")
        self.cycle_text = tk.StringVar(value="0")
        self.showtime_text = tk.StringVar(value="0")
        self.groups_text = tk.StringVar(value="0")
        self.last_cycle_text = tk.StringVar(value="--")

        self.build_ui()
        self.root.after(100, self.process_events)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        # ====================================================
        # V43 CINEMATIC TECH UI
        # Same watcher functionality, new interaction shell.
        # ====================================================

        self.bg = "#04050A"
        self.shell = "#090C14"

        self.panel_movie = "#171226"
        self.panel_where = "#0B1B27"
        self.panel_when = "#101623"
        self.panel_watch = "#0E1623"

        self.panel_movie_hi = "#241B40"
        self.panel_where_hi = "#123044"
        self.panel_when_hi = "#192238"

        self.field_bg = "#090E17"

        self.text = "#FFFFFF"
        self.text_soft = "#D9E1EE"
        self.text_dim = "#93A0B5"

        self.accent = "#BD4DFF"
        self.accent_hover = "#D87BFF"
        self.blue = "#00D4FF"
        self.blue_hover = "#43E2FF"
        self.success = "#25F3A6"
        self.green = self.success

        self.movie_border = "#A64BFF"
        self.where_border = "#00BDF4"
        self.when_border = "#557DCE"
        self.field_border = "#39536F"

        self.advanced_visible = False
        self.theaters_visible = False

        self.root.configure(
            fg_color=self.bg
        )
        self.root.grid_columnconfigure(
            0,
            weight=1
        )
        self.root.grid_rowconfigure(
            0,
            weight=1
        )

        # V44 ambient backdrop: layered "light fields" around the app shell.
        # It is intentionally non-interactive and sits behind the scroll frame.
        self.ambient_canvas = tk.Canvas(
            self.root,
            bg=self.bg,
            highlightthickness=0,
            bd=0
        )
        self.ambient_canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        outer = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0
        )
        outer.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        outer.grid_columnconfigure(
            0,
            weight=1
        )

        self.outer_frame = outer

        # Shadow/depth layer behind the actual shell.
        self.shell_shadow = ctk.CTkFrame(
            outer,
            fg_color="#020308",
            corner_radius=32,
            border_width=1,
            border_color="#11192A"
        )
        self.shell_shadow.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(31, 27)
        )

        self.app_shell = ctk.CTkFrame(
            outer,
            fg_color="#090D17",
            corner_radius=28,
            border_width=1,
            border_color="#354A6B"
        )
        self.app_shell.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=24,
            pady=(24, 38)
        )
        self.app_shell.grid_columnconfigure(
            0,
            weight=1
        )

        content = ctk.CTkFrame(
            self.app_shell,
            fg_color="transparent"
        )
        content.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=28,
            pady=24
        )
        content.grid_columnconfigure(
            0,
            weight=1
        )

        self.root.bind(
            "<Configure>",
            self._on_window_resize,
            add="+"
        )
        self.root.bind(
            "<Configure>",
            self._ambient_resize,
            add="+"
        )
        self.root.after(
            50,
            self._apply_responsive_width
        )
        self.root.after(
            60,
            self._draw_ambient_background
        )

        # ----------------------------------------------------
        # HEADER / ATMOSPHERE
        # ----------------------------------------------------
        hero_outer = ctk.CTkFrame(
            content,
            fg_color="#2A1248",
            corner_radius=22,
            border_width=1,
            border_color="#9B45F4"
        )
        hero_outer.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 18)
        )
        hero_outer.grid_columnconfigure(
            0,
            weight=1
        )

        hero_inner = ctk.CTkFrame(
            hero_outer,
            fg_color="#111A2C",
            corner_radius=19,
            border_width=1,
            border_color="#167EAA"
        )
        hero_inner.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )
        hero_inner.grid_columnconfigure(
            0,
            weight=1
        )

        top_accent = ctk.CTkFrame(
            hero_inner,
            height=4,
            fg_color="#C65CFF",
            corner_radius=2
        )
        top_accent.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=140,
            pady=(10, 0)
        )

        title_row = ctk.CTkFrame(
            hero_inner,
            fg_color="transparent"
        )
        title_row.grid(
            row=1,
            column=0,
            pady=(18, 0)
        )

        ctk.CTkLabel(
            title_row,
            text="Movies",
            font=ctk.CTkFont(
                size=29,
                weight="bold"
            ),
            text_color=self.text
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            title_row,
            text="V44",
            width=42,
            height=23,
            corner_radius=12,
            fg_color="#7024BA",
            text_color="#FFFFFF",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=(10, 0)
        )

        ctk.CTkLabel(
            hero_inner,
            text="Find better seats automatically.",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            text_color="#E9D9FF"
        ).grid(
            row=2,
            column=0,
            pady=(6, 0)
        )

        ctk.CTkLabel(
            hero_inner,
            text="Pick a movie. Tell us where and when. We'll watch the seats.",
            font=ctk.CTkFont(size=11),
            text_color="#9EBCD0"
        ).grid(
            row=3,
            column=0,
            pady=(4, 20)
        )

        # ----------------------------------------------------
        # MOVIE - HERO SECTION
        # ----------------------------------------------------
        movie = self._modern_panel(
            content,
            row=1,
            title="MOVIE",
            subtitle="Choose what you want to see",
            bg=self.panel_movie,
            border=self.movie_border,
            accent=self.accent
        )

        movie_row = ctk.CTkFrame(
            movie,
            fg_color="transparent"
        )
        movie_row.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(2, 14)
        )
        movie_row.grid_columnconfigure(
            0,
            weight=1
        )

        self.movie_combo = ctk.CTkComboBox(
            movie_row,
            variable=self.movie,
            values=(
                self.movie_options
                if self.movie_options
                else [self.movie.get()]
            ),
            height=48,
            corner_radius=13,
            fg_color=self.field_bg,
            border_width=1,
            border_color="#6A468A",
            text_color=self.text,
            button_color="#39294E",
            button_hover_color="#4C3768",
            dropdown_fg_color="#171222",
            dropdown_hover_color="#2A1D3D",
            dropdown_text_color=self.text,
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            )
        )
        self.movie_combo.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.find_movies_button = ctk.CTkButton(
            movie_row,
            text="Find movies",
            command=self.find_movies,
            width=112,
            height=48,
            corner_radius=13,
            fg_color="#402067",
            hover_color="#562B89",
            border_width=1,
            border_color="#8C4CCB",
            text_color="#F0DFFF",
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )
        self.find_movies_button.grid(
            row=0,
            column=1,
            padx=(12, 0)
        )

        movie_controls = ctk.CTkFrame(
            movie,
            fg_color="transparent"
        )
        movie_controls.grid(
            row=3,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 20)
        )

        self._control_chip(
            movie_controls,
            "SEATS TOGETHER",
            self.seats_required,
            0,
            accent="#A84DFF",
            width=150
        )

        self._control_chip(
            movie_controls,
            "MINIMUM ROW",
            self.minimum_row,
            1,
            accent="#7C56E8",
            width=150
        )

        # ----------------------------------------------------
        # WHERE
        # ----------------------------------------------------
        where = self._modern_panel(
            content,
            row=2,
            title="WHERE",
            subtitle="Choose the area and theaters",
            bg=self.panel_where,
            border=self.where_border,
            accent=self.blue
        )

        loc_label_row = ctk.CTkFrame(
            where,
            fg_color="transparent"
        )
        loc_label_row.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(2, 6)
        )
        loc_label_row.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            loc_label_row,
            text="LOCATION",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            ),
            text_color="#78DFFF"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        location_row = ctk.CTkFrame(
            where,
            fg_color="transparent"
        )
        location_row.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )
        location_row.grid_columnconfigure(
            0,
            weight=1
        )

        self.location_entry = ctk.CTkEntry(
            location_row,
            textvariable=self.location_query,
            height=46,
            corner_radius=12,
            fg_color=self.field_bg,
            border_width=1,
            border_color="#26769A",
            text_color=self.text,
            placeholder_text="ZIP, city or address",
            font=ctk.CTkFont(size=13)
        )
        self.location_entry.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        self.use_location_button = ctk.CTkButton(
            location_row,
            text="Use my location",
            command=self.use_my_location,
            width=118,
            height=46,
            corner_radius=12,
            fg_color="#075D85",
            hover_color="#087EAF",
            border_width=1,
            border_color="#00A9DF",
            text_color="#E1F8FF",
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )
        self.use_location_button.grid(
            row=0,
            column=1,
            padx=(10, 0)
        )

        self.find_theaters_button = ctk.CTkButton(
            location_row,
            text="Find theaters",
            command=self.find_theaters,
            width=108,
            height=46,
            corner_radius=12,
            fg_color="#1C2C3B",
            hover_color="#283C50",
            border_width=1,
            border_color="#3E6381",
            text_color=self.text_soft,
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )
        self.find_theaters_button.grid(
            row=0,
            column=2,
            padx=(8, 0)
        )

        where_controls = ctk.CTkFrame(
            where,
            fg_color="transparent"
        )
        where_controls.grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 12)
        )

        self._control_chip(
            where_controls,
            "RADIUS (MILES)",
            self.search_radius,
            0,
            accent="#00B9F2",
            width=165
        )

        format_chip = ctk.CTkFrame(
            where_controls,
            width=210,
            height=66,
            fg_color="#0B1D29",
            corner_radius=13,
            border_width=1,
            border_color="#126D91"
        )
        format_chip.grid(
            row=0,
            column=1,
            padx=(10, 0)
        )
        format_chip.grid_propagate(False)

        ctk.CTkLabel(
            format_chip,
            text="FORMAT",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            ),
            text_color="#6FDCFF"
        ).pack(
            anchor="w",
            padx=12,
            pady=(8, 1)
        )

        self.format_combo = ctk.CTkComboBox(
            format_chip,
            variable=self.format,
            values=[
                "ANY",
                "IMAX 70MM",
                "IMAX",
                "70MM",
                "DOLBY",
                "PRIME",
                "LASER"
            ],
            height=30,
            corner_radius=8,
            fg_color="#0A111A",
            border_width=0,
            text_color=self.text,
            button_color="#15435A",
            button_hover_color="#1D5D7B",
            dropdown_fg_color="#0C1A25",
            dropdown_hover_color="#15364A",
            dropdown_text_color=self.text,
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )
        self.format_combo.pack(
            fill="x",
            padx=8,
            pady=(0, 8)
        )

        self.theater_summary_button = ctk.CTkButton(
            where,
            text="Theaters selected  ›",
            command=self.toggle_theaters,
            height=44,
            corner_radius=12,
            fg_color="#073149",
            hover_color="#0A4667",
            border_width=1,
            border_color="#087DB0",
            text_color="#59D9FF",
            anchor="w",
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            )
        )
        self.theater_summary_button.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )

        self.theater_panel = ctk.CTkFrame(
            where,
            fg_color="#08151F",
            corner_radius=12,
            border_width=1,
            border_color="#17475F"
        )
        self.theater_panel.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        self.theater_panel.grid_columnconfigure(
            0,
            weight=1
        )

        self.theater_grid = ctk.CTkFrame(
            self.theater_panel,
            fg_color="transparent"
        )
        self.theater_grid.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=10
        )
        self.theater_grid.grid_columnconfigure(
            (0, 1),
            weight=1
        )

        self.render_theaters()
        self.theater_panel.grid_remove()

        # ----------------------------------------------------
        # WHEN
        # ----------------------------------------------------
        when = self._modern_panel(
            content,
            row=3,
            title="WHEN",
            subtitle="Choose one date, a range, or let us find the next best",
            bg=self.panel_when,
            border=self.when_border,
            accent="#5B8CFF"
        )

        self.date_mode_control = ctk.CTkSegmentedButton(
            when,
            variable=self.date_mode,
            values=[
                "NEXT BEST",
                "SPECIFIC DATE",
                "DATE RANGE"
            ],
            command=self.on_date_mode_change,
            height=42,
            corner_radius=12,
            fg_color="#0B101A",
            selected_color="#A84DFF",
            selected_hover_color="#BF69FF",
            unselected_color="#1B2434",
            unselected_hover_color="#293650",
            text_color=self.text,
            font=ctk.CTkFont(
                size=10,
                weight="bold"
            )
        )
        self.date_mode_control.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(3, 14)
        )

        self.date_fields = ctk.CTkFrame(
            when,
            fg_color="transparent"
        )
        self.date_fields.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )
        self.date_fields.grid_columnconfigure(
            (0, 1),
            weight=1
        )

        self.date_start_entry = ctk.CTkEntry(
            self.date_fields,
            textvariable=self.date_start,
            height=42,
            corner_radius=11,
            fg_color=self.field_bg,
            border_width=1,
            border_color="#4A5F82",
            text_color=self.text,
            placeholder_text="MM/DD/YYYY"
        )
        self.date_start_entry.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6)
        )

        self.date_end_entry = ctk.CTkEntry(
            self.date_fields,
            textvariable=self.date_end,
            height=42,
            corner_radius=11,
            fg_color=self.field_bg,
            border_width=1,
            border_color="#4A5F82",
            text_color=self.text,
            placeholder_text="MM/DD/YYYY"
        )
        self.date_end_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(6, 0)
        )

        time_controls = ctk.CTkFrame(
            when,
            fg_color="transparent"
        )
        time_controls.grid(
            row=4,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 20)
        )

        self._control_chip(
            time_controls,
            "AFTER",
            self.earliest_time,
            0,
            accent="#6F7DFF",
            width=180
        )

        ctk.CTkLabel(
            time_controls,
            text="to",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color="#78869C"
        ).grid(
            row=0,
            column=1,
            padx=10
        )

        self._control_chip(
            time_controls,
            "BEFORE",
            self.latest_time,
            2,
            accent="#6F7DFF",
            width=180
        )

        # ----------------------------------------------------
        # MORE SETTINGS
        # ----------------------------------------------------
        self.advanced_button = ctk.CTkButton(
            content,
            text="More options  +",
            command=self.toggle_advanced,
            width=112,
            height=32,
            corner_radius=10,
            fg_color="transparent",
            hover_color="#141B28",
            text_color="#8899AF",
            font=ctk.CTkFont(
                size=10,
                weight="bold"
            )
        )
        self.advanced_button.grid(
            row=4,
            column=0,
            sticky="w",
            pady=(2, 8)
        )

        self.advanced_card = ctk.CTkFrame(
            content,
            fg_color="#101722",
            corner_radius=14,
            border_width=1,
            border_color="#2D3E54"
        )
        self.advanced_card.grid(
            row=5,
            column=0,
            sticky="ew",
            pady=(0, 12)
        )

        advanced_inner = ctk.CTkFrame(
            self.advanced_card,
            fg_color="transparent"
        )
        advanced_inner.pack(
            fill="x",
            padx=16,
            pady=14
        )

        ctk.CTkLabel(
            advanced_inner,
            text="CHECK INTERVAL",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            ),
            text_color=self.text_dim
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkEntry(
            advanced_inner,
            textvariable=self.check_interval,
            width=90,
            height=34,
            corner_radius=9,
            fg_color=self.field_bg,
            border_width=1,
            border_color=self.field_border,
            text_color=self.text
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 18),
            pady=(4, 0)
        )

        ctk.CTkSwitch(
            advanced_inner,
            text="Sound alert",
            variable=self.sound_alert,
            progress_color=self.accent,
            button_color="#FFFFFF",
            text_color=self.text_soft
        ).grid(
            row=1,
            column=1,
            padx=(0, 22),
            pady=(4, 0)
        )

        ctk.CTkSwitch(
            advanced_inner,
            text="Open browser on match",
            variable=self.open_browser,
            progress_color=self.blue,
            button_color="#FFFFFF",
            text_color=self.text_soft
        ).grid(
            row=1,
            column=2,
            pady=(4, 0)
        )

        self.advanced_card.grid_remove()

        # ----------------------------------------------------
        # START / WATCH CONTROL
        # ----------------------------------------------------
        action_outer = ctk.CTkFrame(
            content,
            fg_color="#32134E",
            corner_radius=18,
            border_width=1,
            border_color="#B64CFF"
        )
        action_outer.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=(4, 12)
        )
        action_outer.grid_columnconfigure(
            0,
            weight=1
        )

        action = ctk.CTkFrame(
            action_outer,
            fg_color="#0D2232",
            corner_radius=15,
            border_width=1,
            border_color="#00A6D8"
        )
        action.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )
        action.grid_columnconfigure(
            0,
            weight=1
        )

        action_copy = ctk.CTkFrame(
            action,
            fg_color="transparent"
        )
        action_copy.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(18, 12),
            pady=14
        )

        ctk.CTkLabel(
            action_copy,
            text="READY TO WATCH",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            ),
            text_color="#85DFFF"
        ).pack(
            anchor="w"
        )

        ctk.CTkLabel(
            action_copy,
            text="Find me better seats",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            text_color=self.text
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        self.start_button = ctk.CTkButton(
            action,
            text="START WATCHING",
            command=self.start,
            width=220,
            height=54,
            corner_radius=14,
            fg_color="#B53FFF",
            hover_color="#D468FF",
            border_width=1,
            border_color="#E2B3FF",
            text_color="#FFFFFF",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            )
        )
        self.start_button.grid(
            row=0,
            column=1,
            padx=(8, 8),
            pady=10
        )

        self.stop_button = ctk.CTkButton(
            action,
            text="Stop",
            command=self.stop,
            width=68,
            height=54,
            corner_radius=14,
            state="disabled",
            fg_color="#291820",
            hover_color="#3C232E",
            border_width=1,
            border_color="#54303E",
            text_color="#F3B7C4"
        )
        self.stop_button.grid(
            row=0,
            column=2,
            padx=(0, 8),
            pady=10
        )

        self.open_button = ctk.CTkButton(
            action,
            text="Open seats",
            command=self.open_best_match,
            width=92,
            height=54,
            corner_radius=14,
            state="disabled",
            fg_color="#0C382A",
            hover_color="#12533D",
            border_width=1,
            border_color="#176847",
            text_color="#7CFFBF",
            font=ctk.CTkFont(
                size=10,
                weight="bold"
            )
        )
        self.open_button.grid(
            row=0,
            column=3,
            padx=(0, 12),
            pady=10
        )

        # ----------------------------------------------------
        # WATCHING STATUS
        # ----------------------------------------------------
        self.result_card = ctk.CTkFrame(
            content,
            fg_color=self.panel_watch,
            corner_radius=17,
            border_width=1,
            border_color="#2D405B"
        )
        self.result_card.grid(
            row=7,
            column=0,
            sticky="ew"
        )
        self.result_card.grid_columnconfigure(
            0,
            weight=1
        )

        watch_top = ctk.CTkFrame(
            self.result_card,
            fg_color="transparent"
        )
        watch_top.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(15, 4)
        )
        watch_top.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            watch_top,
            text="WATCHING",
            font=ctk.CTkFont(
                size=9,
                weight="bold"
            ),
            text_color="#70D8FF"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.details_button = ctk.CTkButton(
            watch_top,
            text="Activity  ›",
            command=self.toggle_details,
            width=74,
            height=26,
            corner_radius=9,
            fg_color="transparent",
            hover_color="#182539",
            text_color=self.blue,
            font=ctk.CTkFont(size=9)
        )
        self.details_button.grid(
            row=0,
            column=1
        )

        self.result_main = ctk.CTkLabel(
            self.result_card,
            text="Not currently watching",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(
                size=19,
                weight="bold"
            ),
            text_color=self.text
        )
        self.result_main.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18
        )

        self.result_sub = ctk.CTkLabel(
            self.result_card,
            text="Your movie, theaters and seat preferences will appear here when watching starts.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=10),
            text_color=self.text_dim
        )
        self.result_sub.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(4, 10)
        )

        stats = ctk.CTkFrame(
            self.result_card,
            fg_color="#0A111B",
            corner_radius=12,
            border_width=1,
            border_color="#1D3248"
        )
        stats.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=12,
            pady=(0, 12)
        )
        for i in range(4):
            stats.grid_columnconfigure(
                i,
                weight=1
            )

        self._tech_stat(
            stats,
            "CYCLE",
            self.cycle_text,
            0
        )
        self._tech_stat(
            stats,
            "SHOWTIMES",
            self.showtime_text,
            1
        )
        self._tech_stat(
            stats,
            "SEAT GROUPS",
            self.groups_text,
            2
        )
        self._tech_stat(
            stats,
            "LAST SEARCH",
            self.last_cycle_text,
            3
        )

        self.details_card = ctk.CTkFrame(
            content,
            fg_color="#0D121B",
            corner_radius=14,
            border_width=1,
            border_color="#25374E"
        )
        self.details_card.grid(
            row=8,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        self.log = ctk.CTkTextbox(
            self.details_card,
            height=185,
            wrap="word",
            fg_color="#05080D",
            text_color="#D3D9E3",
            font=("Consolas", 10),
            corner_radius=10
        )
        self.log.pack(
            fill="x",
            padx=12,
            pady=12
        )
        self.log.configure(
            state="disabled"
        )

        self.details_card.grid_remove()

        self.on_date_mode_change(
            self.date_mode.get()
        )

    def _draw_ambient_background(self):
        if not hasattr(self, "ambient_canvas"):
            return

        c = self.ambient_canvas
        c.delete("ambient")

        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())

        # Broad, layered color fields. Tkinter has no native blur, so
        # overlapping rounded/oval fields simulate soft atmospheric light.
        purple_layers = [
            (0.34, "#170826"),
            (0.27, "#210B38"),
            (0.20, "#2B0D49"),
            (0.13, "#35105A"),
        ]
        blue_layers = [
            (0.34, "#031923"),
            (0.27, "#042536"),
            (0.20, "#06334A"),
            (0.13, "#07435F"),
        ]

        for frac, color in purple_layers:
            rx = int(w * frac)
            ry = int(h * frac * 0.72)
            c.create_oval(
                -rx // 2,
                -ry // 2,
                rx * 2,
                ry * 2,
                fill=color,
                outline="",
                tags="ambient"
            )

        for frac, color in blue_layers:
            rx = int(w * frac)
            ry = int(h * frac * 0.72)
            c.create_oval(
                w - rx * 2,
                h - ry * 2,
                w + rx // 2,
                h + ry // 2,
                fill=color,
                outline="",
                tags="ambient"
            )

        # Quiet horizon glow behind the centered app shell.
        c.create_rectangle(
            0,
            int(h * 0.30),
            w,
            int(h * 0.72),
            fill="#060B14",
            outline="",
            tags="ambient"
        )

        # Decorative low-opacity-equivalent lines around the app area.
        cx = w // 2
        for offset, color in [
            (640, "#111A2A"),
            (670, "#0B2030"),
            (700, "#160D25"),
        ]:
            c.create_line(
                max(0, cx - offset),
                0,
                max(0, cx - offset),
                h,
                fill=color,
                width=1,
                tags="ambient"
            )
            c.create_line(
                min(w, cx + offset),
                0,
                min(w, cx + offset),
                h,
                fill=color,
                width=1,
                tags="ambient"
            )

        c.tag_lower("ambient")

    def _ambient_resize(self, event=None):
        if getattr(self, "_ambient_job", None):
            try:
                self.root.after_cancel(self._ambient_job)
            except Exception:
                pass
        self._ambient_job = self.root.after(
            45,
            self._draw_ambient_background
        )

    def _modern_panel(
        self,
        parent,
        row,
        title,
        subtitle,
        bg,
        border,
        accent
    ):
        panel = ctk.CTkFrame(
            parent,
            fg_color=bg,
            corner_radius=18,
            border_width=1,
            border_color=border
        )
        panel.grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(0, 14)
        )
        panel.grid_columnconfigure(
            0,
            weight=1
        )

        # Selective highlight instead of a heavy border everywhere.
        light_shelf = ctk.CTkFrame(
            panel,
            height=3,
            fg_color=accent,
            corner_radius=2
        )
        light_shelf.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=28,
            pady=(0, 0)
        )

        heading = ctk.CTkFrame(
            panel,
            fg_color="transparent"
        )
        heading.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(15, 10)
        )
        heading.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkFrame(
            heading,
            width=5,
            height=23,
            corner_radius=3,
            fg_color=accent
        ).grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="ns",
            padx=(0, 10)
        )

        ctk.CTkLabel(
            heading,
            text=title,
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            text_color=self.text
        ).grid(
            row=0,
            column=1,
            sticky="w"
        )

        ctk.CTkLabel(
            heading,
            text=subtitle,
            font=ctk.CTkFont(size=9),
            text_color=self.text_dim
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=(1, 0)
        )

        return panel

    def _control_chip(
        self,
        parent,
        label,
        variable,
        col,
        accent,
        width=160
    ):
        chip = ctk.CTkFrame(
            parent,
            width=width,
            height=68,
            fg_color="#0C121C",
            corner_radius=13,
            border_width=1,
            border_color=accent
        )
        chip.grid(
            row=0,
            column=col,
            padx=(
                (0, 0)
                if col == 0
                else (10, 0)
            )
        )
        chip.grid_propagate(False)

        ctk.CTkLabel(
            chip,
            text=label,
            font=ctk.CTkFont(
                size=8,
                weight="bold"
            ),
            text_color=accent
        ).pack(
            anchor="w",
            padx=12,
            pady=(8, 1)
        )

        ctk.CTkEntry(
            chip,
            textvariable=variable,
            height=30,
            corner_radius=8,
            fg_color="#070B11",
            border_width=0,
            text_color=self.text,
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            )
        ).pack(
            fill="x",
            padx=8,
            pady=(0, 8)
        )

    def _tech_stat(
        self,
        parent,
        title,
        variable,
        col
    ):
        wrap = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )
        wrap.grid(
            row=0,
            column=col,
            sticky="ew",
            pady=9
        )

        ctk.CTkLabel(
            wrap,
            textvariable=variable,
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=(
                self.accent
                if col in (0, 3)
                else self.blue
            )
        ).pack()

        ctk.CTkLabel(
            wrap,
            text=title,
            font=ctk.CTkFont(
                size=8,
                weight="bold"
            ),
            text_color=self.text_dim
        ).pack(
            pady=(1, 0)
        )

    def toggle_theaters(self):
        self.theaters_visible = not self.theaters_visible
        if self.theaters_visible:
            self.theater_panel.grid()
        else:
            self.theater_panel.grid_remove()
        self._refresh_theater_summary()

    def _theater_summary_text(self):
        selected = []
        for theater in self.dynamic_theaters:
            name = theater.get("name", "")
            var = self.theater_vars.get(name)
            try:
                if var and var.get():
                    selected.append(name)
            except Exception:
                pass

        arrow = "⌃" if self.theaters_visible else "›"
        count = len(selected)

        if count == 0:
            return f"No theaters selected   {arrow}"
        if count == 1:
            return f"1 theater · {selected[0]}   {arrow}"

        first = selected[0].replace("AMC ", "")
        return f"{count} theaters · {first} + {count - 1} more   {arrow}"

    def _on_window_resize(self, event):
        if event.widget is self.root:
            self._apply_responsive_width()

    def _apply_responsive_width(self):
        if not hasattr(
            self,
            "app_shell"
        ):
            return

        try:
            window_width = max(
                1,
                self.root.winfo_width()
            )

            # Desired app width:
            # small: almost full width
            # normal: 90% of window
            # large/fullscreen: capped at 1180px
            if window_width < 900:
                target = max(
                    680,
                    window_width - 32
                )
            elif window_width < 1300:
                target = int(
                    window_width * 0.90
                )
            else:
                target = min(
                    1180,
                    int(
                        window_width * 0.84
                    )
                )

            target = max(
                680,
                min(
                    1180,
                    target
                )
            )

            # Because the shell is sticky="ew", padding determines
            # its actual width. This avoids Tk geometry propagation
            # collapsing it back to the content's requested width.
            side_margin = max(
                16,
                int(
                    (window_width - target) / 2
                )
            )

            self.app_shell.grid_configure(
                padx=side_margin
            )

        except Exception:
            pass

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible

        if self.advanced_visible:
            self.advanced_card.grid()
            self.advanced_button.configure(
                text="Hide options  -"
            )
        else:
            self.advanced_card.grid_remove()
            self.advanced_button.configure(
                text="More options  +"
            )

    def _minimal_field(self, parent, label, variable, row, col, values=None):
        ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.text_dim
        ).grid(row=row, column=col, sticky="w", padx=24, pady=(0, 5))

        if values:
            widget = ctk.CTkOptionMenu(
                parent,
                variable=variable,
                values=values,
                height=42,
                corner_radius=12,
                fg_color=self.surface_soft,
                button_color=self.surface_soft,
                button_hover_color=self.surface_hover,
                text_color=self.text
            )
        else:
            widget = ctk.CTkEntry(
                parent,
                textvariable=variable,
                height=42,
                corner_radius=12,
                fg_color=self.surface_soft,
                border_width=0,
                text_color=self.text
            )

        widget.grid(
            row=row+1,
            column=col,
            sticky="ew",
            padx=24,
            pady=(0, 10)
        )

    def _metric(self, parent, title, variable, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.surface,
            corner_radius=18
        )
        card.grid(row=0, column=col, sticky="ew", padx=6)

        ctk.CTkLabel(
            card,
            text=title.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.text_dim
        ).pack(pady=(13, 3))

        value_color = (
            self.accent
            if col in (0, 3)
            else self.cyan
        )

        ctk.CTkLabel(
            card,
            textvariable=variable,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=value_color
        ).pack(pady=(0, 13))

    def toggle_details(self):
        self.details_visible = not self.details_visible

        if self.details_visible:
            self.details_card.grid()
            self.details_button.configure(text="Hide activity")
        else:
            self.details_card.grid_remove()
            self.details_button.configure(text="Activity  ›")

    def render_theaters(self):
        self.dynamic_theaters = clean_theater_list(
            self.dynamic_theaters
        )

        for child in self.theater_grid.winfo_children():
            child.destroy()

        for i, theater in enumerate(
            self.dynamic_theaters
        ):
            name = theater["name"]

            if name not in self.theater_vars:
                self.theater_vars[name] = tk.BooleanVar(
                    value=True
                )

            distance = theater.get(
                "distance"
            )

            label = (
                name
                if distance is None
                else f"{name}   ·   {distance:.1f} mi"
            )

            ctk.CTkCheckBox(
                self.theater_grid,
                text=label,
                variable=self.theater_vars[name],
                checkbox_width=18,
                checkbox_height=18,
                corner_radius=5,
                border_width=1,
                fg_color=self.blue,
                hover_color=self.blue_hover,
                border_color="#3A6A82",
                text_color=self.text_soft,
                command=self._refresh_theater_summary
            ).grid(
                row=i // 2,
                column=i % 2,
                sticky="w",
                padx=8,
                pady=8
            )

        self._refresh_theater_summary()

    def _refresh_theater_summary(self):
        if hasattr(
            self,
            "theater_summary_button"
        ):
            self.theater_summary_button.configure(
                text=self._theater_summary_text()
            )

    def use_my_location(self):
        if (
            self.worker
            and
            self.worker.is_alive()
        ):
            messagebox.showinfo(
                "Watcher Running",
                "Stop the watcher before changing location."
            )
            return

        self.use_location_button.configure(
            state="disabled",
            text="Locating..."
        )

        self.status_text.set(
            "Finding your location..."
        )

        thread = threading.Thread(
            target=self.use_my_location_thread,
            daemon=True
        )
        thread.start()

    def use_my_location_thread(self):
        try:
            result = lookup_current_location()

            self.events.put(
                (
                    "current_location",
                    result
                )
            )

        except Exception as exc:
            self.events.put(
                (
                    "current_location_error",
                    str(exc)
                )
            )

    def find_theaters(self):
        query = self.location_query.get().strip()

        if not query:
            messagebox.showerror(
                "Location Required",
                "Enter a city, ZIP code or address."
            )
            return

        try:
            radius = float(
                self.search_radius.get()
            )
        except Exception:
            messagebox.showerror(
                "Check Radius",
                "Enter a valid search radius."
            )
            return

        if radius <= 0:
            messagebox.showerror(
                "Check Radius",
                "Search radius must be greater than 0."
            )
            return

        if self.worker and self.worker.is_alive():
            messagebox.showinfo(
                "Watcher Running",
                "Stop the watcher before changing the theater list."
            )
            return

        self.find_theaters_button.configure(
            state="disabled",
            text="Searching..."
        )

        self.use_location_button.configure(
            state="disabled"
        )

        self.status_text.set(
            "Finding theaters..."
        )

        self.emit("")
        self.emit(
            f"Finding AMC theaters near: {query}"
        )

        thread = threading.Thread(
            target=self.find_theaters_thread,
            args=(query, radius),
            daemon=True
        )

        thread.start()

    def find_theaters_thread(
        self,
        query,
        radius
    ):
        try:
            result = asyncio.run(
                discover_amc_theaters_for_location(
                    query,
                    radius,
                    emit=self.emit
                )
            )

            self.events.put(
                (
                    "theaters",
                    result
                )
            )

        except Exception as e:
            self.events.put(
                (
                    "theater_error",
                    str(e)
                )
            )

    def get_selected_theaters(self):
        selected = []

        for theater in self.dynamic_theaters:
            name = theater["name"]

            variable = self.theater_vars.get(
                name
            )

            if (
                variable is not None
                and
                variable.get()
            ):
                selected.append(
                    theater
                )

        return selected

    def find_movies(self):
        if (
            self.worker
            and
            self.worker.is_alive()
        ):
            messagebox.showinfo(
                "Watcher Running",
                "Stop the watcher before refreshing the movie list."
            )
            return

        theaters = self.get_selected_theaters()

        if not theaters:
            messagebox.showerror(
                "No Theaters Selected",
                "Select at least one theater first."
            )
            return

        self.find_movies_button.configure(
            state="disabled",
            text="Searching..."
        )

        self.status_text.set(
            "Finding movies..."
        )

        self.emit("")
        self.emit(
            f"Finding movies at {len(theaters)} selected theaters..."
        )

        thread = threading.Thread(
            target=self.find_movies_thread,
            args=(theaters,),
            daemon=True
        )

        thread.start()

    def find_movies_thread(
        self,
        theaters
    ):
        try:
            movies = asyncio.run(
                discover_movies_for_theaters(
                    theaters,
                    emit=self.emit
                )
            )

            self.events.put(
                (
                    "movies",
                    movies
                )
            )

        except Exception as e:
            self.events.put(
                (
                    "movie_error",
                    str(e)
                )
            )

    def on_date_mode_change(
        self,
        value
    ):
        mode = str(
            value
        ).upper().strip()

        if mode == "NEXT BEST":
            self.date_fields.grid_remove()

        elif mode == "SPECIFIC DATE":
            self.date_fields.grid()
            self.date_start_entry.grid()
            self.date_end_entry.grid_remove()

        else:
            self.date_fields.grid()
            self.date_start_entry.grid()
            self.date_end_entry.grid()

    def emit(self, text):
        self.events.put(("log", str(text)))

    def set_status(self, text):
        self.events.put(("status", str(text)))

    def on_match(self, match):
        self.current_best_match = match
        self.events.put(("match", match))

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        try:
            self.log.update_idletasks()
        except Exception:
            pass

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _date_to_iso(self, value):
        value = str(value or "").strip()
        if not value:
            return ""
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(
                    value,
                    fmt
                ).date().isoformat()
            except ValueError:
                pass
        return value

    def collect_settings(self):
        enabled_theaters = [
            name
            for name, var in self.theater_vars.items()
            if var.get()
        ]

        settings = dict(DEFAULT_SETTINGS)
        settings.update({
            "search_center_name": self.saved.get(
                "search_center_name",
                DEFAULT_SETTINGS["search_center_name"]
            ),
            "search_lat": self.saved.get(
                "search_lat",
                DEFAULT_SETTINGS["search_lat"]
            ),
            "search_lon": self.saved.get(
                "search_lon",
                DEFAULT_SETTINGS["search_lon"]
            ),
            "movie": self.movie.get().strip(),
            "format": self.format.get().strip(),
            "earliest_time": self.earliest_time.get().strip(),
            "latest_time": self.latest_time.get().strip(),
            "date_mode": self.date_mode.get().strip(),
            "date_start": self._date_to_iso(self.date_start.get()),
            "date_end": self._date_to_iso(self.date_end.get()),
            "next_best_days": 7,
            "seats_required": int(self.seats_required.get()),
            "minimum_row": int(self.minimum_row.get()),
            "search_radius_miles": float(self.search_radius.get()),
            "check_interval": int(self.check_interval.get()),
            "sound_alert": bool(self.sound_alert.get()),
            "open_browser_on_match": bool(self.open_browser.get()),
            "enabled_theaters": enabled_theaters,
            "location_query": self.location_query.get().strip(),
            "theaters": self.dynamic_theaters,
        })
        return settings

    def validate_settings(self, settings):
        if not settings["movie"]:
            raise ValueError("Movie name is required.")

        if time_to_minutes(settings["earliest_time"]) is None:
            raise ValueError("Use an earliest time such as 1:00pm.")

        if time_to_minutes(settings["latest_time"]) is None:
            raise ValueError("Use a latest time such as 7:15pm.")

        mode = str(
            settings.get(
                "date_mode",
                "NEXT BEST"
            )
        ).upper().strip()

        if mode == "SPECIFIC DATE":
            selected_date = parse_date_value(
                settings.get(
                    "date_start",
                    ""
                )
            )

            if selected_date is None:
                raise ValueError(
                    "Enter the specific date as MM/DD/YYYY or MM/DD/YYYY."
                )

        elif mode == "DATE RANGE":
            start_value = parse_date_value(
                settings.get(
                    "date_start",
                    ""
                )
            )

            end_value = parse_date_value(
                settings.get(
                    "date_end",
                    ""
                )
            )

            if (
                start_value is None
                or
                end_value is None
            ):
                raise ValueError(
                    "Enter valid start and end dates."
                )

            if end_value < start_value:
                raise ValueError(
                    "End date must be on or after start date."
                )

            span = (
                end_value - start_value
            ).days + 1

            if span > MAX_DATE_RANGE_DAYS:
                raise ValueError(
                    f"Date ranges can be up to "
                    f"{MAX_DATE_RANGE_DAYS} days."
                )

        if settings["seats_required"] < 1:
            raise ValueError("Seats must be at least 1.")

        if settings["minimum_row"] < 1:
            raise ValueError("Minimum row must be at least 1.")

        if settings["search_radius_miles"] <= 0:
            raise ValueError("Radius must be greater than 0.")

        if settings["check_interval"] < 1:
            raise ValueError("Check interval must be at least 1 second.")

        if not settings["enabled_theaters"]:
            raise ValueError("Select at least one theater.")

    def start(self):
        if self.worker and self.worker.is_alive():
            return

        try:
            settings = self.collect_settings()
            self.validate_settings(settings)
        except Exception as e:
            messagebox.showerror("Check Settings", str(e))
            return

        save_settings(settings)

        self.stop_event.clear()
        self.current_best_match = None
        self.clear_log()

        self.result_main.configure(
            text="Searching...",
            text_color=self.text
        )
        self.result_sub.configure(
            text="V44 is checking showtimes and ranking qualifying seats.",
            text_color=self.text_soft
        )
        self.open_button.configure(state="disabled")

        self.status_text.set("Starting...")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.worker = threading.Thread(
            target=self.run_engine_thread,
            args=(settings,),
            daemon=True
        )
        self.worker.start()

    def run_engine_thread(self, settings):
        try:
            engine = WatcherEngine(
                settings=settings,
                emit=self.emit,
                status=self.set_status,
                stop_event=self.stop_event,
                match_callback=self.on_match
            )

            asyncio.run(engine.run())

            self.events.put(("done", "Stopped" if self.stop_event.is_set() else "Finished"))

        except Exception as e:
            self.events.put(("error", str(e)))

    def stop(self):
        self.stop_event.set()
        self.status_text.set("Stopping...")
        self.stop_button.configure(state="disabled")

    def open_best_match(self):
        if not self.current_best_match:
            return

        url = self.current_best_match.get("url")
        if not url:
            return

        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Could Not Open Seats", str(e))

    def process_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()

                if kind == "log":
                    self.append_log(value)
                    upper = value.upper()

                    if "NEW SEARCH CYCLE #" in upper:
                        m = re.search(r"NEW SEARCH CYCLE #(\d+)", upper)
                        if m:
                            self.cycle_text.set(m.group(1))
                        self.groups_text.set("0")

                    elif "NEXT BEST DATE #" in upper:
                        m = re.search(r"NEXT BEST DATE #(\d+)", upper)
                        if m:
                            self.cycle_text.set(m.group(1))
                        self.groups_text.set("0")

                    elif "QUALIFYING SHOWTIMES:" in upper:
                        m = re.search(r"QUALIFYING SHOWTIMES:\s*(\d+)", upper)
                        if m:
                            self.showtime_text.set(m.group(1))

                    elif upper.startswith("FOUND:"):
                        try:
                            self.groups_text.set(str(int(self.groups_text.get()) + 1))
                        except Exception:
                            self.groups_text.set("1")

                    elif "SEARCH CYCLE TIME:" in upper:
                        m = re.search(r"SEARCH CYCLE TIME:\s*([0-9.]+)S", upper)
                        if m:
                            self.last_cycle_text.set(m.group(1) + "s")

                    if (
                        not self.current_best_match
                        and value.strip()
                        and not value.startswith("=")
                    ):
                        try:
                            self.result_sub.configure(
                                text=value.strip()[-220:],
                                text_color=self.text_soft
                            )
                        except Exception:
                            pass

                elif kind == "status":
                    self.status_text.set(value)

                elif kind == "match":
                    match = value
                    self.current_best_match = match

                    self.result_main.configure(
                        text=(
                            f"{match['theater']}\n"
                            f"{display_date(match.get('date', ''))}  •  "
                            f"{match['time']}  •  {match['format']}"
                        ),
                        text_color=self.green
                    )

                    self.result_sub.configure(
                        text=(
                            f"ROW {match['seat_row']}    "
                            f"{'   '.join(match['seats'])}\n"
                            f"{match['distance']:.2f} miles away   •   "
                            f"Center score {match['center_score']:.2f}"
                        ),
                        text_color=self.text
                    )

                    self.open_button.configure(state="normal")
                    self.status_text.set("SEATS FOUND")

                elif kind == "movies":
                    movies = value

                    self.movie_options = list(
                        movies
                    )

                    current = self.movie.get().strip()

                    values = list(
                        self.movie_options
                    )

                    if (
                        current
                        and
                        current not in values
                    ):
                        values.insert(
                            0,
                            current
                        )

                    self.movie_combo.configure(
                        values=values
                    )

                    # If current title is not part of newly discovered movies,
                    # select the first movie so the picker visibly updates.
                    if (
                        self.movie_options
                        and
                        current not in self.movie_options
                    ):
                        self.movie.set(
                            self.movie_options[0]
                        )

                    self.find_movies_button.configure(
                        state="normal",
                        text="Find movies"
                    )

                    self.status_text.set(
                        f"{len(self.movie_options)} movies found"
                    )

                    self.append_log(
                        f"Movie picker updated with "
                        f"{len(self.movie_options)} unique titles."
                    )

                    try:
                        save_settings(
                            self.collect_settings()
                        )
                    except Exception:
                        pass

                elif kind == "movie_error":
                    self.find_movies_button.configure(
                        state="normal",
                        text="Find movies"
                    )

                    self.status_text.set(
                        "Movie search failed"
                    )

                    messagebox.showerror(
                        "Could Not Find Movies",
                        value
                    )

                elif kind == "current_location":
                    result = value

                    self.location_query.set(
                        result["query"]
                    )

                    self.use_location_button.configure(
                        state="normal",
                        text="Use my location"
                    )

                    self.status_text.set(
                        "Location found"
                    )

                    self.append_log(
                        "Current location: "
                        + result["query"]
                    )

                    # Continue automatically into theater discovery so
                    # "Use my location" is a true one-click action.
                    self.find_theaters()

                elif kind == "current_location_error":
                    self.use_location_button.configure(
                        state="normal",
                        text="Use my location"
                    )

                    self.status_text.set(
                        "Location unavailable"
                    )

                    messagebox.showerror(
                        "Could Not Determine Location",
                        value
                    )

                elif kind == "theaters":
                    result = value

                    self.dynamic_theaters = clean_theater_list(
                        result["theaters"]
                    )

                    self.theater_vars = {
                        theater["name"]:
                            tk.BooleanVar(
                                value=True
                            )
                        for theater
                        in self.dynamic_theaters
                    }

                    self.location_query.set(
                        result["location_query"]
                    )

                    # Persist the new search center immediately.
                    self.saved["search_center_name"] = (
                        result["display_name"]
                    )
                    self.saved["search_lat"] = (
                        result["lat"]
                    )
                    self.saved["search_lon"] = (
                        result["lon"]
                    )
                    self.saved["location_query"] = (
                        result["location_query"]
                    )
                    self.saved["theaters"] = (
                        self.dynamic_theaters
                    )
                    self.saved["enabled_theaters"] = [
                        t["name"]
                        for t in self.dynamic_theaters
                    ]

                    self.render_theaters()

                    # The available movie list belongs to the old theater set.
                    self.movie_options = []

                    self.movie_combo.configure(
                        values=[
                            self.movie.get().strip()
                        ]
                    )

                    try:
                        save_settings(
                            {
                                **self.collect_settings(),
                                "search_center_name":
                                    result["display_name"],
                                "search_lat":
                                    result["lat"],
                                "search_lon":
                                    result["lon"],
                            }
                        )
                    except Exception:
                        pass

                    self.find_theaters_button.configure(
                        state="normal",
                        text="Find theaters"
                    )

                    self.use_location_button.configure(
                        state="normal",
                        text="Use my location"
                    )

                    self.status_text.set(
                        f"{len(self.dynamic_theaters)} theaters found"
                    )

                    self.append_log(
                        f"Saved {len(self.dynamic_theaters)} theaters "
                        "for this location."
                    )

                elif kind == "theater_error":
                    self.find_theaters_button.configure(
                        state="normal",
                        text="Find theaters"
                    )

                    self.use_location_button.configure(
                        state="normal",
                        text="Use my location"
                    )

                    self.status_text.set(
                        "Theater search failed"
                    )

                    messagebox.showerror(
                        "Could Not Find Theaters",
                        value
                    )

                elif kind == "done":
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")

                    if self.current_best_match:
                        # A match remains a match even after the visible purchase
                        # browser is later closed and the worker thread exits.
                        self.status_text.set("SEATS FOUND")

                    elif value == "Stopped":
                        self.status_text.set("Stopped")
                        try:
                            self.result_main.configure(
                                text="Watch stopped",
                                text_color=self.text
                            )
                            self.result_sub.configure(
                                text="The search was stopped before a qualifying seat match was selected.",
                                text_color=self.text_soft
                            )
                        except Exception:
                            pass

                    else:
                        final_reason = self.status_text.get().strip()
                        active_labels = {
                            "Starting...", "Checking seats...",
                            "Refreshing showtimes...", "Finished",
                        }
                        if (
                            not final_reason
                            or final_reason in active_labels
                            or final_reason.startswith("Next Best:")
                            or final_reason.startswith("Search cycle #")
                        ):
                            final_reason = (
                                "Search completed without finding seats that match all of the selected criteria."
                            )

                        self.status_text.set("NO MATCH")
                        try:
                            self.result_main.configure(
                                text="No matching seats found",
                                text_color=self.text
                            )
                            self.result_sub.configure(
                                text=final_reason,
                                text_color=self.text_soft
                            )
                        except Exception:
                            pass

                elif kind == "error":
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.status_text.set("Error")

                    messagebox.showerror("Watcher Error", value)

        except queue.Empty:
            pass

        self.root.after(100, self.process_events)

    def on_close(self):
        if self.worker and self.worker.is_alive():
            answer = messagebox.askyesno(
                "Close Universal Watcher Movies?",
                "The watcher is still running.\n\nStop it and close?"
            )
            if not answer:
                return
            self.stop_event.set()

        try:
            save_settings(self.collect_settings())
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    root = ctk.CTk()
    SeatWatcherGUI(root)
    root.mainloop()
