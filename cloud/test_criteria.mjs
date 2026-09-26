import test from "node:test";
import assert from "node:assert/strict";
import { validateFamilyDealsCriteria, qualifiesPrice } from "./criteria.mjs";

const criteria = { schema_version: 1, location: " 91304 ", radius_miles: 2, party_size: 7, max_total_price: 50, cuisines: ["pizza_italian", "bbq"], restaurant_type: "independent_local", open_tonight: true };

test("preserves exact search without limiting the selected radius or cuisines", () => {
  const value = validateFamilyDealsCriteria({ ...criteria, radius_miles: 125 });
  assert.equal(value.location, "91304");
  assert.equal(value.radius_miles, 125);
  assert.deepEqual(value.cuisines, ["pizza_italian", "bbq"]);
  assert.equal(value.max_total_cents, 5000);
});

test("budget threshold uses exact cents", () => {
  assert.equal(qualifiesPrice(4999, 5000), true);
  assert.equal(qualifiesPrice(5000, 5000), true);
  assert.equal(qualifiesPrice(5001, 5000), false);
  assert.throws(() => validateFamilyDealsCriteria({ ...criteria, max_total_price: 50.005 }), /exact positive total/);
});

test("rejects invalid parties, fields, classifications and unsupported versions", () => {
  for (const bad of [{ party_size: 3 }, { party_size: 11 }, { restaurant_type: "unknown" }, { schema_version: 2 }, { cuisines: ["bbq", "bbq"] }, { radius_miles: 0 }, { max_total_price: -1 }, { surprise: true }]) {
    assert.throws(() => validateFamilyDealsCriteria({ ...criteria, ...bad }));
  }
});
