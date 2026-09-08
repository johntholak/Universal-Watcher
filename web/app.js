(() => {
  const moduleLabels = { movies: "Movies", "family-deals": "Family Deals" };
  const state = { watches: [], results: [] };
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
    return { movie: byId("movie-title").value.trim(), location: byId("movie-location").value.trim(), radius: byId("movie-radius").value, theaters: selectedTheaters(), date_mode: dateMode, specific_date: byId("specific-date").value, date_from: byId("date-from").value, date_to: byId("date-to").value, earliest_time: byId("earliest-time").value, latest_time: byId("latest-time").value, seats_together: Number(byId("seat-count").value), minimum_row: byId("minimum-row").value.trim(), format: byId("movie-format").value, excluded_theaters: byId("excluded-theaters").value.trim() };
  }
  function updateSummary() {
    const c = movieCriteria(); byId("selected-movie-title").textContent = c.movie || "Enter a movie"; byId("summary-movie").textContent = c.movie || "Not selected";
    byId("summary-location").textContent = `${c.location || "Not selected"} (${c.radius})`; byId("summary-theaters").textContent = `${c.theaters.length} selected`;
    let dateText = c.date_mode; if (c.date_mode === "Specific date" && c.specific_date) dateText = c.specific_date; if (c.date_mode === "Date range" && (c.date_from || c.date_to)) dateText = `${c.date_from || "Start"} – ${c.date_to || "End"}`;
    byId("summary-date").textContent = dateText; byId("summary-time").textContent = `${formatTime(c.earliest_time)} – ${formatTime(c.latest_time)}`; byId("summary-seats").textContent = `${c.seats_together} together${c.minimum_row ? ` (min row ${c.minimum_row})` : ""}`; byId("summary-format").textContent = c.format;
  }
  function showToast(message) {
    const toast = byId("toast"); toast.textContent = message; toast.classList.add("is-visible"); window.clearTimeout(showToast.timer); showToast.timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3600);
  }
  function showOfflineResult() {
    const panel = byId("movie-preview-result"); panel.hidden = false;
    panel.innerHTML = '<div class="result-state-icon">◷</div><div><p class="eyebrow">SEARCH READY</p><h2>Your criteria are configured</h2><p>The interface did not contact AMC. Live Movies search remains paused while AMC is serving its temporary block page; this is an unavailable provider state, not a no-match result.</p></div><button class="button button-watch" type="button" data-save-watch>♧ &nbsp; Keep Watching</button>';
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const statusLabel = (status) => ({ draft: "Saved", active: "Watching", paused: "Paused", completed: "Stopped", error: "Needs attention" })[status] || "Saved";
  function criteriaSummary(watch) {
    const c = watch.criteria || {}; if (watch.module !== "movies") return watch.query;
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
    if (!state.watches.length) { list.className = "full-list empty-state"; list.innerHTML = '<span>♧</span><h2>No watches yet</h2><p>Save a Movies search and its exact criteria will appear here.</p><button class="button button-primary" type="button" data-view="movies">Start a Movies Search</button>'; homeList.innerHTML = ""; return; }
    const markup = state.watches.map((watch) => `<article class="watch-item"><span class="page-icon ${watch.module === "movies" ? "movie-glyph" : "family-glyph"}">${watch.module === "movies" ? "▦" : "♨"}</span><div><strong>${escapeHtml(watch.query)}</strong><small>${escapeHtml(moduleLabels[watch.module] || watch.module)} · ${escapeHtml(criteriaSummary(watch))}</small></div><span class="watch-status watch-status-${escapeHtml(watch.status)}">${statusLabel(watch.status)}</span><div class="watch-actions">${watchControls(watch)}</div></article>`).join("");
    list.className = "full-list"; list.innerHTML = markup; homeList.innerHTML = markup;
  }
  function renderResults() {
    const list = byId("result-list"), section = byId("home-result-section"), homeList = byId("home-result-list"); section.hidden = !state.results.length; if (!state.results.length) return;
    const markup = state.results.map((result) => `<article class="watch-item"><span class="result-badge result-${escapeHtml(result.outcome)}">${escapeHtml(result.outcome)}</span><div><strong>${escapeHtml(result.title)}</strong><small>${escapeHtml(result.reason || result.verification || "Evidence recorded")}</small></div></article>`).join(""); list.className = "full-list"; list.innerHTML = markup; homeList.innerHTML = markup;
  }
  function addDraft(watch) { state.watches.unshift(watch); renderWatches(); showToast("Search criteria saved as a local preview watch."); }
  async function createDraft() {
    const criteria = movieCriteria(); if (!criteria.movie) { byId("movie-title").focus(); showToast("Enter a movie title first."); return; }
    const payload = { module: "movies", query: criteria.movie, criteria };
    try { const response = await fetch("/api/watches", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); if (!response.ok) throw new Error("Local preview API unavailable"); addDraft(await response.json()); }
    catch (_error) { addDraft({ watch_id: `browser-draft-${Date.now()}`, module: "movies", query: criteria.movie, criteria, status: "draft" }); }
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
    if (event.target.closest("[data-save-watch]")) createDraft(); if (event.target.closest("[data-preview-action]")) showToast("Provider request skipped — AMC block protection is active."); if (event.target.closest("[data-location]")) showToast("Location access is not requested in this offline preview."); if (event.target.closest("[data-help]")) showToast("Configure a search, search once, then save the same criteria as a Watch.");
    const action = event.target.closest("[data-watch-action]"); if (action) changeWatchStatus(action.dataset.watchId, action.dataset.watchAction);
  });
  byId("movie-search-form").addEventListener("input", updateSummary); byId("movie-search-form").addEventListener("change", updateSummary); byId("movie-search-form").addEventListener("submit", (event) => { event.preventDefault(); updateSummary(); showOfflineResult(); });
  updateSummary(); renderWatches(); renderResults(); hydrate();
})();
