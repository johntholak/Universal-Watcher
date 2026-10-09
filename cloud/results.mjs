const OUTCOMES = new Set(["MATCH", "PARTIAL", "UNAVAILABLE", "ERROR"]);
const VERIFICATIONS = new Set(["VERIFIED", "PARTIALLY_VERIFIED", "UNABLE_TO_VERIFY"]);
const idPattern = /^[0-9a-f-]{36}$/;

function invalid(message) { const error = new Error(message); error.status = 400; return error; }
function shortText(value, max) { return typeof value === "string" && value.length <= max && !/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value); }
export function validateResultChunk(input) {
  if (!input || typeof input !== "object" || !idPattern.test(input.claim_id || "")) throw invalid("Invalid claim");
  if (!Array.isArray(input.items) || input.items.length < 1 || input.items.length > 5) throw invalid("Submit one through five results per chunk");
  const ids = new Set();
  const items = input.items.map((item) => {
    if (!item || typeof item !== "object" || !idPattern.test(item.id || "") || ids.has(item.id)) throw invalid("Each result needs a distinct stable ID");
    ids.add(item.id);
    if (!OUTCOMES.has(item.outcome) || !VERIFICATIONS.has(item.verification) || !shortText(item.title, 180) || !item.title.trim()) throw invalid("Invalid result state or title");
    if (item.outcome === "MATCH" && item.verification !== "VERIFIED") throw invalid("A match must be verified");
    if (item.summary != null && !shortText(item.summary, 800)) throw invalid("Invalid summary");
    if (item.destination_url != null && (!shortText(item.destination_url, 1000) || !/^https:\/\//.test(item.destination_url))) throw invalid("Invalid destination URL");
    if (item.fingerprint != null && !shortText(item.fingerprint, 180)) throw invalid("Invalid fingerprint");
    if (!item.details || typeof item.details !== "object" || Array.isArray(item.details) || JSON.stringify(item.details).length > 4000) throw invalid("Invalid compact details");
    if (!Array.isArray(item.evidence) || item.evidence.length < 1 || item.evidence.length > 5) throw invalid("Include one through five compact evidence records");
    const evidence = item.evidence.map((entry) => {
      if (!entry || !shortText(entry.source, 120) || !entry.source?.trim() || !shortText(entry.summary, 800) || !entry.summary?.trim() || (entry.url != null && (!shortText(entry.url, 1000) || !/^https:\/\//.test(entry.url))) || (entry.captured_at != null && (!shortText(entry.captured_at, 40) || !Number.isFinite(Date.parse(entry.captured_at))))) throw invalid("Invalid evidence");
      return { source: entry.source, summary: entry.summary, url: entry.url || null, captured_at: entry.captured_at || null };
    });
    return { id: item.id, outcome: item.outcome, verification: item.verification, title: item.title.trim(), summary: item.summary || null, details: item.details, destination_url: item.destination_url || null, fingerprint: item.fingerprint || null, evidence };
  });
  return { claim_id: input.claim_id, items };
}

export function validateProgress(input) {
  if (!input || typeof input !== "object" || !idPattern.test(input.claim_id || "")) throw invalid("Invalid claim");
  const coverage = input.coverage;
  if (!coverage || typeof coverage !== "object" || Array.isArray(coverage) || !new Set(["partial", "unavailable"]).has(coverage.state)) throw invalid("Progress needs incomplete coverage");
  for (const key of ["discovered", "checked", "unavailable", "unresolved"]) if (!Number.isSafeInteger(coverage[key]) || coverage[key] < 0) throw invalid("Coverage counts must be nonnegative integers");
  if (coverage.checked + coverage.unavailable + coverage.unresolved > coverage.discovered) throw invalid("Coverage counts exceed discovery");
  return { claim_id: input.claim_id, coverage: { state: coverage.state, discovered: coverage.discovered, checked: coverage.checked, unavailable: coverage.unavailable, unresolved: coverage.unresolved } };
}

export function verifyFamilyMatch(item, criteria) {
  if (item.outcome !== "MATCH") return;
  const details = item.details;
  if (typeof details.deal_name !== "string" || !details.deal_name.trim() || typeof details.restaurant !== "string" || !details.restaurant.trim()) throw invalid("Verified match needs a deal and restaurant");
  if (!Number.isSafeInteger(details.price_cents) || details.price_cents < 0 || details.price_cents > Math.round(criteria.max_total_price * 100)) throw invalid("Verified total exceeds the search budget or is unknown");
  if (!Number.isInteger(details.serves_max) || details.serves_max < criteria.party_size || details.serves_max > 10) throw invalid("Serving capacity does not cover the party");
  if (!["meal_verified", "price_verified", "capacity_verified", "location_verified"].every((key) => details[key] === true)) throw invalid("Verified match is missing required evidence flags");
  if (criteria.open_tonight && details.open_tonight_verified !== true) throw invalid("Dinner hours are not verified");
}

export function validateCompletion(input, verifiedMatches) {
  if (!input || !idPattern.test(input.claim_id || "") || !new Set(["MATCH", "NO_MATCH", "PARTIAL", "UNAVAILABLE", "ERROR"]).has(input.outcome)) throw invalid("Invalid completion state");
  if (!shortText(input.summary, 800) || !input.summary?.trim()) throw invalid("Completion needs a short summary");
  const coverage = input.coverage;
  if (!coverage || typeof coverage !== "object" || Array.isArray(coverage) || !new Set(["complete", "partial", "unavailable"]).has(coverage.state)) throw invalid("Completion needs truthful coverage");
  for (const key of ["discovered", "checked", "unavailable", "unresolved"]) if (!Number.isSafeInteger(coverage[key]) || coverage[key] < 0) throw invalid("Coverage counts must be nonnegative integers");
  if (coverage.checked + coverage.unavailable + coverage.unresolved > coverage.discovered) throw invalid("Coverage counts exceed discovery");
  if (coverage.state === "complete" && (coverage.checked !== coverage.discovered || coverage.unavailable || coverage.unresolved)) throw invalid("Complete coverage counts disagree");
  if (input.outcome === "NO_MATCH" && (verifiedMatches || coverage.state !== "complete")) throw invalid("No-match requires a complete check and no verified results");
  if (input.outcome === "MATCH" && !verifiedMatches) throw invalid("Match requires verified results");
  if (input.outcome === "PARTIAL" && coverage.state === "complete") throw invalid("Partial outcome needs partial coverage");
  return { claim_id: input.claim_id, outcome: input.outcome, summary: input.summary, coverage: { state: coverage.state, discovered: coverage.discovered, checked: coverage.checked, unavailable: coverage.unavailable, unresolved: coverage.unresolved } };
}

export async function digest(value) {
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(value))));
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
