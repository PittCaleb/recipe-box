(function () {
  const form = document.getElementById("cookbook-form");
  if (!form) return;

  const submitBtn = document.getElementById("cookbook-submit");
  const spinner = document.getElementById("cookbook-spinner");
  const status = document.getElementById("cookbook-status");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    status.hidden = true;
    status.classList.remove("share-status--ok", "share-status--error");
    submitBtn.disabled = true;
    spinner.hidden = false;

    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("The server couldn't build the cookbook.");
        }
        const disposition = res.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : "cookbook.pdf";
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        status.hidden = false;
        status.textContent = "Cookbook ready — download started.";
        status.classList.add("share-status--ok");
      })
      .catch((err) => {
        status.hidden = false;
        status.textContent = err.message;
        status.classList.add("share-status--error");
      })
      .finally(() => {
        submitBtn.disabled = false;
        spinner.hidden = true;
      });
  });
})();
