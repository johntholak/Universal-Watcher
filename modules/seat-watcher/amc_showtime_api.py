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
        values = embedded.get(key) if isinstance(embedded, dict) else None
        if not isinstance(values, list) or any(not isinstance(v, dict) for v in values):
            raise AmcApiError(f"AMC API returned an invalid {key} collection")
        return values

    def _list_pages(self, path, key):
        """Fail closed on partial/malformed catalogs instead of losing coverage."""
        records, seen = [], set()
        expected_count = None
        for page_number in range(1, 51):
            payload = self._get(path, {"page-size": 200, "page-number": page_number})
            values = self._embedded(payload, key)
            links = payload.get("_links", {})
            if not isinstance(links, dict) or payload.get("pageNumber", page_number) != page_number:
                raise AmcApiError(f"AMC API returned invalid pagination for {path}")
            count = payload.get("count")
            if count is not None:
                if type(count) is not int or count < 0:
                    raise AmcApiError(f"AMC API returned an invalid count for {path}")
                if expected_count is not None and count != expected_count:
                    raise AmcApiError(f"AMC API catalog changed during pagination for {path}")
                expected_count = count
            for value in values:
                record_id = str(value.get("id", "")).strip()
                if not record_id or record_id == "None" or record_id in seen:
                    raise AmcApiError(f"AMC API returned missing/repeated IDs for {path}")
                seen.add(record_id)
                records.append(value)
            if not links.get("next"):
                if expected_count is not None and len(records) != expected_count:
                    raise AmcApiError(f"AMC API returned an incomplete collection for {path}")
                return records
            if not values:
                raise AmcApiError(f"AMC API pagination made no progress for {path}")
        raise AmcApiError(f"AMC API pagination safety limit reached for {path}; coverage incomplete")

    def list_theatres(self):
        return self._list_pages("/theatres", "theatres")

    def resolve_theatre_id(self, slug):
        target = str(slug or "").strip().lower()
        if not target:
            raise ValueError("AMC theatre slug is required")
        for theatre in self.list_theatres():
            if str(theatre.get("slug", "")).strip().lower() == target:
                return int(theatre["id"])
        raise AmcApiError(f"AMC theatre slug was not found: {slug}")

    def list_showtimes(self, theatre_id, search_date):
        parsed = (
            search_date
            if isinstance(search_date, date)
            else datetime.strptime(str(search_date), "%Y-%m-%d").date()
        )
        api_date = parsed.strftime("%m-%d-%Y")
        return self._list_pages(f"/theatres/{int(theatre_id)}/showtimes/{api_date}", "showtimes")
