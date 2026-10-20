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
})();
