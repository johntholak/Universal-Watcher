(() => {
  const dialog = document.querySelector("#create-dialog");
  const form = document.querySelector("#create-form");
  const nameInput = document.querySelector("#watch-name");
  const moduleInput = document.querySelector("#watch-module");
  const watchList = document.querySelector("#watch-list");
  const activityList = document.querySelector("#activity-list");
  const watchCount = document.querySelector("#watch-count");
  const pageTitle = document.querySelector("#page-title");
  const heroTitle = document.querySelector("#hero-title");

  const moduleLabels = {
    movies: "Movies",
    tickets: "Tickets",
    "family-deals": "Family Deals",
  };
  const state = { watches: [], activities: [] };

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
  hydrateWatches();
})();
