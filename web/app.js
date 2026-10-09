(() => {
  const moduleLabels = { movies: "Movies", "family-deals": "Family Deals" };
  const state = { watches: [], results: [], resultDetails: {}, csrfToken: "", currentSearchId: "", pollTimer: null, pollCount: 0 };
  const byId = (id) => document.getElementById(id);
  const all = (selector) => [...document.querySelectorAll(selector)];
  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));

  function selectView(view) {
    const target = document.querySelector(`[data-page="${view}"]`) || document.querySelector('[data-page="home"]');
    all("[data-page]").forEach((page) => page.classList.toggle("is-visible", page === target));
    all("[data-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.view === view));
    document.body.classList.remove("menu-open");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function formatTime(value) {
    if (!value) return "Any time";
    const [hourText, minute] = value.split(":"); const hour = Number(hourText);
    return `${hour % 12 || 12}:${minute} ${hour >= 12 ? "PM" : "AM"}`;
  }
  const selectedTheaters = () => all('input[name="theaters"]:checked').map((input) => input.value);
  function movieCriteria() {
    const dateMode = document.querySelector('input[name="date-mode"]:checked')?.value || "Next best available";
    return { schema_version: 1, movie: byId("movie-title").value.trim(), location: byId("movie-location").value.trim(), radius: byId("movie-radius").value, theaters: selectedTheaters(), date_mode: dateMode, specific_date: byId("specific-date").value, date_from: byId("date-from").value, date_to: byId("date-to").value, earliest_time: byId("earliest-time").value, latest_time: byId("latest-time").value, seats_together: Number(byId("seat-count").value), minimum_row: byId("minimum-row").value.trim(), format: byId("movie-format").value, excluded_theaters: byId("excluded-theaters").value.trim() };
  }
  function updateSummary() {
    const c = movieCriteria(); byId("selected-movie-title").textContent = c.movie || "Enter a movie"; byId("summary-movie").textContent = c.movie || "Not selected";
    byId("summary-location").textContent = `${c.location || "Not selected"} (${c.radius})`; byId("summary-theaters").textContent = `${c.theaters.length} selected`;
    let dateText = c.date_mode; if (c.date_mode === "Specific date" && c.specific_date) dateText = c.specific_date; if (c.date_mode === "Date range" && (c.date_from || c.date_to)) dateText = `${c.date_from || "Start"} – ${c.date_to || "End"}`;
    byId("summary-date").textContent = dateText; byId("summary-time").textContent = `${formatTime(c.earliest_time)} – ${formatTime(c.latest_time)}`; byId("summary-seats").textContent = `${c.seats_together} together${c.minimum_row ? ` (min row ${c.minimum_row})` : ""}`; byId("summary-format").textContent = c.format;
  }
  const restaurantTypes = { any: "Any", independent_local: "Independent + local", independent: "Independent only", chains: "Chains only" };
  function dealCriteria() {
    const location = byId("deal-location").value.trim();
    return { schema_version: 1, location, radius_miles: Number(byId("deal-radius").value), party_size: Number(byId("deal-party-size").value), max_total_price: Number(byId("deal-budget").value), cuisines: all('input[name="deal-cuisine"]:checked').map((input) => input.value), restaurant_type: byId("deal-restaurant-type").value, open_tonight: byId("deal-open-tonight").checked };
  }
  function updateDealSummary() {
    const c = dealCriteria();
    byId("deal-summary-location").textContent = c.location || "Add a location";
    byId("deal-summary-radius").textContent = `${c.radius_miles || "?"} miles`;
    byId("deal-summary-party").textContent = `${c.party_size} people`;
    byId("deal-summary-budget").textContent = byId("deal-budget").value ? `${c.max_total_price.toFixed(2)} total` : "Add a maximum";
    const names = all('input[name="deal-cuisine"]:checked').map((input) => input.parentElement.textContent.trim());
    byId("deal-summary-cuisine").textContent = names.join(", ") || "Any cuisine";
    byId("deal-summary-type").textContent = restaurantTypes[c.restaurant_type];
    byId("deal-summary-hours").textContent = c.open_tonight ? "Open tonight, if verified" : "Any availability";
  }
  async function apiRequest(path, options = {}) {
    const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
    if (state.csrfToken && options.method && options.method !== "GET") headers["X-CSRF-Token"] = state.csrfToken;
    const response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }
  function setAuthMessage(message) { const el = byId("deal-auth-message"); if (el) el.textContent = message; }
  function setConnected(connected) {
    byId("deal-access-secret").disabled = connected;
    byId("deal-auth-form").querySelector('button[type="submit"]').textContent = connected ? "Connected" : "Connect";
    setAuthMessage(connected ? "Connected securely. Ready for a one-time search." : "Not connected.");
  }
  async function connectDealSession(secret = "") {
    if (secret) {
      const data = await apiRequest("/api/v1/session", { method: "POST", body: JSON.stringify({ access_secret: secret }) });
      state.csrfToken = data.csrf_token || "";
    } else {
      const data = await apiRequest("/api/v1/session");
      state.csrfToken = data.csrf_token || "";
    }
    setConnected(true);
  }
  function renderLiveDealResults(results, provisional) {
    const panel = byId("deal-preview-result");
    panel.hidden = false;
    const cards = results.map((r) => {
      const d = r.details || {};
      const evidence = (r.evidence || []).map((e) => {
        const source = escapeHtml(e.source || "Source");
        const summary = escapeHtml(e.summary || "");
        const url = typeof e.source_url === "string" && /^https:\/\//i.test(e.source_url) ? e.source_url : "";
        return `<li>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${source}</a>` : source}: ${summary}</li>`;
      }).join("");
      const price = Number.isInteger(d.price_cents) ? `${(d.price_cents / 100).toFixed(2)} total` : "Total price not verified";
      const serves = d.serves_max ? `Serves up to ${escapeHtml(d.serves_max)}` : "Serving capacity not verified";
      const restaurant = escapeHtml(d.restaurant || r.title || "Meal deal");
      const dealName = escapeHtml(d.deal_name || r.title || "Meal deal");
      const destination = typeof r.destination_url === "string" && /^https:\/\//i.test(r.destination_url) ? r.destination_url : "";
      return `<article class="watch-item"><span class="result-badge result-${escapeHtml(r.outcome)}">${escapeHtml(r.outcome)}</span><div><strong>${dealName}</strong><small>${restaurant} · ${price} · ${serves}</small><p>${escapeHtml(r.summary || "")}</p>${evidence ? `<ul>${evidence}</ul>` : ""}${destination ? `<a href="${escapeHtml(destination)}" target="_blank" rel="noopener noreferrer">View deal source</a>` : ""}</div></article>`;
    }).join("");
    panel.innerHTML = `<div class="result-state-icon">${provisional ? "◷" : "✓"}</div><div><p class="eyebrow">${provisional ? "PROVISIONAL RESULTS" : "SEARCH RESULTS"}</p><h2>${results.length ? `${results.length} candidate${results.length === 1 ? "" : "s"} found` : "No candidates published yet"}</h2><p>${provisional ? "These are early candidates, not a final result. Keep this page open while full-radius coverage is checked." : "Search finished. Coverage and verification status determine whether the result is a confirmed match or an incomplete search."}</p></div><div class="full-list">${cards || "<p>No candidate results have arrived yet.</p>"}</div>`;
  }
  async function fetchAllSearchResults(searchId) {
    const results = [], seen = new Set();
    let cursor = null;
    do {
      const query = new URLSearchParams({ search_id: searchId, limit: "50" });
      if (cursor) { query.set("before", cursor.before); query.set("before_id", cursor.before_id); }
      const data = await apiRequest(`/api/v1/results?${query}`);
      for (const result of data.results || []) if (!seen.has(result.id)) { seen.add(result.id); results.push(result); }
      cursor = data.next_cursor || null;
    } while (cursor);
    await Promise.all(results.map(async (result) => {
      if (state.resultDetails[result.id]) { Object.assign(result, state.resultDetails[result.id]); return; }
      try {
        const detail = await apiRequest(`/api/v1/results/${encodeURIComponent(result.id)}`);
        state.resultDetails[result.id] = detail;
        Object.assign(result, detail);
      } catch { /* A provisional row can briefly precede its evidence record. */ }
    }));
    return results;
  }
  function renderSearchProgress(search, results) {
    const panel = byId("deal-preview-result");
    const coverage = search.coverage;
    const coverageLine = coverage
      ? `Radius: ${coverage.radius_discovered ?? "unknown"} restaurants discovered · Verification: ${coverage.checked ?? 0} of ${coverage.discovered ?? 0} checked · ${coverage.unavailable ?? 0} unavailable · ${coverage.unresolved ?? 0} unresolved`
      : "Coverage summary pending until verification completes";
    const statusText = ({ QUEUED: "Search queued", RUNNING: "Checking the full radius", COMPLETED: search.last_outcome || "Search completed", FAILED: "Search failed", DELAYED: "Search delayed" })[search.status] || search.status;
    renderLiveDealResults(results, ["QUEUED", "RUNNING"].includes(search.status));
    const summary = document.createElement("p");
    summary.textContent = `${statusText}. ${coverageLine}.`;
    panel.prepend(summary);
    if (search.status === "COMPLETED" || search.status === "FAILED" || search.status === "DELAYED") {
      window.clearTimeout(state.pollTimer); state.pollTimer = null;
      state.currentSearchId = "";
      byId("deal-search-form").querySelector('button[type="submit"]').disabled = false;
    }
  }
  async function pollFamilySearch(searchId) {
    if (state.currentSearchId !== searchId) return;
    if (state.pollCount >= 240) {
      const panel = byId("deal-preview-result");
      if (panel && !panel.querySelector("[data-poll-limit-note]")) {
        const note = document.createElement("p");
        note.dataset.pollLimitNote = "true";
        note.textContent = "This search is taking longer than expected. Automatic refresh has paused, but the search has not been marked as failed.";
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "button button-outline";
        retry.dataset.resumeFamilySearch = "true";
        retry.textContent = "Check status again";
        note.append(" ", retry);
        panel.append(note);
      }
      state.pollTimer = null;
      return;
    }
    state.pollCount++;
    try {
      const [search, results] = await Promise.all([
        apiRequest(`/api/v1/searches/${encodeURIComponent(searchId)}`),
        fetchAllSearchResults(searchId)
      ]);
      renderSearchProgress(search, results);
      if (["QUEUED", "RUNNING"].includes(search.status)) state.pollTimer = window.setTimeout(() => pollFamilySearch(searchId), 2500);
    } catch (error) {
      showToast(error.message || "Could not refresh search progress.");
      state.pollTimer = window.setTimeout(() => pollFamilySearch(searchId), 5000);
    }
  }
  async function submitFamilyDealsSearch() {
    const form = byId("deal-search-form");
    const submitButton = form.querySelector('button[type="submit"]');
    if (state.currentSearchId) { showToast("Your current Family Deals search is still running."); return; }
    if (!form.reportValidity()) return;
    if (!state.csrfToken) {
      byId("deal-auth-panel").scrollIntoView({ behavior: "smooth", block: "center" });
      setAuthMessage("Connect first, then run your one-time search.");
      byId("deal-access-secret").focus();
      return;
    }
    const criteria = dealCriteria();
    if (!criteria.location || !Number.isFinite(criteria.max_total_price) || criteria.max_total_price <= 0) {
      showToast("Enter a location and a maximum total price.");
      return;
    }
    try {
      submitButton.disabled = true;
      window.clearTimeout(state.pollTimer);
      state.currentSearchId = ""; state.pollCount = 0;
      const created = await apiRequest("/api/v1/searches", { method: "POST", body: JSON.stringify({ module: "family-deals", criteria }) });
      state.currentSearchId = created.id;
      const panel = byId("deal-preview-result"); panel.hidden = false;
      panel.innerHTML = `<div class="result-state-icon">◷</div><div><p class="eyebrow">ONE-TIME SEARCH</p><h2>Search ${escapeHtml(created.status || "queued")}</h2><p>Search ID: ${escapeHtml(created.id)}. Worker dispatch: ${escapeHtml(created.dispatch || "unknown")}.</p></div>`;
      if (created.dispatch === "signaled" || created.dispatch === "idle") {
        pollFamilySearch(created.id);
      } else {
        state.currentSearchId = "";
        submitButton.disabled = false;
        const detail = document.createElement("p");
        detail.textContent = "The search is saved, but the execution worker has not confirmed a run. No results will be invented. This needs backend dispatch configuration before it can run live.";
        panel.append(detail);
      }
      panel.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) {
      submitButton.disabled = false;
      showToast(error.message || "Family Deals search could not be started.");
      setAuthMessage(error.message || "Connection needs attention.");
    }
  }

  function showToast(message) {
    const toast = byId("toast"); toast.textContent = message; toast.classList.add("is-visible"); window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3600);
  }
  function showOfflineResult() {
    const panel = byId("movie-preview-result"); panel.hidden = false;
    panel.innerHTML = '<div class="result-state-icon">◷</div><div><p class="eyebrow">SEARCH READY</p><h2>Your criteria are configured</h2><p>The interface did not contact AMC. Live Movies search remains paused while AMC is serving its temporary block page; this is an unavailable provider state, not a no-match result.</p></div><button class="button button-watch" type="button" data-save-watch>♧ &nbsp; Keep Watching</button>';
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function showDealPreview() {
    const panel = byId("deal-preview-result"); panel.hidden = false;
    panel.innerHTML = '<div class="result-state-icon">◷</div><div><p class="eyebrow">SEARCH CONFIGURED</p><h2>Live deal verification is unavailable in this preview</h2><p>No restaurants were checked, so there is no result or coverage count yet. The production search will show deals first with verified total price, serving capacity, included food, source, distance, and last checked time. Sources that cannot be verified will appear in coverage details.</p></div><button class="button button-watch" type="button" data-save-deal-watch>♧ &nbsp; Save this Search</button>';
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const statusLabel = (status) => ({ draft: "Saved", active: "Watching", paused: "Paused", completed: "Stopped", error: "Needs attention" })[status] || "Saved";
  function criteriaSummary(watch) {
    const c = watch.criteria || {};
    if (watch.module === "family-deals") return `${c.location || "Location pending"} · ${c.radius_miles || "?"} miles · ${c.party_size || "?"} people · $${c.max_total_price || "?"} total`;
    if (watch.module !== "movies") return watch.query;
    return `${c.location || "Location pending"} · ${Array.isArray(c.theaters) ? c.theaters.length : 0} theaters · ${c.seats_together || "?"} seats · ${c.format || "Any format"}`;
  }
  function watchControls(watch) {
    const id = escapeHtml(watch.watch_id || ""); if (!id) return "";
    if (watch.status === "draft") return `<button type="button" data-watch-action="active" data-watch-id="${id}">Start</button>`;
    if (watch.status === "active") return `<button type="button" data-watch-action="paused" data-watch-id="${id}">Pause</button><button type="button" data-watch-action="completed" data-watch-id="${id}">Stop</button>`;
    if (watch.status === "paused") return `<button type="button" data-watch-action="active" data-watch-id="${id}">Resume</button><button type="button" data-watch-action="completed" data-watch-id="${id}">Stop</button>`; return "";
  }
  function renderWatches() {
    const list = byId("watch-list"), section = byId("home-watch-section"), homeList = byId("home-watch-list"); section.hidden = !state.watches.length;
    if (!state.watches.length) { list.className = "full-list empty-state"; list.innerHTML = '<span>♧</span><h2>No watches yet</h2><p>Save a search and its exact criteria will appear here as a preview draft.</p><button class="button button-primary" type="button" data-view="home">Start a Search</button>'; homeList.innerHTML = ""; return; }
    const markup = state.watches.map((watch) => `<article class="watch-item"><span class="page-icon ${watch.module === "movies" ? "movie-glyph" : "family-glyph"}">${watch.module === "movies" ? "▦" : "♨"}</span><div><strong>${escapeHtml(watch.query)}</strong><small>${escapeHtml(moduleLabels[watch.module] || watch.module)} · ${escapeHtml(criteriaSummary(watch))}</small></div><span class="watch-status watch-status-${escapeHtml(watch.status)}">${statusLabel(watch.status)}</span><div class="watch-actions">${watchControls(watch)}</div></article>`).join("");
    list.className = "full-list"; list.innerHTML = markup; homeList.innerHTML = markup;
  }
  function renderResults() {
    const list = byId("result-list"), section = byId("home-result-section"), homeList = byId("home-result-list"); section.hidden = !state.results.length; if (!state.results.length) return;
    const markup = state.results.map((result) => `<article class="watch-item"><span class="result-badge result-${escapeHtml(result.outcome)}">${escapeHtml(result.outcome)}</span><div><strong>${escapeHtml(result.title)}</strong><small>${escapeHtml(result.reason || result.verification || "Evidence recorded")}</small></div></article>`).join(""); list.className = "full-list"; list.innerHTML = markup; homeList.innerHTML = markup;
  }
  function addDraft(watch) { state.watches.unshift(watch); renderWatches(); showToast("Search criteria saved as a local preview watch."); }
  async function createDraft(module = "movies") {
    const form = byId(module === "movies" ? "movie-search-form" : "deal-search-form");
    if (!form.reportValidity()) return;
    const criteria = module === "movies" ? movieCriteria() : dealCriteria();
    const query = module === "movies" ? criteria.movie : `Family deals near ${criteria.location}`;
    if (!query) { byId("movie-title").focus(); showToast("Enter a movie title first."); return; }
    const payload = { module, query, criteria };
    try { const response = await fetch("/api/watches", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); if (!response.ok) throw new Error("Local preview API unavailable"); addDraft(await response.json()); }
    catch (_error) { addDraft({ watch_id: `browser-draft-${Date.now()}`, module, query, criteria, status: "draft" }); }
  }
  async function changeWatchStatus(watchId, status) {
    const watch = state.watches.find((item) => item.watch_id === watchId); if (!watch) return;
    try { const response = await fetch(`/api/watches/${encodeURIComponent(watchId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); if (!response.ok) throw new Error("Local preview API unavailable"); Object.assign(watch, await response.json()); }
    catch (_error) { const allowed = { draft: ["active"], active: ["paused", "completed"], paused: ["active", "completed"] }; if (!(allowed[watch.status] || []).includes(status)) return; watch.status = status; } renderWatches();
  }
  async function hydrate() {
    try { const [watchResponse, resultResponse] = await Promise.all([fetch("/api/watches", { cache: "no-store" }), fetch("/api/results", { cache: "no-store" })]); if (watchResponse.ok) { const watches = await watchResponse.json(); if (Array.isArray(watches)) state.watches = watches.filter((watch) => Object.hasOwn(moduleLabels, watch.module)); } if (resultResponse.ok) { const results = await resultResponse.json(); if (Array.isArray(results)) state.results = results.filter((result) => Object.hasOwn(moduleLabels, result.module)); } renderWatches(); renderResults(); } catch (_error) { /* Static preview remains useful without the API. */ }
  }
  document.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-view]"); if (viewButton) selectView(viewButton.dataset.view);
    if (event.target.closest("[data-mobile-menu]")) document.body.classList.toggle("menu-open"); if (event.target.closest("[data-focus-first]")) byId("movie-title").focus();
    if (event.target.closest("[data-select-all]")) { const boxes = all('input[name="theaters"]'); const select = boxes.some((box) => !box.checked); boxes.forEach((box) => { box.checked = select; }); updateSummary(); }
    if (event.target.closest("[data-save-watch]")) createDraft(); if (event.target.closest("[data-save-deal-watch]")) createDraft("family-deals"); if (event.target.closest("[data-focus-deal]")) byId("deal-location").focus();
    if (event.target.closest("[data-preview-action]")) showToast("Provider request skipped — AMC block protection is active."); if (event.target.closest("[data-location]")) showToast("Location access is not requested in this offline preview."); if (event.target.closest("[data-help]")) showToast("Configure a search, search once, then save the same criteria as a Watch.");
    if (event.target.closest("[data-deal-location]")) {
      if (!navigator.geolocation) { showToast("Location is unavailable in this browser. Enter an address or ZIP instead."); return; }
      navigator.geolocation.getCurrentPosition(({ coords }) => { byId("deal-location").value = `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)}`; updateDealSummary(); }, () => showToast("Location access was unavailable. Enter an address or ZIP instead."), { timeout: 10000, maximumAge: 300000 });
    }
    const action = event.target.closest("[data-watch-action]"); if (action) changeWatchStatus(action.dataset.watchId, action.dataset.watchAction);
    if (event.target.closest("[data-resume-family-search]") && state.currentSearchId) {
      state.pollCount = 0;
      pollFamilySearch(state.currentSearchId);
    }
  });
  byId("movie-search-form").addEventListener("input", updateSummary); byId("movie-search-form").addEventListener("change", updateSummary); byId("movie-search-form").addEventListener("submit", (event) => { event.preventDefault(); updateSummary(); showOfflineResult(); });
  byId("deal-search-form").addEventListener("input", updateDealSummary); byId("deal-search-form").addEventListener("change", updateDealSummary); byId("deal-search-form").addEventListener("submit", (event) => { event.preventDefault(); updateDealSummary(); submitFamilyDealsSearch(); });
  byId("deal-auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = byId("deal-access-secret");
    try { await connectDealSession(input.value); input.value = ""; showToast("Connected. Your one-time search is ready."); }
    catch (error) { setAuthMessage(error.message || "Connection failed."); showToast(error.message || "Connection failed."); }
  });
  connectDealSession().catch(() => setConnected(false));
  updateSummary(); updateDealSummary(); renderWatches(); renderResults(); hydrate();
})();
