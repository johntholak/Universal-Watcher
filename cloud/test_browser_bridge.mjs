import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("./family_deals_v5.py", import.meta.url), "utf8");
const match = /await page\.evaluate\("""(criteria => \{[\s\S]*?\})""", \{/.exec(source);
if (!match) throw new Error("V5 browser bridge script not found");
// Python unescapes the two backslashes in its triple-quoted string.
const script = match[1].replaceAll("\\\\", "\\");

test("V5 bridge applies exact values and recognizes coordinate input", async () => {
  const elements = { distance: { max: "30" }, budget: { max: "100" }, location: {} };
  const state = { people: 4, openOnly: false, restaurantType: "any", cuisines: [] };
  let rendered = 0;
  const context = { document: { getElementById: (id) => elements[id] }, state,
    geocode: async () => { throw new Error("Should not call network geocoder"); },
    renderControls: () => rendered++, renderFilterControls: () => rendered++ };
  const configure = vm.runInNewContext(`(${script})`, context);
  configure({ radius_miles: 45, max_total_price: 85.01, location: "34.2, -118.6",
    party_size: 7, open_tonight: true, restaurant_type: "indie_local", cuisines: ["italian", "bbq"] });
  assert.equal(elements.distance.value, "45");
  assert.equal(elements.distance.max, "45");
  assert.equal(elements.budget.value, "85.01");
  assert.equal(elements.budget.step, "any");
  assert.equal(state.people, 7);
  assert.equal(state.restaurantType, "indie_local");
  assert.equal(rendered, 2);
  const center = await context.geocode();
  assert.equal(center.lat, 34.2);
  assert.equal(center.lon, -118.6);
});
