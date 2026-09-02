import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hunt_server", ROOT / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class StrictPriceBindingTests(unittest.TestCase):
    def analyze(self, text, budget=50, people=4):
        return server.analyze_deals([text], "https://example.test/menu", budget, people)

    def test_family_restaurant_name_does_not_make_discount_a_family_deal(self):
        out = self.analyze("Big Z Pizza Family Restaurant | Original price was $3.50 | Discounted price is $3.15")
        self.assertEqual(out["deals"], [])

    def test_delivery_fee_is_not_meal_price(self):
        out = self.analyze("6-Foot Sub (Serves 30) | $99.99 | Please add $4.00 for convenient delivery")
        self.assertEqual(out["deals"], [])

    def test_side_dish_feeding_many_is_not_full_dinner(self):
        out = self.analyze("BROCCOLI PASTA SALAD | $25 SMALL (feeds 10-12)")
        self.assertEqual(out["deals"], [])

    def test_faq_price_is_not_bound_to_family_meal(self):
        out = self.analyze("Frequently asked questions | What family meal deals do we have? | Build dinner with the $7 value menu")
        self.assertEqual(out["deals"], [])

    def test_real_family_meal_for_four_is_kept(self):
        out = self.analyze("Family Meal for 4 | Includes roasted chicken, two family-size sides and bread | $39.99")
        self.assertEqual(len(out["deals"]), 1)
        self.assertTrue(out["deals"][0]["capacity_verified"])
        self.assertEqual(out["deals"][0]["price"], 39.99)

    def test_per_person_price_is_converted_to_group_total(self):
        out = self.analyze("Family Feast | Serves 4 | $10.00 per person | Includes chicken and sides")
        self.assertEqual(len(out["deals"]), 1)
        self.assertEqual(out["deals"][0]["price"], 40.0)

    def test_starting_price_is_not_exact(self):
        out = self.analyze("Family Feast | Serves 10 | starts at only $13.50 per person")
        self.assertEqual(out["deals"], [])

    def test_family_of_four_accepts_meal_for_six(self):
        out = self.analyze("Family Meal | Serves 6 | Includes chicken, rice and sides | $44.99", people=4)
        self.assertEqual(len(out["deals"]), 1)
        self.assertTrue(out["deals"][0]["capacity_verified"])
        self.assertEqual(out["deals"][0]["capacity"], 6)

    def test_serving_range_can_cover_party(self):
        out = self.analyze("Family Dinner | Serves 4-6 | Includes pasta, salad and bread | $42.00", people=5)
        self.assertEqual(len(out["deals"]), 1)
        self.assertEqual(out["deals"][0]["capacity_label"], "4-6")

    def test_family_of_four_accepts_meal_for_ten(self):
        out = self.analyze("Family Feast | Serves 10 | Includes chicken, sides and bread | $49.00", people=4)
        self.assertEqual(len(out["deals"]), 1)


    def test_birthday_party_package_is_not_a_family_dinner(self):
        out = self.analyze("Birthday Party Package | Includes 6 kids, play points, reserved table and pizza | $49.99")
        self.assertEqual(out["deals"], [])

    def test_takehome_party_pack_can_still_be_a_meal(self):
        out = self.analyze("Party Pack | Serves 6 | Takeout dinner includes 2 pizzas, salad and bread | $44.99")
        self.assertEqual(len(out["deals"]), 1)
        self.assertTrue(out["deals"][0]["capacity_verified"])

    def test_package_entirely_above_family_range_is_rejected(self):
        out = self.analyze("Party Package | Serves 12 | Includes entrees and sides | $49.00", people=4)
        self.assertEqual(out["deals"], [])


if __name__ == "__main__":
    unittest.main()
