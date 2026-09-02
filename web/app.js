(() => {
  const dialog = document.querySelector("#create-dialog");
  const form = document.querySelector("#create-form");
  const nameInput = document.querySelector("#watch-name");
  const moduleInput = document.querySelector("#watch-module");
  const watchList = document.querySelector("#watch-list");
  const activityList = document.querySelector("#activity-list");
  const watchCount = document.querySelector("#watch-count");
  const resultList = document.querySelector("#result-list");
  const resultCount = document.querySelector("#result-count");
  const pageTitle = document.querySelector("#page-title");
  const heroTitle = document.querySelector("#hero-title");

  const moduleLabels = {
    movies: "Movies",
    tickets: "Tickets",
    "family-deals": "Family Deals",
  };
  const state = { watches: [], activities: [], results: [] };

  function openDialog(module = "movies") {
    moduleInput.value = module;
    dialog.showModal();
    window.requestAnimationFrame(() => nameInput.focus());
  }

  function closeDialog() {
    dialog.close();
    form.reset();
  }

  function renderWatches() {
    watchCount.textContent = String(state.watches.length);
    if (!state.watches.length) {
      watchList.className = "empty-state";
      watchList.innerHTML = `<span class="empty-icon" aria-hidden="true">⌁</span><h3>No watches yet</h3><p>Your Movies, Tickets, and Family Deals watches will appear here.</p><button class="button button-secondary" type="button" data-open-create>Start your first watch</button>`;
      return;
    }
    watchList.className = "watch-list";
    watchList.innerHTML = state.watches.map((watch) => {
      const status = watch.status || "draft";
      const controls = watchControls(watch);
      return `<div class="watch-item"><div><strong>${escapeHtml(watch.query || watch.name)}</strong><small>${moduleLabels[watch.module]} · local preview</small></div><div class="watch-item-actions"><span class="watch-status watch-status-${status}">${statusLabel(status)}</span>${controls}</div></div>`;
    }).join("");
  }

  function statusLabel(status) {
    return ({ draft: "Draft", active: "Active", paused: "Paused", completed: "Stopped", error: "Error" })[status] || "Draft";
  }

  function watchControls(watch) {
    const status = watch.status || "draft";
    const id = escapeHtml(watch.watch_id || "");
    if (!id) return "";
    if (status === "draft") return `<button class="watch-action" type="button" data-watch-action="active" data-watch-id="${id}">Start</button>`;
    if (status === "active") return `<button class="watch-action" type="button" data-watch-action="paused" data-watch-id="${id}">Pause</button><button class="watch-action" type="button" data-watch-action="completed" data-watch-id="${id}">Stop</button>`;
    if (status === "paused") return `<button class="watch-action" type="button" data-watch-action="active" data-watch-id="${id}">Resume</button><button class="watch-action" type="button" data-watch-action="completed" data-watch-id="${id}">Stop</button>`;
    return "";
  }

  function renderActivity() {
    if (!state.activities.length) {
      activityList.innerHTML = '<li class="activity-empty">Activity will appear when a watch runs.</li>';
      return;
    }
    activityList.innerHTML = state.activities.map((activity) => `<li class="activity-item"><div><strong>${escapeHtml(activity.message)}</strong><small>${escapeHtml(activity.detail)}</small></div></li>`).join("");
  }

  function renderResults() {
    resultCount.textContent = String(state.results.length);
    if (!state.results.length) {
      resultList.className = "empty-state";
      resultList.innerHTML = '<span class="empty-icon" aria-hidden="true">✓</span><h3>No verified matches yet</h3><p>Results and the evidence behind them will appear here as module adapters come online.</p>';
      return;
    }
    resultList.className = "result-list";
    resultList.innerHTML = state.results.map((result) => {
      const outcome = ["match", "no_match", "unavailable", "error"].includes(result.outcome) ? result.outcome : "unavailable";
      const evidence = Array.isArray(result.evidence) ? result.evidence : [];
      const evidenceMarkup = evidence.length
        ? evidence.map((item) => {
            const summary = escapeHtml(item.summary || "Evidence captured");
            const url = safeHttpUrl(item.url);
            return `<span>${summary}${url ? ` · <a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Source</a>` : ""}</span>`;
          }).join("<br>")
        : "No evidence attached";
      const destination = safeHttpUrl(result.destination_url);
      const moduleName = moduleLabels[result.module] || result.module || "Unknown module";
      const coverage = result.coverage || "unknown";
      const verification = result.verification || "unverified";
      return `<article class="result-item"><div><strong>${escapeHtml(result.title || "Untitled result")}</strong><small>${escapeHtml(moduleName)} · ${escapeHtml(verification)} · ${escapeHtml(coverage)} coverage</small><div class="result-evidence">${evidenceMarkup}${result.reason ? `<br>${escapeHtml(result.reason)}` : ""}${destination ? ` · <a href="${escapeHtml(destination)}" target="_blank" rel="noreferrer">Open destination</a>` : ""}</div></div><div class="result-item-meta"><span class="result-status result-status-${outcome}">${outcomeLabel(outcome)}</span></div></article>`;
    }).join("");
  }

  function outcomeLabel(outcome) {
    return ({ match: "Match", no_match: "No match", unavailable: "Unavailable", error: "Error" })[outcome] || "Unavailable";
  }

  function safeHttpUrl(value) {
    if (!value) return "";
    try {
      const url = new URL(value, window.location.href);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch (_error) {
      return "";
    }
  }

  function addDraft(watch, detail) {
    state.watches.unshift(watch);
    state.activities.unshift({
      message: `Created ${moduleLabels[watch.module]} draft`,
      detail,
    });
    renderWatches();
    renderActivity();
  }

  async function createDraft(name, module) {
    const payload = { module, query: name, criteria: {} };
    try {
      const response = await fetch("/api/watches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Preview API unavailable");
      addDraft(await response.json(), "Local preview API · not monitoring yet");
    } catch (_error) {
      addDraft({
        watch_id: `browser-draft-${Date.now()}`,
        module,
        query: name,
        status: "draft",
      }, "Browser-only preview · not monitoring yet");
    }
  }

  async function changeWatchStatus(watchId, status) {
    const watch = state.watches.find((item) => item.watch_id === watchId);
    if (!watch) return;
    try {
      const response = await fetch(`/api/watches/${encodeURIComponent(watchId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error("Preview API unavailable");
      const updated = await response.json();
      Object.assign(watch, updated);
    } catch (_error) {
      // Keep the static-only preview useful without claiming a live run.
      const allowed = {
        draft: ["active", "error"],
        active: ["paused", "completed", "error"],
        paused: ["active", "completed", "error"],
      };
      if (!(allowed[watch.status || "draft"] || []).includes(status)) return;
      watch.status = status;
    }
    state.activities.unshift({
      message: `${statusLabel(status)} ${moduleLabels[watch.module]} draft`,
      detail: "Local preview · not monitoring yet",
    });
    renderWatches();
    renderActivity();
  }

  async function hydrateWatches() {
    try {
      const response = await fetch("/api/watches", { cache: "no-store" });
      if (!response.ok) return;
      const watches = await response.json();
      if (!Array.isArray(watches)) return;
      state.watches = watches;
      renderWatches();
    } catch (_error) {
      // Opening the shell through a static file server is supported; drafts stay local.
    }
  }

  async function hydrateResults() {
    try {
      const response = await fetch("/api/results", { cache: "no-store" });
      if (!response.ok) return;
      const results = await response.json();
      if (!Array.isArray(results)) return;
      state.results = results;
      renderResults();
    } catch (_error) {
      // A static-only shell simply keeps the honest empty state.
    }
  }

  function selectView(view) {
    const label = moduleLabels[view] || "Overview";
    pageTitle.textContent = label;
    heroTitle.textContent = view === "overview" ? "Let Universal Watcher keep looking." : `Start a ${label} watch.`;
    document.querySelectorAll("[data-view]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.view === view);
    });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  }

  document.addEventListener("click", (event) => {
    const openButton = event.target.closest("[data-open-create]");
    if (openButton) openDialog(openButton.dataset.module || "movies");
    if (event.target.closest("[data-close-dialog]")) closeDialog();

    const viewButton = event.target.closest("[data-view]");
    if (viewButton) selectView(viewButton.dataset.view);

    const moduleCard = event.target.closest("button[data-module]");
    if (moduleCard) openDialog(moduleCard.dataset.module);

    const actionButton = event.target.closest("[data-watch-action]");
    if (actionButton) changeWatchStatus(actionButton.dataset.watchId, actionButton.dataset.watchAction);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = nameInput.value.trim();
    if (!name) return;
    await createDraft(name, moduleInput.value);
    closeDialog();
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog();
  });

  renderWatches();
  renderActivity();
  renderResults();
  hydrateWatches();
  hydrateResults();
})();
