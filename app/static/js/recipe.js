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

  // --- Copy recipe image to clipboard ---
  const toast = document.getElementById("toast");
  let toastTimer = null;
  function showToast(message, isError) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle("toast--error", Boolean(isError));
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.hidden = true;
    }, 3000);
  }

  const copyBtn = document.getElementById("copy-image-btn");
  // Browsers only allow writing images to the clipboard on https:// or
  // localhost; elsewhere (e.g. a phone on the LAN over http) the button
  // stays hidden and "Save image" is the way to go.
  if (copyBtn && window.isSecureContext && navigator.clipboard && window.ClipboardItem) {
    copyBtn.hidden = false;
    copyBtn.addEventListener("click", () => {
      copyBtn.disabled = true;
      copyBtn.classList.add("is-busy");
      // Safari requires ClipboardItem to be created synchronously inside the
      // click, so hand it a promise for the image rather than awaiting first.
      const blob = fetch(copyBtn.dataset.imageUrl).then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      });
      navigator.clipboard
        .write([new ClipboardItem({ "image/png": blob })])
        .then(() => showToast("Recipe image copied — paste it anywhere."))
        .catch((err) => {
          console.error(err);
          showToast("Couldn't copy the image. Try Save image instead.", true);
        })
        .finally(() => {
          copyBtn.disabled = false;
          copyBtn.classList.remove("is-busy");
        });
    });
  }

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
