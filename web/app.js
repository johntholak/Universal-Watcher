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
    watchList.innerHTML = state.watches.map((watch) => `<div class="watch-item"><div><strong>${escapeHtml(watch.name)}</strong><small>${moduleLabels[watch.module]} · local draft</small></div><span class="watch-status">Draft</span></div>`).join("");
  }

  function renderActivity() {
    if (!state.activities.length) {
      activityList.innerHTML = '<li class="activity-empty">Activity will appear when a watch runs.</li>';
      return;
    }
    activityList.innerHTML = state.activities.map((activity) => `<li class="activity-item"><div><strong>${escapeHtml(activity.message)}</strong><small>${escapeHtml(activity.detail)}</small></div></li>`).join("");
  }

  function addDraft(name, module) {
    state.watches.unshift({ name, module });
    state.activities.unshift({
      message: `Created ${moduleLabels[module]} draft`,
      detail: "Local shell preview · not monitoring yet",
    });
    renderWatches();
    renderActivity();
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
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = nameInput.value.trim();
    if (!name) return;
    addDraft(name, moduleInput.value);
    closeDialog();
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDialog();
  });

  renderWatches();
  renderActivity();
})();
