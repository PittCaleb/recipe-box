(function () {
  const form = document.getElementById("search-form");
  const results = document.getElementById("results");
  if (!form || !results) return;

  const url = form.dataset.searchUrl;
  let debounceTimer = null;
  let activeController = null;

  function refresh() {
    const params = new URLSearchParams(new FormData(form));
    if (activeController) activeController.abort();
    activeController = new AbortController();

    fetch(`${url}?${params.toString()}`, { signal: activeController.signal })
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

    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, "", newUrl);
  }

  function debouncedRefresh() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(refresh, 250);
  }

  form.addEventListener("submit", (e) => e.preventDefault());
  form.querySelectorAll("select, input[type=checkbox]").forEach((el) => {
    el.addEventListener("change", refresh);
  });
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", debouncedRefresh);
  }

  // --- Display / group-by pill toggles ---
  const sortSelect = document.getElementById("sort-select");
  const groupToggle = document.getElementById("group-toggle");
  const hiddenInputs = {
    display: document.getElementById("display-input"),
    group: document.getElementById("group-input"),
  };

  function setPref(kind, value, { persist = true, skipRefresh = false } = {}) {
    const input = hiddenInputs[kind];
    if (!input || input.value === value) {
      if (!skipRefresh && input && input.value !== value) refresh();
      return;
    }
    input.value = value;
    const group = form.querySelector(`[data-pill-group="${kind}"]`);
    if (group) {
      group.querySelectorAll(".pill-btn").forEach((btn) => {
        const active = btn.dataset.value === value;
        btn.classList.toggle("is-active", active);
        btn.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }
    if (persist) {
      try {
        localStorage.setItem(`recipes.${kind}`, value);
      } catch (e) {
        /* ignore (private browsing, etc.) */
      }
    }
    if (!skipRefresh) refresh();
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
      const kind = group.dataset.pillGroup;
      setPref(kind, btn.dataset.value);
    });
  });

  if (sortSelect) {
    sortSelect.addEventListener("change", updateGroupAvailability);
  }
  updateGroupAvailability();

  // On a fresh page load with no explicit display/group in the URL, fall
  // back to the viewer's last-used preference from localStorage.
  (function restorePreference() {
    const urlParams = new URLSearchParams(window.location.search);
    let changed = false;
    ["display", "group"].forEach((kind) => {
      if (urlParams.has(kind)) return;
      try {
        const stored = localStorage.getItem(`recipes.${kind}`);
        if (stored && hiddenInputs[kind] && hiddenInputs[kind].value !== stored) {
          setPref(kind, stored, { persist: false, skipRefresh: true });
          changed = true;
        }
      } catch (e) {
        /* ignore */
      }
    });
    if (changed) refresh();
  })();
})();
