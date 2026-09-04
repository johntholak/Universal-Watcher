import json
import unittest
from urllib.error import HTTPError
from io import BytesIO

from amc_showtime_api import AmcApiError, AmcShowtimeClient, AmcUnauthorizedVendorKey


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class RecordingOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payloads.pop(0))


class AmcShowtimeClientTests(unittest.TestCase):
    def test_invalid_collection_is_not_an_empty_schedule(self):
        for payload in ({}, {"_embedded": {"showtimes": None}},
                        {"_embedded": {"showtimes": [None]}}, []):
            with self.subTest(payload=payload):
                client = AmcShowtimeClient("test-key", opener=RecordingOpener([payload]))
                with self.assertRaises(AmcApiError):
                    client.list_showtimes(123, "2026-09-04")

    def test_collects_complete_theatre_catalog(self):
        opener = RecordingOpener([
            {"count": 2, "pageNumber": 1, "_embedded": {"theatres": [{"id": 1}]},
             "_links": {"next": {"href": "next"}}},
            {"count": 2, "pageNumber": 2, "_embedded": {"theatres": [{"id": 2}]},
             "_links": {}},
        ])
        self.assertEqual([t["id"] for t in AmcShowtimeClient(
            "test-key", opener=opener).list_theatres()], [1, 2])

    def test_missing_page_or_repeated_page_is_unavailable(self):
        cases = [
            [{"count": 2, "_embedded": {"showtimes": [{"id": 1}]}, "_links": {}}],
            [{"_embedded": {"showtimes": [{"id": 1}]},
              "_links": {"next": {"href": "next"}}},
             {"_embedded": {"showtimes": [{"id": 1}]}, "_links": {}}],
        ]
        for pages in cases:
            with self.subTest(pages=pages):
                with self.assertRaises(AmcApiError):
                    AmcShowtimeClient("test-key", opener=RecordingOpener(pages)).list_showtimes(
                        123, "2026-09-04")

    def test_pagination_guard_does_not_return_partial_success(self):
        pages = [{"_embedded": {"showtimes": [{"id": i}]},
                  "_links": {"next": {"href": "next"}}} for i in range(50)]
        with self.assertRaises(AmcApiError):
            AmcShowtimeClient("test-key", opener=RecordingOpener(pages)).list_showtimes(
                123, "2026-09-04")

    def test_explicit_empty_collection_is_valid(self):
        client = AmcShowtimeClient("test-key", opener=RecordingOpener([
            {"count": 0, "_embedded": {"showtimes": []}, "_links": {}}
        ]))
        self.assertEqual(client.list_showtimes(123, "2026-09-04"), [])

    def test_unauthorized_vendor_key_has_specific_error(self):
        def reject(request, timeout):
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                {},
                BytesIO(b'{"errors":[{"code":12005,"exceptionMessage":"Unauthorized VendorKey."}]}'),
            )

        client = AmcShowtimeClient("issued-but-inactive", opener=reject)
        with self.assertRaises(AmcUnauthorizedVendorKey):
            client.resolve_theatre_id("universal-cinema-an-amc-theatre")

    def test_resolves_theatre_slug_and_sends_vendor_key(self):
        opener = RecordingOpener([{
            "_embedded": {"theatres": [
                {"id": 123, "slug": "universal-cinema-an-amc-theatre"}
            ]},
            "_links": {},
        }])
        client = AmcShowtimeClient("test-key", opener=opener)
        self.assertEqual(
            client.resolve_theatre_id("universal-cinema-an-amc-theatre"), 123
        )
        request, timeout = opener.requests[0]
        self.assertEqual(request.get_header("X-amc-vendor-key"), "test-key")
        self.assertIn("/v2/theatres?", request.full_url)

    def test_collects_paginated_showtimes(self):
        opener = RecordingOpener([
            {
                "_embedded": {"showtimes": [{"id": 1}]},
                "_links": {"next": {"href": "next"}},
            },
            {
                "_embedded": {"showtimes": [{"id": 2}]},
                "_links": {},
            },
        ])
        client = AmcShowtimeClient("test-key", opener=opener)
        self.assertEqual(
            [item["id"] for item in client.list_showtimes(123, "2026-09-03")],
            [1, 2],
        )
        self.assertIn("/v2/theatres/123/showtimes/09-03-2026", opener.requests[0][0].full_url)
        self.assertIn("page-number=2", opener.requests[1][0].full_url)


if __name__ == "__main__":
    unittest.main()
