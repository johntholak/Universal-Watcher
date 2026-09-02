"""Small approved AMC catalog client used only when a vendor key is configured."""
import json
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_ROOT = "https://api.amctheatres.com/v2"


class AmcApiError(RuntimeError):
    pass


class AmcUnauthorizedVendorKey(AmcApiError):
    pass


class AmcShowtimeClient:
    def __init__(self, vendor_key, opener=urlopen, timeout=20):
        self.vendor_key = str(vendor_key or "").strip()
        self.opener = opener
        self.timeout = timeout
        if not self.vendor_key:
            raise ValueError("AMC vendor key is required")

    def _get(self, path, query=None):
        url = API_ROOT + path
        if query:
            url += "?" + urlencode(query)
        request = Request(
            url,
            headers={
                "Accept": "application/hal+json, application/json",
                "X-AMC-Vendor-Key": self.vendor_key,
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                detail = ""
            finally:
                exc.close()
            if len(detail) > 500:
                detail = detail[:500] + "..."
            suffix = f" | AMC response: {detail}" if detail else ""
            error_type = (
                AmcUnauthorizedVendorKey
                if exc.code == 403 and (
                    "Unauthorized VendorKey" in detail or '"code":12005' in detail
                )
                else AmcApiError
            )
            raise error_type(
                f"AMC API request failed for {path}: HTTP {exc.code}{suffix}"
            ) from exc
        except Exception as exc:
            raise AmcApiError(f"AMC API request failed for {path}: {exc}") from exc

    @staticmethod
    def _embedded(payload, key):
        embedded = payload.get("_embedded", {}) if isinstance(payload, dict) else {}
        values = embedded.get(key, []) if isinstance(embedded, dict) else []
        return values if isinstance(values, list) else []

    def resolve_theatre_id(self, slug):
        target = str(slug or "").strip().lower()
        if not target:
            raise ValueError("AMC theatre slug is required")
        page_number = 1
        while page_number <= 50:
            payload = self._get(
                "/theatres",
                {"page-size": 200, "page-number": page_number},
            )
            theatres = self._embedded(payload, "theatres")
            for theatre in theatres:
                if str(theatre.get("slug", "")).strip().lower() == target:
                    return int(theatre["id"])
            if not payload.get("_links", {}).get("next"):
                break
            page_number += 1
        raise AmcApiError(f"AMC theatre slug was not found: {slug}")

    def list_showtimes(self, theatre_id, search_date):
        parsed = (
            search_date
            if isinstance(search_date, date)
            else datetime.strptime(str(search_date), "%Y-%m-%d").date()
        )
        api_date = parsed.strftime("%m-%d-%Y")
        page_number = 1
        showtimes = []
        while page_number <= 50:
            payload = self._get(
                f"/theatres/{int(theatre_id)}/showtimes/{api_date}",
                {"page-size": 200, "page-number": page_number},
            )
            showtimes.extend(self._embedded(payload, "showtimes"))
            if not payload.get("_links", {}).get("next"):
                break
            page_number += 1
        return showtimes
