import unittest

from ticket_watcher.matcher import event_similarity, qualify, rejection_reasons
from ticket_watcher.models import Listing, WatchConfig
from ticket_watcher.sources.ticketmaster import encode_geohash
from ticket_watcher.ticketmaster_browser import parse_quickpicks
from ticket_watcher.ticketmaster_live import quantity_url, requested_quantity


def listing(**changes):
    values = dict(source="Test", event_id="1", event_name="Los Angeles Lakers vs Golden State Warriors", event_url="https://example.com", venue="Crypto.com Arena", city="Los Angeles", starts_at=None, currency="USD", price_each=140.0, quantity_available=4, seats_together=True, fees_included=True)
    values.update(changes)
    return Listing(**values)


class MatcherTests(unittest.TestCase):
    def test_fuzzy_event_match(self):
        self.assertGreater(event_similarity("Lakers vs Warriors", "Los Angeles Lakers vs Golden State Warriors"), 0.7)

    def test_price_each_rejected(self):
        config = WatchConfig(event="Lakers Warriors", max_price_each=100)
        self.assertIsNone(qualify(listing(), config))

    def test_total_rejected(self):
        config = WatchConfig(event="Lakers Warriors", quantity=4, max_order_total=500)
        self.assertIsNone(qualify(listing(), config))

    def test_fees_required(self):
        config = WatchConfig(event="Lakers Warriors", require_fees_included=True)
        self.assertIsNone(qualify(listing(fees_included=None), config))

    def test_qualifying_match(self):
        config = WatchConfig(event="Lakers Warriors", quantity=2, max_price_each=150, max_order_total=300)
        result = qualify(listing(), config)
        self.assertIsNotNone(result)
        self.assertEqual(result.estimated_order_total, 280)

    def test_west_hills_geohash(self):
        self.assertEqual(encode_geohash(34.1973, -118.6430), "9q5ds1qv9")

    def test_partial_radius_config_rejected(self):
        with self.assertRaises(ValueError):
            WatchConfig(event="Celtics Lakers", latitude=34.1973).validate()

    def test_ticketmaster_radius_limit_rejected(self):
        with self.assertRaises(ValueError):
            WatchConfig(event="Celtics Lakers", latitude=34.1973, longitude=-118.6430, radius_miles=20000).validate()

    def test_missing_price_explained(self):
        config = WatchConfig(event="Lakers Warriors", max_price_each=150)
        reasons = rejection_reasons(listing(price_each=None), config)
        self.assertIn("Ticketmaster did not publish an event price range", reasons)

    def test_expensive_price_explained(self):
        config = WatchConfig(event="Lakers Warriors", max_price_each=100)
        reasons = rejection_reasons(listing(price_each=140), config)
        self.assertIn("advertised minimum $140.00 exceeds $100.00 per ticket", reasons)

    def test_quickpicks_all_in_price(self):
        payload = {"_embedded": {"offer": [{
            "id": "offer-1", "section": "304", "row": "15", "currency": "USD",
            "listPrice": 175.0, "charges": [{"amount": 40.25}, {"amount": 0.0}],
        }]}}
        offers = parse_quickpicks(payload)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].all_in_price, 215.25)
        self.assertEqual(offers[0].section, "304")

    def test_quickpicks_quantity_url(self):
        original = "https://example.com/quickpicks?show=places&qty=2&embed=offer"
        self.assertEqual(quantity_url(original, 4), "https://example.com/quickpicks?show=places&qty=4&embed=offer")
        self.assertEqual(requested_quantity("https://example.com/quickpicks?show=places&qty=4&embed=offer"), 4)


if __name__ == "__main__":
    unittest.main()
