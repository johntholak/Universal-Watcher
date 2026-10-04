(() => {
  const moduleLabels = { movies: "Seat Finder", "movie-gm": "Streaming GM", "family-deals": "Family Deals" };
  const state = { watches: [], results: [] };
  const familyDealsState = { searchId: "", pollTimer: null, pollCount: 0 };
  const byId = (id) => document.getElementById(id);
  const all = (selector) => [...document.querySelectorAll(selector)];
  const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  const movieApi = { production: !["localhost", "127.0.0.1"].includes(window.location.hostname), csrf: "", ready: false, bootstrapPromise: null };

  function movieApiPath(path) {
    if (!movieApi.production) return path;
    if (path.startsWith("/api/")) return `/api/v1${path.slice(4)}`;
    return `/api/v1${path}`;
  }

  async function movieApiFetch(path, options = {}) {
    if (movieApi.bootstrapPromise) await movieApi.bootstrapPromise;
    const requestOptions = { credentials: "same-origin", cache: "no-store", ...options };
    const headers = new Headers(requestOptions.headers || {});
    if (movieApi.production && requestOptions.method && requestOptions.method !== "GET") {
      headers.set("X-CSRF-Token", movieApi.csrf);
    }
    requestOptions.headers = headers;
    const response = await fetch(movieApiPath(path), requestOptions);
    return response;
  }


  async function bootstrapMovieApi() {
    try {
      try {
        const statusResponse = await fetch("/api/v1/system/status", { credentials: "same-origin", cache: "no-store" });
        if (statusResponse.ok) {
          const status = await statusResponse.json();
          if (status.state === "production") movieApi.production = true;
        } else if (statusResponse.status !== 404) {
          movieApi.production = true;
        }
      } catch (_error) {
        // Production detection is advisory. Do not block the existing session bootstrap.
      }

      const response = await fetch("/api/v1/session", { credentials: "same-origin", cache: "no-store" });
      if (response.status === 404 && !movieApi.production) {
        movieApi.ready = true;
        return;
      }
      movieApi.production = true;
      const previewBanner = byId("movie-preview-banner");
      if (previewBanner) previewBanner.hidden = true;
      if (response.ok) {
        const data = await response.json();
        movieApi.csrf = data.csrf_token || "";
      } else if (response.status === 401) {
        const demoResponse = await fetch("/api/v1/session?mode=demo", { credentials: "same-origin", cache: "no-store" });
        if (demoResponse.ok) {
          const data = await demoResponse.json();
          movieApi.csrf = data.csrf_token || "";
        }
      }
      movieApi.ready = true;
    } catch (_error) {
      movieApi.ready = true;
    }
  }

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
    byId("deal-summary-budget").textContent = byId("deal-budget").value ? `$${c.max_total_price.toFixed(2)} total` : "Add a maximum";
    const names = all('input[name="deal-cuisine"]:checked').map((input) => input.parentElement.textContent.trim());
    byId("deal-summary-cuisine").textContent = names.join(", ") || "Any cuisine";
    byId("deal-summary-type").textContent = restaurantTypes[c.restaurant_type];
    byId("deal-summary-hours").textContent = c.open_tonight ? "Open tonight, if verified" : "Any availability";
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
    panel.innerHTML = '<div class="result-state-icon">◷</div><div><p class="eyebrow">PREVIEW ONLY</p><h2>Family Deals live checking is not connected</h2><p>This local preview does not contact restaurant sources. The production Universal Watcher site will run the full-radius search and show verified or clearly partial results with source evidence.</p></div>';
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function setFamilyBanner(connected) {
    const banner = byId("family-deals-preview-banner");
    if (banner) banner.hidden = connected;
  }

  function familyResultCard(result) {
    const d = result.details || {};
    const evidence = Array.isArray(result.evidence) ? result.evidence[0] : null;
    const price = Number.isFinite(Number(d.price_cents)) ? "$" + (Number(d.price_cents) / 100).toFixed(2) : "Price unavailable";
    const serving = d.serving_label || (d.serves_max ? "Serves up to " + d.serves_max : "Serving capacity not shown");
    const distance = Number.isFinite(Number(d.distance_miles)) ? Number(d.distance_miles).toFixed(1) + " mi" : "Distance unknown";
    const classification = d.classification && d.classification !== "unknown" ? d.classification : "Classification unknown";
    const destination = result.destination_url ? '<a class="deal-result-link" href="' + escapeHtml(result.destination_url) + '" target="_blank" rel="noopener">View official source ↗</a>' : "";
    return '<article class="deal-result-card"><div class="deal-result-top"><div><span class="result-badge result-' + escapeHtml(result.outcome) + '">' + escapeHtml(result.outcome) + '</span><h3>' + escapeHtml(d.restaurant || result.title) + '</h3></div><strong class="deal-price">' + escapeHtml(price) + '</strong></div><p class="deal-result-summary">' + escapeHtml(result.summary || "") + '</p><dl class="deal-result-facts"><div><dt>Serves</dt><dd>' + escapeHtml(serving) + '</dd></div><div><dt>Distance</dt><dd>' + escapeHtml(distance) + '</dd></div><div><dt>Type</dt><dd>' + escapeHtml(classification) + '</dd></div></dl>' + (evidence ? '<div class="deal-evidence"><strong>Source evidence</strong><p>' + escapeHtml(evidence.summary || "") + '</p></div>' : "") + '<div class="deal-result-actions">' + destination + '<span class="deal-location-note">' + (d.location_verified ? "Location verified" : "Location applicability needs confirmation") + '</span></div></article>';
  }

  async function loadFamilyResults(searchId) {
    const response = await movieApiFetch("/api/results?search_id=" + encodeURIComponent(searchId) + "&limit=50");
    if (!response.ok) return null;
    const data = await response.json();
    return Array.isArray(data.results) ? data.results : [];
  }

  function renderFamilySearchState(status, search, results) {
    results = results || [];
    const panel = byId("deal-preview-result"); panel.hidden = false;
    const coverage = search && search.coverage;
    const coverageText = coverage ? (coverage.checked || 0) + " checked · " + (coverage.unavailable || 0) + " unavailable · " + (coverage.unresolved || 0) + " unresolved" : "Coverage will appear when the scan finishes.";
    let heading = "Family Deals search";
    let body = "Universal Watcher is checking the full selected radius. You can leave this page open while the worker runs.";
    let icon = "◷";
    if (status === "COMPLETED") {
      heading = results.length ? results.length + " family meal candidate" + (results.length === 1 ? "" : "s") + " found" : "No verified family deal matches";
      body = search.last_outcome === "PARTIAL" ? "The scan completed, but some candidates still need location applicability confirmation. They are shown below rather than being promoted to verified matches." : (search.last_outcome === "NO_MATCH" ? "The full selected radius was checked and no verified match was found." : "The scan completed.");
      icon = results.length ? "✓" : "◌";
    } else if (status === "FAILED") {
      heading = "Family Deals search could not finish";
      body = "The worker reported a failure. This is not a no-match result.";
      icon = "!";
    } else if (status === "DELAYED") {
      heading = "Family Deals search is delayed";
      body = "The free execution allowance is temporarily full. Universal Watcher will retry when capacity is available.";
    } else if (status === "RUNNING") {
      heading = "Family Deals search is running";
      body = "The cloud worker is actively checking restaurants and official sources. No Mac or local computer is required.";
    } else if (status === "QUEUED") {
      heading = "Family Deals search queued";
      body = "Your search is queued for the cloud worker. No Mac or local computer is required.";
    }
    const save = status === "COMPLETED" ? '<button class="button button-watch" type="button" data-save-deal-watch>♧ &nbsp; Save this Search as a Watch</button>' : "";
    const cards = results.map(familyResultCard).join("");
    panel.innerHTML = '<div class="family-search-status"><div class="result-state-icon">' + icon + '</div><div><p class="eyebrow">' + escapeHtml(status) + '</p><h2>' + escapeHtml(heading) + '</h2><p>' + escapeHtml(body) + '</p><small>' + escapeHtml(coverageText) + '</small></div></div>' + (cards ? '<div class="deal-results-list">' + cards + '</div>' : "") + save;
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function pollFamilySearch(searchId) {
    if (familyDealsState.pollTimer) window.clearTimeout(familyDealsState.pollTimer);
    try {
      const response = await movieApiFetch("/api/searches/" + encodeURIComponent(searchId));
      if (!response.ok) throw new Error("Could not read Family Deals search status");
      const search = await response.json();
      const status = search.status === "QUEUED" && ["CLAIMED", "RUNNING"].includes(search.job_status) ? "RUNNING" : (search.status || "QUEUED");
      let results = [];
      if (status === "COMPLETED") {
        results = await loadFamilyResults(searchId) || [];
        state.results = results.map((item) => ({ ...item, module: "family-deals", reason: item.summary }));
        renderResults();
      }
      renderFamilySearchState(status, search, results);
      if (!["COMPLETED", "FAILED", "DELAYED"].includes(status) && familyDealsState.pollCount < 240) {
        familyDealsState.pollCount += 1;
        familyDealsState.pollTimer = window.setTimeout(() => pollFamilySearch(searchId), 5000);
      }
      if (status === "COMPLETED") showToast("Family Deals search finished.");
    } catch (error) {
      renderFamilySearchState("QUEUED", { status: "QUEUED" }, []);
      if (familyDealsState.pollCount < 240) {
        familyDealsState.pollCount += 1;
        familyDealsState.pollTimer = window.setTimeout(() => pollFamilySearch(searchId), 7000);
      } else {
        showToast(error.message || "Family Deals status could not be read.");
      }
    }
  }

  async function runFamilyDealsSearch() {
    const form = byId("deal-search-form");
    if (!form.reportValidity()) return;
    if (!movieApi.production) { showDealPreview(); return; }
    const criteria = dealCriteria();
    try {
      const response = await movieApiFetch("/api/searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module: "family-deals", criteria })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Family Deals search could not be queued");
      familyDealsState.searchId = data.id;
      familyDealsState.pollCount = 0;
      renderFamilySearchState(data.status || "QUEUED", data, []);
      await pollFamilySearch(data.id);
    } catch (error) {
      renderFamilySearchState("FAILED", { status: "FAILED", last_outcome: "ERROR" }, []);
      showToast(error.message || "Family Deals search could not start.");
    }
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
  let movieGMMode = "everyone";
  const movieGMState = { viewers: [], learning: null };

  function listValue(id) {
    return byId(id).value.split(",").map((item) => item.trim()).filter(Boolean).slice(0, 20);
  }
  function renderMovieGMLearning(data) {
    movieGMState.learning = data || null;
    const target = byId("gm-learning-summary");
    if (!target) return;
    const count = Number(data?.evidence_count || 0);
    if (!count) {
      target.textContent = "No explicit feedback yet. Rate a movie after a recommendation and Movie GM will learn from it.";
      return;
    }
    const liked = (data.preferred_genres || []).slice(0, 4).join(", ");
    const disliked = (data.disliked_genres || []).slice(0, 4).join(", ");
    target.innerHTML = `Learning from <strong>${count}</strong> explicit ratings.${liked ? ` Likes are trending toward <strong>${escapeHtml(liked)}</strong>.` : ""}${disliked ? ` Avoidance signals include <strong>${escapeHtml(disliked)}</strong>.` : ""}`;
  }

  function renderMovieGMViewers() {
    const target = byId("gm-viewer-list");
    if (!target) return;
    if (!movieGMState.viewers.length) {
      target.innerHTML = '<p class="gm-viewer-empty">No individual profiles yet. Movie GM will use learned household feedback when available.</p>';
      return;
    }
    target.innerHTML = movieGMState.viewers.map((viewer) => `<article class="gm-viewer">
      <div><strong>${escapeHtml(viewer.display_name)}</strong><span>Weight ${Number(viewer.weight).toFixed(1)}${viewer.preferred_genres?.length ? " · Likes " + escapeHtml(viewer.preferred_genres.slice(0,3).join(", ")) : ""}</span></div>
      <div><button type="button" data-edit-viewer="${escapeHtml(viewer.viewer_id)}">Edit</button><button type="button" data-delete-viewer="${escapeHtml(viewer.viewer_id)}">Delete</button></div>
    </article>`).join("");
  }

  function fillMovieGMViewer(viewer) {
    byId("gm-viewer-name").value = viewer.display_name || "";
    byId("gm-viewer-name").dataset.viewerId = viewer.viewer_id || "";
    byId("gm-viewer-weight").value = viewer.weight ?? 1;
    byId("gm-viewer-preferred-genres").value = (viewer.preferred_genres || []).join(", ");
    byId("gm-viewer-disliked-genres").value = (viewer.disliked_genres || []).join(", ");
    byId("gm-viewer-preferred-keywords").value = (viewer.preferred_keywords || []).join(", ");
    byId("gm-viewer-disliked-keywords").value = (viewer.disliked_keywords || []).join(", ");
    byId("gm-viewer-runtime-min").value = viewer.preferred_runtime_min ?? "";
    byId("gm-viewer-runtime-max").value = viewer.preferred_runtime_max ?? "";
  }

  async function hydrateMovieGMSettings() {
    try {
      const [viewerResponse, learningResponse] = await Promise.all([
        movieApiFetch("/api/movies/viewers"),
        movieApiFetch("/api/movies/feedback")
      ]);
      if (viewerResponse.ok) {
        const data = await viewerResponse.json();
        movieGMState.viewers = Array.isArray(data.viewers) ? data.viewers : [];
        renderMovieGMViewers();
      }
      if (learningResponse.ok) renderMovieGMLearning(await learningResponse.json());
    } catch (_error) {
      renderMovieGMViewers();
    }
  }

  async function saveMovieGMViewer(event) {
    event.preventDefault();
    const name = byId("gm-viewer-name");
    const displayName = name.value.trim();
    if (!displayName) { name.focus(); return; }
    const viewerId = name.dataset.viewerId || displayName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || `viewer-${Date.now()}`;
    const payload = {
      viewer_id: viewerId,
      display_name: displayName,
      weight: Number(byId("gm-viewer-weight").value || 1),
      preferred_genres: listValue("gm-viewer-preferred-genres"),
      disliked_genres: listValue("gm-viewer-disliked-genres"),
      preferred_keywords: listValue("gm-viewer-preferred-keywords"),
      disliked_keywords: listValue("gm-viewer-disliked-keywords"),
      preferred_runtime_min: byId("gm-viewer-runtime-min").value || null,
      preferred_runtime_max: byId("gm-viewer-runtime-max").value || null
    };
    try {
      const response = await movieApiFetch("/api/movies/viewers", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not save household profile");
      await hydrateMovieGMSettings();
      event.target.reset();
      name.dataset.viewerId = "";
      byId("gm-viewer-weight").value = "1";
      showToast("Household profile saved. Movie GM will use it next time.");
    } catch (error) { showToast(error.message || "Household profile could not be saved."); }
  }

  async function deleteMovieGMViewer(viewerId) {
    try {
      const response = await movieApiFetch(`/api/movies/viewers/${encodeURIComponent(viewerId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not delete household profile");
      await hydrateMovieGMSettings();
      showToast("Household profile removed.");
    } catch (error) { showToast(error.message || "Household profile could not be removed."); }
  }

  function formatRuntime(minutes) {
    if (!Number.isFinite(minutes)) return "Runtime unknown";
    const hours = Math.floor(minutes / 60); const mins = minutes % 60;
    return hours ? (mins ? `${hours}h ${mins}m` : `${hours}h`) : `${mins}m`;
  }
  function renderMovieGM(data) {
    const panel = byId("movie-gm-results");
    const unavailable = (data.providers_unavailable || []).map((item) => `<div class="gm-source-warning"><strong>${escapeHtml(item.provider)}</strong><span>Unavailable: ${escapeHtml(item.reason)}</span></div>`).join("");
    const cards = (data.recommendations || []).map((item) => {
      const providers = (item.offers || []).map((offer) => `<a href="${escapeHtml(offer.watch_url || "#")}" target="_blank" rel="noopener noreferrer">${escapeHtml(offer.provider)}</a>`).join(", ") || "No accessible offer";
      const why = (item.why || []).slice(0, 4).map((reason) => `<li>${escapeHtml(reason)}</li>`).join("");
      const ratings = item.ratings || {};
      const ratingBadges = [
        Number.isFinite(ratings.imdb) ? "IMDb " + Number(ratings.imdb).toFixed(1) + (ratings.imdb_votes ? " · " + Number(ratings.imdb_votes).toLocaleString() + " votes" : "") : "",
        Number.isFinite(ratings.rotten_tomatoes_critics) ? "RT Critics " + Number(ratings.rotten_tomatoes_critics).toFixed(0) + "%" : "",
        Number.isFinite(ratings.rotten_tomatoes_audience) ? "RT Audience " + Number(ratings.rotten_tomatoes_audience).toFixed(0) + "%" : "",
        Number.isFinite(ratings.metacritic) ? "Metacritic " + Number(ratings.metacritic).toFixed(0) : "",
      ].filter(Boolean).map((rating) => `<span>${escapeHtml(rating)}</span>`).join("");
      return `<article class="gm-card"><header><div><h3>${escapeHtml(item.title)}</h3><span>${escapeHtml(item.year || "Year unknown")} · ${escapeHtml(formatRuntime(item.runtime_minutes))} · ${escapeHtml(item.age_rating || "Rating unknown")}</span></div><strong class="gm-score">${Number(item.combined_score).toFixed(1)}</strong></header><div class="gm-meta"><span>Quality ${Number(item.quality_score).toFixed(1)}</span><span>Household ${Number(item.household_score).toFixed(1)}</span><span>Availability ${escapeHtml(item.availability_confidence)}</span></div>${ratingBadges ? `<div class="gm-ratings">${ratingBadges}</div>` : ""}<p class="gm-providers"><strong>Available via:</strong> ${providers}</p><details><summary>Why this result?</summary><ul>${why || "<li>No additional explanation available.</li>"}</ul></details><div class="gm-feedback"><span>How did this sound?</span><button type="button" data-movie-feedback="loved" data-title="${escapeHtml(item.title)}" data-genres="${escapeHtml((item.genres || []).join("|"))}">Loved it</button><button type="button" data-movie-feedback="liked" data-title="${escapeHtml(item.title)}" data-genres="${escapeHtml((item.genres || []).join("|"))}">Liked it</button><button type="button" data-movie-feedback="disliked" data-title="${escapeHtml(item.title)}" data-genres="${escapeHtml((item.genres || []).join("|"))}">Not for us</button></div></article>`;
    }).join("");
    const upcoming = (data.upcoming || []).map((item) => `<article class="gm-upcoming"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.year || "Year unknown")} · ${escapeHtml(formatRuntime(item.runtime_minutes))} · ${escapeHtml(item.age_rating || "Rating unknown")}</span><small>${escapeHtml((item.why || [])[0] || "Confirmed upcoming offer")}</small></article>`).join("");
    panel.hidden = false;
    panel.innerHTML = `<div class="gm-summary"><strong>${data.recommendations?.length || 0} recommendations</strong><span>${data.total_candidates || 0} candidates checked</span><span>Sources checked: ${escapeHtml((data.providers_checked || []).join(", ") || "none")}</span></div>${unavailable}${cards ? `<div class="gm-card-grid">${cards}</div>` : `<div class="gm-empty"><strong>No qualifying movies were returned.</strong><span>This is not treated as a provider failure. Check the source status above.</span></div>`}${upcoming ? `<div class="gm-upcoming-section"><p class="eyebrow">NEXT 30 DAYS</p><h3>Coming soon</h3><div class="gm-upcoming-list">${upcoming}</div></div>` : ""}`;
  }
  async function runMovieGM() {
    const status = byId("movie-gm-status"); const panel = byId("movie-gm-results");
    const query = byId("movie-gm-query").value.trim();
    status.textContent = movieGMMode === "kids" ? "Checking streaming offers and applying the kids safety gate..." : "Finding something good for you...";
    panel.hidden = true;
    const params = new URLSearchParams({ mode: movieGMMode }); if (query) params.set("query", query);
    try {
      const response = await movieApiFetch(`/api/movies/search?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Movie search failed");
      renderMovieGM(data);
      status.textContent = data.providers_unavailable?.length ? "Search completed with one or more unavailable sources. Results remain clearly marked." : "Search complete. Availability and confidence are shown on each result.";
    } catch (error) {
      panel.hidden = false;
      panel.innerHTML = `<div class="gm-empty"><strong>Movie search unavailable</strong><span>${escapeHtml(error.message || "The source could not be checked.")}</span></div>`;
      status.textContent = "The search could not be completed.";
    }
  }
  document.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-view]"); if (viewButton) selectView(viewButton.dataset.view);
    if (event.target.closest("[data-mobile-menu]")) document.body.classList.toggle("menu-open"); if (event.target.closest("[data-focus-first]")) byId("movie-title").focus();
    if (event.target.closest("[data-select-all]")) { const boxes = all('input[name="theaters"]'); const select = boxes.some((box) => !box.checked); boxes.forEach((box) => { box.checked = select; }); updateSummary(); }
    const gmMode = event.target.closest("[data-gm-mode]"); if (gmMode) { movieGMMode = gmMode.dataset.gmMode; all("[data-gm-mode]").forEach((button) => button.classList.toggle("is-active", button === gmMode)); }
    if (event.target.closest("[data-save-watch]")) createDraft(); if (event.target.closest("[data-save-deal-watch]")) createDraft("family-deals"); if (event.target.closest("[data-focus-deal]")) byId("deal-location").focus();
    if (event.target.closest("[data-preview-action]")) showToast("Provider request skipped — AMC block protection is active."); if (event.target.closest("[data-location]")) showToast("Location access is not requested in this offline preview."); if (event.target.closest("[data-help]")) showToast("Configure a search, search once, then save the same criteria as a Watch.");
    if (event.target.closest("[data-deal-location]")) {
      if (!navigator.geolocation) { showToast("Location is unavailable in this browser. Enter an address or ZIP instead."); return; }
      navigator.geolocation.getCurrentPosition(({ coords }) => { byId("deal-location").value = `${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)}`; updateDealSummary(); }, () => showToast("Location access was unavailable. Enter an address or ZIP instead."), { timeout: 10000, maximumAge: 300000 });
    }
    const editViewer = event.target.closest("[data-edit-viewer]");
    if (editViewer) {
      const viewer = movieGMState.viewers.find((item) => item.viewer_id === editViewer.dataset.editViewer);
      if (viewer) fillMovieGMViewer(viewer);
    }
    const deleteViewer = event.target.closest("[data-delete-viewer]");
    if (deleteViewer) deleteMovieGMViewer(deleteViewer.dataset.deleteViewer);

    const feedback = event.target.closest("[data-movie-feedback]");
    if (feedback) {
      const payload = { title: feedback.dataset.title, rating: feedback.dataset.movieFeedback, genres: (feedback.dataset.genres || "").split("|").filter(Boolean) };
      movieApiFetch("/api/movies/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        .then((response) => { if (!response.ok) throw new Error("Could not save feedback"); return response.json(); })
        .then(() => showToast("Got it. Movie GM will use that feedback next time."))
        .catch(() => showToast("Feedback could not be saved in this preview."));
    }
    const action = event.target.closest("[data-watch-action]"); if (action) changeWatchStatus(action.dataset.watchId, action.dataset.watchAction);
  });
  byId("movie-gm-form").addEventListener("submit", (event) => { event.preventDefault(); runMovieGM(); });
  byId("gm-viewer-form").addEventListener("submit", saveMovieGMViewer);
  byId("movie-search-form").addEventListener("input", updateSummary); byId("movie-search-form").addEventListener("change", updateSummary); byId("movie-search-form").addEventListener("submit", (event) => { event.preventDefault(); updateSummary(); showOfflineResult(); });
  byId("deal-search-form").addEventListener("input", updateDealSummary); byId("deal-search-form").addEventListener("change", updateDealSummary); byId("deal-search-form").addEventListener("submit", (event) => { event.preventDefault(); updateDealSummary(); runFamilyDealsSearch(); });
  updateSummary(); updateDealSummary(); renderWatches(); renderResults(); hydrate(); movieApi.bootstrapPromise = bootstrapMovieApi(); movieApi.bootstrapPromise.then(() => { setFamilyBanner(movieApi.production); hydrateMovieGMSettings(); }); const initialView = new URLSearchParams(window.location.search).get("view"); if (initialView) selectView(initialView);
})();
