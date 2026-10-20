(function () {
  document.querySelectorAll("[data-open-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = document.getElementById(btn.dataset.openModal);
      if (modal) modal.hidden = false;
    });
  });

  document.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", () => {
      const modal = el.closest(".modal");
      if (modal) modal.hidden = true;
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal").forEach((m) => (m.hidden = true));
    }
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (!window.confirm(form.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // --- Email / Text sharing ---
  document.querySelectorAll("form[data-share-form]").forEach((form) => {
    const status = form.querySelector(".share-status");
    const submitBtn = form.querySelector("button[type=submit]");

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      status.hidden = true;
      status.classList.remove("share-status--ok", "share-status--error");
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending…";

      fetch(form.dataset.shareUrl, { method: "POST", body: new FormData(form) })
        .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          status.hidden = false;
          status.textContent = data.message;
          status.classList.add(ok && data.success ? "share-status--ok" : "share-status--error");
          if (ok && data.success) {
            form.reset();
          }
        })
        .catch(() => {
          status.hidden = false;
          status.textContent = "Something went wrong sending this.";
          status.classList.add("share-status--error");
        })
        .finally(() => {
          submitBtn.disabled = false;
          submitBtn.textContent = "Send";
        });
    });
  });

  // --- Adjust (scaling) ---
  const adjustPanel = document.getElementById("adjust-panel");
  const adjustSlider = document.getElementById("adjust-slider");
  const adjustBanner = document.getElementById("adjust-banner");
  const adjustBannerValue = document.getElementById("adjust-banner-value");
  const adjustCurrentLabel = document.getElementById("adjust-current-label");
  const adjustReset = document.getElementById("adjust-reset");
  const variantsDataEl = document.getElementById("adjust-variants-data");

  if (adjustPanel && adjustSlider && variantsDataEl) {
    const variants = JSON.parse(variantsDataEl.textContent);
    const labels = Array.from(document.querySelectorAll(".adjust-slider-ticks span")).map((el) => el.textContent);
    const defaultIndex = parseInt(adjustPanel.dataset.defaultIndex, 10);
    const rows = document.querySelectorAll("#ingredient-list [data-ing-index]");

    function applyIndex(index) {
      const variant = variants[index];
      rows.forEach((row) => {
        const i = parseInt(row.dataset.ingIndex, 10);
        const textEl = row.querySelector(".ingredient-item-text") || row;
        textEl.textContent = variant[i];
      });
      adjustCurrentLabel.textContent = labels[index];
      if (index === defaultIndex) {
        adjustBanner.hidden = true;
      } else {
        adjustBanner.hidden = false;
        adjustBannerValue.textContent = labels[index];
      }
    }

    adjustSlider.addEventListener("input", () => {
      applyIndex(parseInt(adjustSlider.value, 10));
    });

    if (adjustReset) {
      adjustReset.addEventListener("click", () => {
        adjustSlider.value = defaultIndex;
        applyIndex(defaultIndex);
      });
    }
  }
})();
