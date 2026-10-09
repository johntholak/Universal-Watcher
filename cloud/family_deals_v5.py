"""Headless bridge to the preserved Family Deals V5 discovery and verifier.

The legacy page owns geocoding, the full Overpass radius scan, classification,
and filters. Its Python server owns official-source verification. No live source
is contacted by importing this module; callers supply a Playwright page and a
loopback URL serving the unchanged legacy page.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from typing import Any


CUISINE_TO_V5 = {
    "pizza_italian": "italian", "mexican_latin": "mexican", "asian": "asian",
    "american": "american", "bbq": "bbq", "mediterranean": "mediterranean",
    "indian": "indian", "seafood": "seafood", "other_unknown": "other",
}
TYPE_TO_V5 = {"any": "any", "independent_local": "indie_local",
              "independent": "independent", "chains": "chains"}


async def run_v5_page(page: Any, base_url: str, criteria: dict[str, Any], on_progress: Any = None) -> dict[str, Any]:
    """Run V5 while optionally publishing candidates as official sources finish."""
    if criteria.get("schema_version") != 1 or criteria.get("restaurant_type") not in TYPE_TO_V5:
        raise ValueError("Unsupported Family Deals criteria")
    if any(c not in CUISINE_TO_V5 for c in criteria.get("cuisines", [])):
        raise ValueError("Unsupported cuisine")
    await page.goto(base_url, wait_until="domcontentloaded")
    await page.evaluate("""criteria => {
      const radius = document.getElementById('distance');
      radius.min = '0.01'; radius.max = String(Math.max(Number(radius.max), criteria.radius_miles));
      radius.step = 'any'; radius.value = String(criteria.radius_miles);
      const budget = document.getElementById('budget');
      budget.min = '0.01'; budget.max = String(Math.max(Number(budget.max), criteria.max_total_price));
      budget.step = 'any'; budget.value = String(criteria.max_total_price);
      document.getElementById('location').value = criteria.location;
      state.people = criteria.party_size;
      state.openOnly = criteria.open_tonight;
      state.restaurantType = criteria.restaurant_type;
      state.cuisines = criteria.cuisines;
      const coordinates = /^\\s*(-?\\d+(?:\\.\\d+)?)\\s*,\\s*(-?\\d+(?:\\.\\d+)?)\\s*$/.exec(criteria.location);
      if (coordinates) {
        const lat = Number(coordinates[1]), lon = Number(coordinates[2]);
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) throw new Error('Invalid coordinates');
        geocode = async () => ({lat, lon, display: criteria.location});
      }
      renderControls(); renderFilterControls();
    }""", {
        **criteria,
        "restaurant_type": TYPE_TO_V5[criteria["restaurant_type"]],
        "cuisines": [CUISINE_TO_V5[c] for c in criteria.get("cuisines", [])],
    })
    await page.evaluate("""() => {
      window.__uwHuntFinished = false;
      window.__uwHuntPromise = Promise.resolve().then(() => runHunt()).finally(() => { window.__uwHuntFinished = true; });
      return true;
    }""")
    last_signature = None
    while True:
        snapshot = await page.evaluate("""() => {
          const verification = state.verification;
          const selected = state.restaurants.length;
          return {
            radius_discovered: state.allRestaurants.length,
            selected_restaurants: selected,
            verification,
            error: document.querySelector('#results .error')?.textContent || null,
            discovery_completed: window.__uwHuntFinished === true || (selected > 0 && !!verification),
            hunt_finished: window.__uwHuntFinished === true,
          };
        }""")
        verification = snapshot.get("verification") or {}
        if on_progress and snapshot.get("discovery_completed") and verification.get("status") in ("resolving", "checking"):
            signature = (verification.get("status"), verification.get("sources_checked"), len(verification.get("matches") or []))
            if signature != last_signature:
                await on_progress(snapshot)
                last_signature = signature
        if snapshot.get("hunt_finished") or "hunt_finished" not in snapshot:
            return snapshot
        await asyncio.sleep(0.8)


def _https(url: Any) -> str | None:
    return url if isinstance(url, str) and url.startswith("https://") and len(url) <= 1000 else None


def normalize_v5_snapshot(snapshot: dict[str, Any], criteria: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Keep V5 candidates distinct from location-verified deals."""
    job = snapshot.get("verification") or {}
    selected = max(0, int(snapshot.get("selected_restaurants") or 0))
    error = snapshot.get("error")
    verification_status = job.get("status")
    progressive = verification_status in ("resolving", "checking") and snapshot.get("discovery_completed")
    if error or not snapshot.get("discovery_completed") or (selected and verification_status != "done" and not progressive):
        return {"outcome": "UNAVAILABLE", "summary": "Restaurant discovery or verification could not finish.",
                "coverage": {"state": "unavailable", "discovered": selected, "checked": 0,
                             "unavailable": selected, "unresolved": 0}, "results": []}

    checked = max(0, int(job.get("restaurants_checked") or 0)) if selected else 0
    unavailable = max(0, int(job.get("restaurants_unavailable") or 0)) if selected else 0
    unresolved = max(0, int(job.get("restaurants_unresolved") or 0)) if selected else 0
    coverage_valid = (checked + unavailable + unresolved <= selected) if progressive else (checked + unavailable + unresolved == selected)
    if not coverage_valid:
        return {"outcome": "UNAVAILABLE", "summary": "Restaurant coverage counts did not reconcile.",
                "coverage": {"state": "unavailable", "discovered": selected, "checked": 0,
                             "unavailable": selected, "unresolved": 0}, "results": []}

    candidates = job.get("matches") or []
    results = []
    verified_count = 0
    partial_count = 0
    omitted_candidates = 0
    for record in candidates:
        # V5 confirms meal/price/capacity, but a generic official domain does not
        # prove the offer applies to this particular restaurant location.
        evidence = str(record.get("evidence") or "").strip()
        name = str(record.get("name") or "Restaurant").strip()[:120]
        source = _https(record.get("source_url") or record.get("website"))
        restaurant_class = str(record.get("restaurantClass") or "unknown")
        direct_source = bool(record.get("source_direct"))
        name_tokens = [t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) >= 3]
        evidence_low = evidence.lower()
        name_match = len(name_tokens) >= 2 and all(t in evidence_low for t in name_tokens[:3])
        address_tokens = [t for t in re.findall(r"[a-z0-9]+", str(record.get("address") or "").lower()) if len(t) >= 3]
        address_match = len(address_tokens) >= 2 and all(t in evidence_low for t in address_tokens[:3])
        # An independent restaurant's own discovered website is location-specific enough.
        # Chains and local groups still need the evidence itself to identify the location.
        location_verified = (restaurant_class == "independent" and direct_source) or name_match or address_match
        if not evidence or record.get("price") is None or not record.get("capacity_verified"):
            omitted_candidates += 1
            continue
        price_cents = round(float(record["price"]) * 100)
        if price_cents > round(float(criteria["max_total_price"]) * 100):
            omitted_candidates += 1
            continue
        fingerprint = hashlib.sha256(json.dumps([name, source, price_cents, record.get("capacity_label"), evidence], ensure_ascii=False).encode()).hexdigest()
        deal_name = str(record.get("deal_name") or "").strip()
        match_verified = location_verified and bool(deal_name)
        if match_verified:
            verified_count += 1
        else:
            partial_count += 1
        results.append({
            "id": str(uuid.uuid5(uuid.UUID(job_id), fingerprint)),
            "title": f"Family meal offer at {name}", "outcome": "MATCH" if match_verified else "PARTIAL",
            "verification": "VERIFIED" if match_verified else "PARTIALLY_VERIFIED", "summary": "Meal, total, capacity, explicit deal name, and location applicability verified." if match_verified else "Meal, total, and capacity found; explicit deal-name or location proof is still needed.",
            "fingerprint": fingerprint, "destination_url": source,
            "details": {"deal_name": deal_name or None, "restaurant": name, "price_cents": price_cents,
                        "serves_max": record.get("capacity_max"), "serving_label": record.get("capacity_label"),
                        "cuisine": record.get("cuisine"), "classification": record.get("restaurantClass", "unknown"),
                        "distance_miles": record.get("distance"), "included_food": None,
                        "meal_verified": True, "price_verified": True, "capacity_verified": True,
                        "location_verified": location_verified, "open_tonight_verified": record.get("opening_status") is True},
            "evidence": [{"source": "Restaurant official source", "summary": evidence[:800], "url": source}],
        })

    complete = not progressive and checked == selected and not unavailable and not unresolved
    state = "complete" if complete and not partial_count and not omitted_candidates else "partial"
    coverage = {"state": state, "discovered": selected, "checked": checked,
                "unavailable": unavailable, "unresolved": unresolved,
                "verified_matches": verified_count, "partial_candidates": partial_count,
                "omitted_candidates": omitted_candidates}
    if progressive:
        outcome = "PARTIAL"
        summary = f"{len(results)} qualifying meal candidates found so far; {checked} of {selected} restaurants checked. Explicit deal-name/location proof and full coverage may still be pending."
    elif verified_count:
        if partial_count or not complete or omitted_candidates:
            outcome = "PARTIAL"
            summary = f"{verified_count} verified family deal(s) found; {partial_count} additional candidate(s) still need location confirmation."
        else:
            outcome = "MATCH"
            summary = f"{verified_count} verified family deal(s) found."
    elif partial_count or not complete or omitted_candidates:
        outcome = "PARTIAL"
        summary = f"No fully verified family deals yet; {partial_count} candidate(s) still need location confirmation."
    else:
        outcome = "NO_MATCH"
        summary = f"No qualifying family meal found among {checked} checked restaurants."
    return {"outcome": outcome, "summary": summary, "coverage": coverage, "results": results,
            "radius_discovered": max(0, int(snapshot.get("radius_discovered") or 0))}
