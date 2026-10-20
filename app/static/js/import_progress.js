(function () {
  const el = document.getElementById("import-progress");
  if (!el) return;

  const statusUrl = el.dataset.statusUrl;
  const statusText = document.getElementById("import-status-text");
  const bar = document.getElementById("import-progress-bar");

  function poll() {
    fetch(statusUrl)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ready" || data.status === "error") {
          window.location.reload();
          return;
        }
        bar.max = data.total_pages || 1;
        bar.value = data.processed_pages;
        if (data.status === "rendering") {
          statusText.textContent = "Rendering pages…";
        } else {
          statusText.textContent = `Transcribing page ${data.processed_pages} of ${data.total_pages || "?"}…`;
        }
        setTimeout(poll, 2000);
      })
      .catch(() => setTimeout(poll, 4000));
  }

  setTimeout(poll, 1500);
})();
