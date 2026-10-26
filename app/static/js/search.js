(function () {
  const form = document.getElementById("search-form");
  const results = document.getElementById("results");
  if (!form || !results) return;

  const STATE_KEY = "recipes.browseQuery";

  function currentQuery() {
    return new URLSearchParams(new FormData(form)).toString();
  }

  function readState() {
    try {
      const stored = localStorage.getItem(STATE_KEY);
      if (stored !== null) return stored;
      // Older versions only remembered the view style; carry that over.
      const legacy = new URLSearchParams();
      ["display", "group"].forEach((kind) => {
        const value = localStorage.getItem(`recipes.${kind}`);
        if (value) legacy.set(kind, value);
      });
      return legacy.toString() || null;
    } catch (e) {
      return null;
    }
  }

  function saveState(query) {
    try {
      localStorage.setItem(STATE_KEY, query);
    } catch (e) {
      /* private browsing etc. -- filters just won't be remembered */
    }
  }

  // Arriving at a bare "/" (header link, after editing, a new tab) restores
  // the last search and filters. A full reload lets the server render that
  // state exactly; replace() keeps it out of the Back history.
  if (!window.location.search) {
    const stored = readState();
    if (stored) {
      const merged = new URLSearchParams(currentQuery());
      new URLSearchParams(stored).forEach((value, key) => merged.set(key, value));
      if (merged.toString() !== currentQuery()) {
        window.location.replace(`${window.location.pathname}?${stored}`);
        return;
      }
    }
  }

  const url = form.dataset.searchUrl;
  const clearBtn = document.getElementById("clear-filters");
  const sortSelect = document.getElementById("sort-select");
  const groupToggle = document.getElementById("group-toggle");
  const searchInput = document.getElementById("search-input");
  let debounceTimer = null;
  let activeController = null;

  function filtersActive() {
    const data = new FormData(form);
    return Boolean(
      (data.get("q") || "").trim() ||
      data.get("category") ||
      (data.get("sort") && data.get("sort") !== "name") ||
      data.get("favorites") || data.get("needs_review") || data.get("needs_split"),
    );
  }

  function updateClearButton() {
    if (clearBtn) clearBtn.hidden = !filtersActive();
  }

  function refresh() {
    const query = currentQuery();
    if (activeController) activeController.abort();
    activeController = new AbortController();

    fetch(`${url}?${query}`, { signal: activeController.signal })
      .then((res) => res.text())
      .then((html) => {
        results.innerHTML = html;
        const countData = results.querySelector("[data-results-count]");
        const countSlot = document.getElementById("results-count");
        if (countData && countSlot) countSlot.textContent = countData.dataset.resultsCount;
      })
      .catch((err) => {
        if (err.name !== "AbortError") console.error(err);
      });

    window.history.replaceState(null, "", `${window.location.pathname}?${query}`);
    saveState(query);
    updateClearButton();
  }

  function debouncedRefresh() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(refresh, 250);
  }

  form.addEventListener("submit", (e) => e.preventDefault());
  form.querySelectorAll("select, input[type=checkbox]").forEach((el) => {
    el.addEventListener("change", refresh);
  });
  if (searchInput) searchInput.addEventListener("input", debouncedRefresh);

  // --- Display / group-by pill toggles ---
  const hiddenInputs = {
    display: document.getElementById("display-input"),
    group: document.getElementById("group-input"),
  };

  function setPref(kind, value) {
    const input = hiddenInputs[kind];
    if (!input || input.value === value) return;
    input.value = value;
    const group = form.querySelector(`[data-pill-group="${kind}"]`);
    if (group) {
      group.querySelectorAll(".pill-btn").forEach((btn) => {
        const active = btn.dataset.value === value;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }
    refresh();
  }

  function updateGroupAvailability() {
    const groupingUsable = !sortSelect || sortSelect.value === "name";
    if (groupToggle) {
      groupToggle.classList.toggle("pill-group--disabled", !groupingUsable);
      groupToggle.setAttribute("aria-disabled", groupingUsable ? "false" : "true");
    }
  }

  form.querySelectorAll(".pill-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const group = btn.closest("[data-pill-group]");
      if (group && group.classList.contains("pill-group--disabled")) return;
      setPref(group.dataset.pillGroup, btn.dataset.value);
    });
  });

  if (sortSelect) sortSelect.addEventListener("change", updateGroupAvailability);
  updateGroupAvailability();

  // --- Clear filters (keeps the Cards/Text and A–Z/Category view) ---
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
      const category = document.getElementById("category-select");
      if (category) category.value = "";
      if (sortSelect) sortSelect.value = "name";
      form.querySelectorAll("input[type=checkbox]").forEach((box) => {
        box.checked = false;
      });
      updateGroupAvailability();
      refresh();
      if (searchInput) searchInput.focus();
    });
  }

  // Remember whatever state this page was opened with (e.g. a shared link).
  saveState(currentQuery());
  updateClearButton();
})();
