export const CUISINES = new Set([
  "pizza_italian", "mexican_latin", "asian", "american", "bbq",
  "mediterranean", "indian", "seafood", "other_unknown",
]);
export const RESTAURANT_TYPES = new Set(["any", "independent_local", "independent", "chains"]);

function invalid(message) {
  const error = new Error(message);
  error.status = 400;
  return error;
}

export function validateFamilyDealsCriteria(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw invalid("Criteria must be an object");
  const keys = new Set(["schema_version", "location", "radius_miles", "party_size", "max_total_price", "cuisines", "restaurant_type", "open_tonight"]);
  if (Object.keys(input).some((key) => !keys.has(key))) throw invalid("Unsupported criteria field");
  if (input.schema_version !== 1) throw invalid("Unsupported criteria schema version");
  const location = typeof input.location === "string" ? input.location.trim() : "";
  if (!location || location.length > 160 || /[\x00-\x1f]/.test(location)) throw invalid("Enter an address, city, ZIP, or coordinates");
  const radius = input.radius_miles;
  if (typeof radius !== "number" || !Number.isFinite(radius) || radius <= 0) throw invalid("Radius must be positive");
  const party = input.party_size;
  if (!Number.isInteger(party) || party < 4 || party > 10) throw invalid("Party size must be 4 through 10");
  const price = input.max_total_price;
  const cents = price * 100;
  if (typeof price !== "number" || !Number.isFinite(price) || price <= 0 || !Number.isSafeInteger(Math.round(cents)) || Math.abs(cents - Math.round(cents)) > 1e-6) throw invalid("Enter an exact positive total price in cents");
  if (!Array.isArray(input.cuisines) || input.cuisines.length > CUISINES.size || input.cuisines.some((cuisine) => !CUISINES.has(cuisine)) || new Set(input.cuisines).size !== input.cuisines.length) throw invalid("Choose valid distinct cuisines");
  if (!RESTAURANT_TYPES.has(input.restaurant_type)) throw invalid("Choose a valid restaurant type");
  if (typeof input.open_tonight !== "boolean") throw invalid("Open tonight must be true or false");
  return { schema_version: 1, location, radius_miles: radius, party_size: party, max_total_price: Math.round(cents) / 100, max_total_cents: Math.round(cents), cuisines: [...input.cuisines], restaurant_type: input.restaurant_type, open_tonight: input.open_tonight };
}

export function qualifiesPrice(priceCents, budgetCents) {
  return Number.isSafeInteger(priceCents) && priceCents >= 0 && Number.isSafeInteger(budgetCents) && priceCents <= budgetCents;
}
