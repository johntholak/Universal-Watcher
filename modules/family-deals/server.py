from __future__ import annotations

import html
import json
import re
import hashlib
import threading
import time
import uuid
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36 HUNT/0.4.1"
)
FETCH_TIMEOUT = 5.5
MAX_BYTES = 1_500_000
MAX_PAGES_PER_SOURCE = 3
MAX_WORKERS = 24
RESOLVE_WORKERS = 20
PARSER_VERSION = "5.0.1-hours"
SOURCE_CACHE_TTL = 6 * 60 * 60
WIKIDATA_CACHE_TTL = 7 * 24 * 60 * 60
CACHE_DIR = Path.home() / ".hunt_cache"
CACHE_LOCK = threading.Lock()
FAMILY_MIN_SERVES = 4
FAMILY_MAX_SERVES = 10

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

PRICE_RE = re.compile(r"\$\s*([0-9]{1,4}(?:\.[0-9]{1,2})?)")

# V4.1 is deliberately conservative. A dollar amount is not a deal just because it
# appears near the word "family". We require a meal/package concept, bind the price
# to that concept, and reject common misleading price contexts.
STRONG_ITEM_PHRASES = (
    "family meal", "family meals", "family bundle", "family bundles", "family pack",
    "family packs", "family feast", "family dinner", "family deal", "family deals",
    "meal for 4", "meal for four", "meal for 5", "meal for five", "meal for 6",
    "meal for six", "dinner for 4", "dinner for four", "dinner for 5", "dinner for five",
    "dinner for 6", "dinner for six", "take home meal", "take-home meal", "group meal",
    "party pack", "dinner box", "meal bundle", "meal package",
)
STRUCTURED_MEAL_WORDS = (
    "meal", "dinner", "feast", "bundle", "pack", "package", "combo", "box",
)
MEAL_COMPONENT_WORDS = (
    "entree", "entrée", "main", "chicken", "pizza", "pasta", "sandwich", "sub",
    "taco", "tacos", "burger", "burgers", "protein", "rice", "beans", "sides",
)
PRICE_REJECT_TERMS = (
    "delivery fee", "delivery charge", "service fee", "service charge", "additional charge",
    "surcharge", "processing fee", "convenience fee", "tax", "deposit", "gratuity",
    "coupon", "coupon off", "discount", "discounted price", "original price", "save $",
    "savings", "reward", "gift card", "membership", "upgrade", "add-on", "addon",
)
UNCERTAIN_PRICE_TERMS = (
    "starting at", "starts at", "start at", "from $", "as low as", "under $", "less than $",
    "around $", "about $", "approximately $", "approx. $", "up to $",
)
UNAVAILABLE_TERMS = (
    "not available", "unavailable", "excluded locations", "excludes locations",
    "participating locations only", "select locations only", "where available",
)
REVIEW_TERMS = (
    "i used", "i ordered", "we ordered", "i paid", "we paid", "my order", "our order",
    "review", "reviews", "customer said", "customer review", "testimonial",
)
SIDE_ONLY_TERMS = (
    "side salad", "pasta salad", "garden salad", "caesar salad", "breadsticks only",
    "side dish", "side order", "full tray", "half tray", "dessert tray", "beverage",
)
PER_PERSON_RE = re.compile(r"(?:per\s+person|/\s*person|each\s+person)", re.I)
EVENT_PACKAGE_TERMS = (
    "birthday", "birthday party", "party room", "party host", "reserved table",
    "play points", "game play", "gameplay", "game card", "arcade", "tokens",
    "unlimited games", "birthday child", "party guests", "event space",
)
TAKEHOME_MEAL_TERMS = (
    "family meal", "family dinner", "family feast", "meal bundle", "meal package",
    "take home", "take-home", "takeout", "take-out", "carryout", "to go", "dinner box",
)

LINK_KEYWORDS = (
    "family", "bundle", "catering", "menu", "deal", "special", "order", "takeout",
    "take-out", "party", "group", "dinner", "meal", "packages",
)
SKIP_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip", ".mp4",
    ".mov", ".avi", ".css", ".js", ".woff", ".woff2", ".ttf",
)


def clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    return url


def safe_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def root_domain(host: str) -> str:
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _cache_file(kind: str, key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()
    return CACHE_DIR / kind / f"{digest}.json"


def cache_get(kind: str, key: str, ttl: float) -> Any | None:
    path = _cache_file(kind, key)
    try:
        with CACHE_LOCK:
            data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("saved_at", 0)) > ttl:
            return None
        return data.get("value")
    except Exception:
        return None


def cache_set(kind: str, key: str, value: Any) -> None:
    path = _cache_file(kind, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        payload = {"saved_at": time.time(), "value": value}
        with CACHE_LOCK:
            temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temp.replace(path)
    except Exception:
        pass


def crawl_cache_key(url: str, people: int) -> str:
    # Budget is intentionally omitted: crawl with a high ceiling and apply the user budget
    # afterward so changing $50 to $60 can reuse the same fresh source evidence.
    return f"{PARSER_VERSION}|{normalize_url(url)}|people={people}"


def json_get(url: str, timeout: int = FETCH_TIMEOUT) -> Any:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.5",
            "Accept-Encoding": "identity",
        },
    )
    with urlopen(req, timeout=timeout) as r:
        raw = r.read(MAX_BYTES)
    return json.loads(raw.decode("utf-8", errors="replace"))


class PageParser(HTMLParser):
    BLOCKS = {
        "address", "article", "aside", "blockquote", "br", "button", "div", "dl", "dt",
        "dd", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
        "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "tbody", "td", "th", "thead", "tr", "ul",
    }

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._anchor_href = ""
        self._anchor_text: list[str] = []
        self._skip_depth = 0
        self._json_script = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag in ("style", "noscript"):
            self._skip_depth += 1
        elif tag == "script":
            t = a.get("type", "").lower()
            self._json_script = "json" in t
            if not self._json_script:
                self._skip_depth += 1
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "a":
            self._anchor_href = a.get("href", "")
            self._anchor_text = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("style", "noscript") and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "script":
            if self._json_script:
                self._json_script = False
            elif self._skip_depth:
                self._skip_depth -= 1
        if tag == "a" and self._anchor_href:
            href = urljoin(self.base_url, self._anchor_href)
            text = clean_space(" ".join(self._anchor_text))
            self.links.append((href, text))
            self._anchor_href = ""
            self._anchor_text = []
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        s = clean_space(data)
        if not s:
            return
        self.parts.append(s)
        self.parts.append(" ")
        if self._anchor_href:
            self._anchor_text.append(s)

    def lines(self) -> list[str]:
        text = html.unescape("".join(self.parts))
        lines = [clean_space(x) for x in text.splitlines()]
        return [x for x in lines if len(x) >= 2]


def fetch_page(url: str) -> tuple[str, list[str], list[tuple[str, str]]]:
    req = Request(
        normalize_url(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(req, timeout=FETCH_TIMEOUT) as r:
        final_url = r.geturl()
        ctype = (r.headers.get("content-type") or "").lower()
        raw = r.read(MAX_BYTES)
    if "html" not in ctype and "json" not in ctype and not raw.lstrip().startswith((b"<", b"{", b"[")):
        return final_url, [], []
    text = raw.decode("utf-8", errors="replace")
    if "json" in ctype and not text.lstrip().startswith("<"):
        plain = clean_space(text)
        return final_url, [plain] if plain else [], []
    parser = PageParser(final_url)
    parser.feed(text)
    return final_url, parser.lines(), parser.links


def score_link(href: str, anchor: str, official_url: str) -> int:
    try:
        p = urlparse(href)
    except Exception:
        return -999
    if p.scheme not in ("http", "https") or not p.hostname:
        return -999
    lower = (href + " " + anchor).lower()
    if any(p.path.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
        return -999
    score = sum(3 for kw in LINK_KEYWORDS if kw in lower)
    official_host = safe_host(official_url)
    h = safe_host(href)
    if root_domain(h) == root_domain(official_host):
        score += 5
    elif any(k in lower for k in ("order", "menu", "catering")):
        score += 1
    else:
        return -999
    if "privacy" in lower or "terms" in lower or "careers" in lower or "franchise" in lower:
        score -= 8
    return score


def parse_capacity_range(text: str) -> tuple[int, int] | None:
    low = text.lower()

    # Explicit numeric ranges such as "serves 4-6" or "feeds 4 to 6".
    range_patterns = (
        r"(?:feeds|serves)\s+(?:approximately\s+)?(\d{1,2})\s*(?:[-–]|to)\s*(\d{1,2})",
        r"(?:for)\s+(\d{1,2})\s*(?:[-–]|to)\s*(\d{1,2})\s+(?:people|persons|guests|adults|kids)",
    )
    for pat in range_patterns:
        m = re.search(pat, low)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return (min(a, b), max(a, b))

    single_patterns = (
        r"(?:feeds|serves)\s+(?:approximately\s+)?(\d{1,2})",
        r"(?:feeds|serves)\s+(?:multiples\s+of\s+)?(\d{1,2})",
        r"(?:for)\s+(\d{1,2})\s+(?:people|persons|guests|adults|kids)?",
        r"(\d{1,2})\s+(?:people|persons|guests)\b",
    )
    for pat in single_patterns:
        m = re.search(pat, low)
        if m:
            try:
                n = int(m.group(1))
                return (n, n)
            except ValueError:
                pass

    words = {
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "twelve": 12,
    }
    m = re.search(r"(?:feeds|serves|for)\s+(two|three|four|five|six|seven|eight|nine|ten|twelve)\b", low)
    if m:
        n = words[m.group(1)]
        return (n, n)
    return None


def parse_capacity(text: str) -> int | None:
    """Backward-compatible single capacity: use the maximum advertised serving size."""
    rng = parse_capacity_range(text)
    return rng[1] if rng else None


def has_strong_meal_anchor(text: str) -> bool:
    low = text.lower()
    # "Family restaurant" is a restaurant description/name, not a family meal.
    if "family restaurant" in low and not any(p in low for p in STRONG_ITEM_PHRASES):
        low = low.replace("family restaurant", "")
    if any(p in low for p in STRONG_ITEM_PHRASES):
        return True
    # Allow a clearly structured meal/package even when the word family is absent,
    # but only when it also has an explicit serving count.
    if parse_capacity(low) is not None and any(w in low for w in STRUCTURED_MEAL_WORDS):
        if "includes" in low and any(w in low for w in MEAL_COMPONENT_WORDS):
            return True
    return False


def split_clauses(text: str) -> list[str]:
    text = clean_space(text)
    if not text:
        return []
    # Preserve dollar decimals while splitting obvious menu/list boundaries.
    raw = re.split(r"\s*\|\s*|(?<=[!?])\s+|\s+[•·]\s+", text)
    return [clean_space(x) for x in raw if clean_space(x)]


def price_context_is_bad(context: str) -> tuple[bool, str]:
    low = context.lower()
    if any(t in low for t in PRICE_REJECT_TERMS):
        return True, "fee/discount/coupon"
    if any(t in low for t in UNCERTAIN_PRICE_TERMS):
        return True, "non-exact price"
    if any(t in low for t in UNAVAILABLE_TERMS):
        return True, "availability exclusion"
    if any(t in low for t in REVIEW_TERMS):
        return True, "review/anecdote"
    return False, ""


def capacity_range_near_anchor(text: str, anchor_pos: int, radius: int = 180) -> tuple[int, int] | None:
    lo = max(0, anchor_pos - radius)
    hi = min(len(text), anchor_pos + radius)
    return parse_capacity_range(text[lo:hi])


def analyze_deals(lines: list[str], url: str, budget: float, people: int) -> dict[str, Any]:
    deals: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    seen: set[tuple[str, int]] = set()

    def reject(reason: str) -> None:
        rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    # Work with local three-line windows, then with smaller clauses inside them.
    # This keeps a price tied to an item instead of sweeping every dollar amount
    # from a broad family-related paragraph.
    for i in range(len(lines)):
        window = clean_space(" | ".join(lines[max(0, i - 1): min(len(lines), i + 2)]))
        if not window:
            continue
        if len(window) > 1400:
            window = window[:1400]
        clauses = split_clauses(window)
        if not clauses:
            continue

        for ci, clause in enumerate(clauses):
            if not has_strong_meal_anchor(clause):
                continue
            clause_low = clause.lower()
            if "frequently asked questions" in window.lower() or " faq " in f" {window.lower()} " or clause.rstrip().endswith("?"):
                reject("faq/general copy")
                continue

            # Consider a compact item block around the anchor. Three neighbors covers common
            # markup such as Title | Serves 6 | Includes... | $Price without sweeping the page.
            local_parts = clauses[max(0, ci - 3): min(len(clauses), ci + 4)]
            local = clean_space(" | ".join(local_parts))
            if not has_strong_meal_anchor(local):
                continue

            anchor_low = local.lower()

            # Birthday/event packages are not dinner deals. A food "party pack" may still
            # qualify, but entertainment/event language must be accompanied by clear
            # take-home meal language before HUNT will consider it.
            if any(t in anchor_low for t in EVENT_PACKAGE_TERMS) and not any(
                t in anchor_low for t in TAKEHOME_MEAL_TERMS
            ):
                reject("event/party package")
                continue

            anchor_positions = [anchor_low.find(p) for p in STRONG_ITEM_PHRASES if anchor_low.find(p) >= 0]
            if not anchor_positions:
                # Structured non-family package anchor.
                anchor_positions = [max(0, len(local) // 2)]
            anchor_pos = min(anchor_positions)

            # A single side/tray cannot become a full family dinner merely because it serves many.
            if any(t in anchor_low for t in SIDE_ONLY_TERMS) and not any(
                p in anchor_low for p in ("family meal", "family dinner", "family feast", "meal package", "meal bundle")
            ):
                reject("side-only item")
                continue

            price_matches = list(PRICE_RE.finditer(local))
            if not price_matches:
                continue

            # Evaluate each price independently and rank by distance to the actual meal anchor.
            ranked_prices = sorted(price_matches, key=lambda m: abs(m.start() - anchor_pos))
            accepted_for_anchor = False
            for pm in ranked_prices:
                listed_price = float(pm.group(1))
                if listed_price <= 0:
                    continue
                # Judge fee/discount/etc. against the price's own menu clause, not the
                # whole item block. This keeps a legitimate $35 meal from being rejected
                # merely because the next clause says "delivery fee $4".
                left = local.rfind(" | ", 0, pm.start())
                right = local.find(" | ", pm.end())
                pc_lo = 0 if left < 0 else left + 3
                pc_hi = len(local) if right < 0 else right
                price_context = local[pc_lo:pc_hi]
                bad, reason = price_context_is_bad(price_context)
                if bad:
                    reject(reason)
                    continue

                # Do not let a price from a different menu item piggyback on the anchor.
                if abs(pm.start() - anchor_pos) > 360:
                    reject("price too far from meal item")
                    continue

                capacity_range = capacity_range_near_anchor(local, anchor_pos)
                capacity_min = capacity_range[0] if capacity_range else None
                capacity_max = capacity_range[1] if capacity_range else None
                capacity = capacity_max
                capacity_label = (
                    str(capacity_min) if capacity_range and capacity_min == capacity_max
                    else f"{capacity_min}-{capacity_max}" if capacity_range
                    else ""
                )
                price_mode = "package"
                effective_total = listed_price

                # Family-size means the advertised serving range overlaps 4 through 10.
                # A request for 4 may therefore match a meal for 5, 6, 8, or 10.
                family_size = bool(
                    capacity_range
                    and capacity_max >= FAMILY_MIN_SERVES
                    and capacity_min <= FAMILY_MAX_SERVES
                )
                covers_party = bool(capacity_range and capacity_max >= people)

                if capacity_range and not family_size:
                    reject("outside family-size range")
                    continue
                if capacity_range and not covers_party:
                    reject("serves too few")
                    continue

                if PER_PERSON_RE.search(price_context):
                    price_mode = "per_person"
                    if capacity_range is None:
                        reject("per-person price without group size")
                        continue
                    # Charge the minimum headcount the offer itself requires, but never fewer
                    # than the user's party. Example: serves 6 at $10/person costs at least $60
                    # even when the user only needs dinner for four.
                    billed_people = max(people, capacity_min, FAMILY_MIN_SERVES)
                    if billed_people > capacity_max:
                        reject("serves too few")
                        continue
                    effective_total = round(listed_price * billed_people, 2)

                if effective_total > budget:
                    reject("over budget")
                    continue

                # A full match requires explicit family-size serving evidence that covers
                # the requested party. It does NOT require an exact party-size match.
                capacity_verified = family_size and covers_party

                evidence = local[:420]
                normalized = re.sub(r"[^a-z0-9]+", " ", evidence.lower())[:180]
                key = (normalized, int(round(effective_total * 100)))
                if key in seen:
                    continue
                seen.add(key)
                deals.append({
                    "price": round(effective_total, 2),
                    "listed_price": round(listed_price, 2),
                    "price_mode": price_mode,
                    "capacity": capacity,
                    "capacity_min": capacity_min,
                    "capacity_max": capacity_max,
                    "capacity_label": capacity_label,
                    "capacity_verified": capacity_verified,
                    "evidence": evidence,
                    "source_url": url,
                    "score": 20 + (6 if capacity_verified else 0) - min(8, abs(pm.start() - anchor_pos) // 35),
                })
                accepted_for_anchor = True
                break

            if not accepted_for_anchor and ranked_prices:
                # Individual rejection reasons above explain why.
                pass

    deals.sort(key=lambda d: (not d["capacity_verified"], -d["score"], d["price"]))
    return {"deals": deals[:12], "rejections": rejection_counts}


def resolve_wikidata(ids: list[str]) -> str:
    for qid in ids:
        if not re.fullmatch(r"Q\d+", qid or ""):
            continue
        cache_key = f"wikidata-homepage|{qid}"
        cached = cache_get("wikidata", cache_key, WIKIDATA_CACHE_TTL)
        if isinstance(cached, str):
            if cached:
                return cached
            continue
        found = ""
        try:
            data = json_get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")
            claims = data.get("entities", {}).get(qid, {}).get("claims", {})
            for claim in claims.get("P856", []):
                value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    found = value
                    break
        except Exception:
            # Do not cache transient failures.
            continue
        cache_set("wikidata", cache_key, found)
        if found:
            return found
    return ""


def crawl_official_source(url: str, budget: float, people: int) -> dict[str, Any]:
    url = normalize_url(url)
    errors: list[str] = []
    all_deals: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    pages_checked = 0

    def add_analysis(page_url: str, lines: list[str]) -> bool:
        nonlocal pages_checked
        pages_checked += 1
        analyzed = analyze_deals(lines, page_url, budget, people)
        all_deals.extend(analyzed.get("deals") or [])
        for reason, count in (analyzed.get("rejections") or {}).items():
            rejection_counts[reason] = rejection_counts.get(reason, 0) + int(count)
        return any(bool(d.get("capacity_verified")) for d in (analyzed.get("deals") or []))

    try:
        final_home, home_lines, links = fetch_page(url)
    except Exception as exc:
        return {"status": "blocked", "source_url": url, "pages_checked": 0, "deals": [], "error": type(exc).__name__}

    # Analyze immediately. If a page itself proves a qualifying family meal, do not
    # keep crawling the same restaurant just to collect redundant evidence.
    verified_found = add_analysis(final_home, home_lines)

    ranked: list[tuple[int, str]] = []
    seen_urls = {final_home.split("#", 1)[0]}
    for href, anchor in links:
        href = href.split("#", 1)[0]
        score = score_link(href, anchor, final_home)
        if score > 0 and href not in seen_urls:
            ranked.append((score, href))
    ranked.sort(key=lambda x: (-x[0], len(x[1])))

    if not verified_found:
        for _, href in ranked[: MAX_PAGES_PER_SOURCE - 1]:
            if href in seen_urls:
                continue
            seen_urls.add(href)
            try:
                page_url, lines, _ = fetch_page(href)
                if add_analysis(page_url, lines):
                    break
            except Exception as exc:
                errors.append(type(exc).__name__)

    deduped: list[dict[str, Any]] = []
    seen_deals: set[tuple[int, str]] = set()
    for d in sorted(all_deals, key=lambda x: (-x["score"], x["price"])):
        key = (int(round(d["price"] * 100)), re.sub(r"[^a-z0-9]+", " ", d["evidence"].lower())[:120])
        if key not in seen_deals:
            seen_deals.add(key)
            deduped.append(d)
    return {
        "status": "checked",
        "source_url": final_home,
        "pages_checked": pages_checked,
        "deals": deduped[:12],
        "rejections": rejection_counts,
        "error": ",".join(errors[:3]),
    }


DAY_INDEX = {
    "Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6,
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6,
}


def expand_days(spec: str) -> set[int]:
    out: set[int] = set()
    for token in [x.strip() for x in spec.split(",") if x.strip()]:
        if "-" in token:
            a, b = token.split("-", 1)
            if a in DAY_INDEX and b in DAY_INDEX:
                i, j = DAY_INDEX[a], DAY_INDEX[b]
                while True:
                    out.add(i)
                    if i == j:
                        break
                    i = (i + 1) % 7
        elif token in DAY_INDEX:
            out.add(DAY_INDEX[token])
    return out


def _parse_clock(value: str) -> int | None:
    """Parse a conservative 12-hour or 24-hour clock value."""
    value = value.strip().lower().replace(" ", "")
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(am|pm)?", value)
    if not match:
        # OSM also permits compact values such as 1130 or 2200.
        compact = re.fullmatch(r"(\d{3,4})", value)
        if compact:
            digits = compact.group(1).zfill(4)
            hour, minute = int(digits[:2]), int(digits[2:])
            return hour * 60 + minute if hour <= 23 and minute <= 59 else None
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)
    if minute > 59:
        return None
    if meridiem:
        if hour < 1 or hour > 12:
            return None
        if meridiem == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12
    elif hour > 24 or (hour == 24 and minute != 0):
        return None
    return hour * 60 + minute


def _parse_opening_span(value: str) -> tuple[int, int] | None:
    value = value.strip().replace("–", "-").replace("—", "-")
    match = re.fullmatch(r"(.+?)\s*-\s*(.+)", value)
    if not match:
        return None
    start = _parse_clock(match.group(1))
    end = _parse_clock(match.group(2))
    if start is None or end is None:
        return None
    return start, end


def parse_simple_opening_hours(spec: str, at: datetime | None = None) -> bool | None:
    """Return dinner availability as true, false, or unknown.

    This is intentionally a small, conservative reader for common OSM and
    official-source strings. A day not mentioned by the source is unknown,
    not closed. Unsupported syntax also remains unknown rather than being
    treated as proof that dinner is unavailable.
    """
    spec = clean_space(spec).replace("–", "-").replace("—", "-")
    if not spec:
        return None
    if spec.casefold() == "24/7":
        return True

    at = at or datetime.now()
    # Dinner availability means 6:30 PM today, not whether the place is open at the moment the morning search runs.
    target_min = 18 * 60 + 30
    weekday = at.weekday()
    day_names = "|".join(sorted(DAY_INDEX, key=len, reverse=True))
    day_pattern = rf"((?:{day_names})(?:-(?:{day_names}))?(?:,(?:{day_names})(?:-(?:{day_names}))?)*)"
    current_day_covered = False
    current_day_unknown = False

    for chunk in [c.strip() for c in spec.split(";") if c.strip()]:
        match = re.match(rf"^{day_pattern}\s*(?::|\s)\s*(.+)$", chunk, flags=re.I)
        if not match:
            continue
        day_spec, hours_spec = match.group(1), match.group(2).strip()
        # Normalize full day names back to the canonical keys used by expand_days.
        canonical_days = []
        for token in re.split(r"[-,]", day_spec):
            token = token[:1].upper() + token[1:].lower()
            canonical_days.append(token)
        canonical_spec = day_spec
        for original, canonical in zip(re.split(r"[-,]", day_spec), canonical_days):
            canonical_spec = re.sub(rf"(?<![A-Za-z]){re.escape(original)}(?![A-Za-z])", canonical, canonical_spec)
        days = expand_days(canonical_spec)
        if weekday not in days:
            continue

        current_day_covered = True
        if hours_spec.casefold() in {"off", "closed", "none"}:
            return False

        spans = [_parse_opening_span(span) for span in re.split(r"\s*,\s*", hours_spec)]
        valid_spans = [span for span in spans if span is not None]
        if not valid_spans:
            current_day_unknown = True
            continue
        for start, end in valid_spans:
            if end < start:  # crosses midnight
                if target_min >= start or target_min <= end:
                    return True
            elif start <= target_min <= end:
                return True

    if current_day_covered and not current_day_unknown:
        return False
    return None


def set_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def run_verification_job(job_id: str, payload: dict[str, Any]) -> None:
    started_at = time.time()
    restaurants = payload.get("restaurants") or []
    budget = float(payload.get("budget") or 0)
    people = int(payload.get("people") or 1)
    open_only = bool(payload.get("openOnly"))
    total = len(restaurants)
    set_job(job_id, status="resolving", total=total, processed=0, message="Resolving official restaurant sources in parallel")

    prepared: list[dict[str, Any]] = [dict(item) for item in restaurants]
    source_cache: dict[tuple[str, ...], str] = {}

    # Resolve unique structured IDs concurrently. V4.1 did this inside the restaurant
    # loop, which made hundreds of network lookups feel serial.
    pending_ids: set[tuple[str, ...]] = set()
    for r in prepared:
        if normalize_url(r.get("website", "")):
            continue
        ids = tuple(x for x in [r.get("wikidata", ""), r.get("brandWikidata", ""), r.get("operatorWikidata", "")] if x)
        if ids:
            pending_ids.add(ids)

    completed_ids = 0
    if pending_ids:
        with ThreadPoolExecutor(max_workers=min(RESOLVE_WORKERS, len(pending_ids))) as pool:
            futures = {pool.submit(resolve_wikidata, list(ids)): ids for ids in pending_ids}
            for fut in as_completed(futures):
                ids = futures[fut]
                try:
                    source_cache[ids] = fut.result()
                except Exception:
                    source_cache[ids] = ""
                completed_ids += 1
                if completed_ids % 10 == 0 or completed_ids == len(pending_ids):
                    set_job(job_id, message=f"Resolved {completed_ids} of {len(pending_ids)} structured source records in parallel")

    resolved_count = 0
    unresolved_count = 0
    for idx, r in enumerate(prepared):
        source = normalize_url(r.get("website", ""))
        if not source:
            ids = tuple(x for x in [r.get("wikidata", ""), r.get("brandWikidata", ""), r.get("operatorWikidata", "")] if x)
            source = source_cache.get(ids, "") if ids else ""
        r["resolvedWebsite"] = source
        if source:
            resolved_count += 1
        else:
            unresolved_count += 1
        if idx % 40 == 0 or idx + 1 == total:
            set_job(
                job_id,
                processed=idx + 1,
                resolved=resolved_count,
                unresolved=unresolved_count,
                message=f"Prepared official sources for {idx + 1} of {total} filtered restaurants",
            )

    # Crawl each unique official URL once; this avoids hammering chain-wide sites shared by many locations.
    unique_sources: dict[str, str] = {}
    for r in prepared:
        u = r.get("resolvedWebsite") or ""
        if u:
            unique_sources.setdefault(u, u)

    source_results: dict[str, dict[str, Any]] = {}
    checked = 0
    blocked = 0
    cached_sources = 0
    sources = list(unique_sources)
    set_job(
        job_id,
        status="checking",
        processed=0,
        sources_total=len(sources),
        sources_checked=0,
        message=f"Checking {len(sources)} unique official web sources for family deals",
    )

    def work(u: str) -> tuple[str, dict[str, Any]]:
        key = crawl_cache_key(u, people)
        cached = cache_get("sources", key, SOURCE_CACHE_TTL)
        if isinstance(cached, dict) and cached.get("status") == "checked":
            result = dict(cached)
            result["from_cache"] = True
            return u, result
        result = crawl_official_source(u, 10_000.0, people)
        result["from_cache"] = False
        if result.get("status") == "checked":
            cache_set("sources", key, result)
        return u, result

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, max(1, len(sources)))) as pool:
        futures = [pool.submit(work, u) for u in sources]
        for fut in as_completed(futures):
            try:
                u, result = fut.result()
            except Exception as exc:
                # Should be rare because the worker already converts most network failures.
                u, result = "", {"status": "blocked", "deals": [], "error": type(exc).__name__}
            if u:
                source_results[u] = result
            checked += 1
            if result.get("status") == "blocked":
                blocked += 1
            if result.get("from_cache"):
                cached_sources += 1
            candidate_count = sum(
                sum(1 for d in (v.get("deals") or []) if float(d.get("price") or 0) <= budget)
                for v in source_results.values()
            )
            set_job(
                job_id,
                sources_checked=checked,
                blocked=blocked,
                cached_sources=cached_sources,
                candidate_deals=candidate_count,
                message=f"Checked {checked} of {len(sources)} official web sources · {cached_sources} reused from cache",
            )

    matches: list[dict[str, Any]] = []
    needs_hours: list[dict[str, Any]] = []
    needs_capacity: list[dict[str, Any]] = []
    no_deal = 0
    rejection_totals: dict[str, int] = {}
    for sr in source_results.values():
        for reason, count in (sr.get("rejections") or {}).items():
            rejection_totals[reason] = rejection_totals.get(reason, 0) + int(count)

    for r in prepared:
        u = r.get("resolvedWebsite") or ""
        sr = source_results.get(u) if u else None
        deals = [
            d for d in ((sr or {}).get("deals") or [])
            if float(d.get("price") or 0) <= budget
        ]
        if not deals:
            no_deal += 1
            continue

        # Prefer candidates that actually prove the requested party size, then lower total price.
        best = min(deals, key=lambda d: (not bool(d.get("capacity_verified")), d["price"], -d["score"]))
        opening_status = parse_simple_opening_hours(r.get("opening", "")) if open_only else True
        record = {
            "name": r.get("name", "Restaurant"),
            "distance": r.get("distance", 0),
            "cuisine": r.get("cuisine", ""),
            "restaurantClass": r.get("restaurantClass", "unknown"),
            "classReason": r.get("classReason", ""),
            "address": r.get("address", ""),
            "website": u,
            "price": best.get("price"),
            "listed_price": best.get("listed_price"),
            "price_mode": best.get("price_mode", "package"),
            "capacity": best.get("capacity"),
            "capacity_min": best.get("capacity_min"),
            "capacity_max": best.get("capacity_max"),
            "capacity_label": best.get("capacity_label", ""),
            "capacity_verified": bool(best.get("capacity_verified")),
            "evidence": best.get("evidence", ""),
            "source_url": best.get("source_url", u),
            "pages_checked": (sr or {}).get("pages_checked", 0),
            "opening_status": opening_status,
            "opening": r.get("opening", ""),
        }

        # Price-only evidence is no longer enough to claim a match for the user's party size.
        if not record["capacity_verified"]:
            needs_capacity.append(record)
            continue

        if open_only and opening_status is None:
            needs_hours.append(record)
        elif open_only and opening_status is False:
            continue
        else:
            matches.append(record)

    matches.sort(key=lambda m: (m["price"], m["distance"]))
    needs_hours.sort(key=lambda m: (m["price"], m["distance"]))
    needs_capacity.sort(key=lambda m: (m["price"], m["distance"]))

    set_job(
        job_id,
        status="done",
        processed=total,
        resolved=resolved_count,
        unresolved=unresolved_count,
        sources_total=len(sources),
        sources_checked=checked,
        blocked=blocked,
        matches=matches,
        needs_hours=needs_hours,
        needs_capacity=needs_capacity,
        no_deal=no_deal,
        rejection_counts=rejection_totals,
        candidate_deals=sum(
            sum(1 for d in (v.get("deals") or []) if float(d.get("price") or 0) <= budget)
            for v in source_results.values()
        ),
        cached_sources=cached_sources,
        elapsed_seconds=round(time.time() - started_at, 1),
        message=f"Strict verification complete: {len(matches)} fully verified matches",
        completed_at=time.time(),
    )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[HUNT] " + (fmt % args))

    def send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json({"ok": True, "version": "v5.0"})
        if parsed.path == "/api/verify/status":
            q = parse_qs(parsed.query)
            job_id = (q.get("id") or [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                data = dict(job) if job else None
            if data is None:
                return self.send_json({"error": "Unknown verification job"}, 404)
            return self.send_json(data)
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/verify/start":
            return self.send_json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 5_000_000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            restaurants = payload.get("restaurants")
            if not isinstance(restaurants, list) or not restaurants:
                raise ValueError("No restaurants were supplied")
            job_id = uuid.uuid4().hex
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "id": job_id,
                    "status": "queued",
                    "created_at": time.time(),
                    "total": len(restaurants),
                    "processed": 0,
                    "resolved": 0,
                    "unresolved": 0,
                    "sources_total": 0,
                    "sources_checked": 0,
                    "blocked": 0,
                    "cached_sources": 0,
                    "candidate_deals": 0,
                    "matches": [],
                    "needs_hours": [],
                    "message": "Verification queued",
                }
            threading.Thread(target=run_verification_job, args=(job_id, payload), daemon=True).start()
            return self.send_json({"job_id": job_id})
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 400)


def open_browser(port: int) -> None:
    time.sleep(0.8)
    try:
        webbrowser.open(f"http://{HOST}:{port}")
    except Exception:
        pass


def main() -> None:
    print("=" * 64)
    print("HUNT FAMILY DEALS V5.0 FAST FILTERS")
    print("Full-radius discovery + fast filtered strict family-meal verifier")
    print("=" * 64)
    server = None
    port = PORT
    for candidate in range(PORT, PORT + 10):
        try:
            server = ThreadingHTTPServer((HOST, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        print("Could not find an open local port between 8765 and 8774.")
        input("Press ENTER to close.")
        return
    print(f"Opening http://{HOST}:{port}")
    if port != PORT:
        print(f"Port {PORT} was already in use, so HUNT safely moved to {port}.")
    print("Leave this window open while HUNT is running.")
    print("Press Ctrl+C here when you are finished.")
    print()
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
