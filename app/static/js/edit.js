(function () {
  const rowsContainer = document.getElementById("ingredient-rows");
  const addRowBtn = document.getElementById("add-ingredient-row");
  const form = document.getElementById("edit-form");
  const quillEl = document.getElementById("quill-editor");
  const instructionsInput = document.getElementById("instructions_html");
  const parseUrl = rowsContainer ? rowsContainer.dataset.parseUrl : null;

  function rowTemplate() {
    const row = document.createElement("div");
    row.className = "ingredient-row";
    row.dataset.kind = "item";
    row.innerHTML = `
      <div class="ingredient-row-controls">
        <button type="button" class="icon-button row-btn" data-move="up" title="Move up" aria-label="Move up">&uarr;</button>
        <button type="button" class="icon-button row-btn" data-move="down" title="Move down" aria-label="Move down">&darr;</button>
      </div>
      <div class="ingredient-text-wrap">
        <input type="hidden" name="ingredient_kind" value="item">
        <input type="text" name="ingredient_text" value="" class="ingredient-text" placeholder="e.g. 2 cups flour, or a heading">
        <span class="split-chip" hidden></span>
      </div>
      <input type="hidden" name="ingredient_no_scale" value="0">
      <input type="hidden" name="ingredient_is_split" value="0">
      <input type="hidden" name="ingredient_quantity" value="">
      <input type="hidden" name="ingredient_quantity_max" value="">
      <input type="hidden" name="ingredient_unit" value="">
      <input type="hidden" name="ingredient_item" value="">
      <div class="ingredient-row-controls">
        <button type="button" class="chip-toggle-btn" data-toggle="heading">Heading</button>
        <button type="button" class="chip-toggle-btn" data-toggle="no_scale">Scale: on</button>
        <button type="button" class="chip-toggle-btn" data-action="split">Split</button>
        <button type="button" class="icon-button row-btn row-btn--danger" data-remove title="Delete row" aria-label="Delete row">&times;</button>
      </div>
    `;
    return row;
  }

  if (addRowBtn && rowsContainer) {
    addRowBtn.addEventListener("click", () => {
      const row = rowTemplate();
      rowsContainer.appendChild(row);
      row.querySelector(".ingredient-text").focus();
    });
  }

  // --- Split modal ---
  const splitModal = document.getElementById("split-modal");
  const splitRawText = document.getElementById("split-modal-raw-text");
  const splitQuantity = document.getElementById("split-quantity");
  const splitQuantityMax = document.getElementById("split-quantity-max");
  const splitUnit = document.getElementById("split-unit");
  const splitItem = document.getElementById("split-item");
  const splitSaveBtn = document.getElementById("split-save");
  const splitClearBtn = document.getElementById("split-clear");
  let activeRow = null;

  function rowField(row, name) {
    return row.querySelector(`input[name=${name}]`);
  }

  function updateChip(row) {
    const isSplit = rowField(row, "ingredient_is_split").value === "1";
    const chip = row.querySelector(".split-chip");
    if (!isSplit) {
      chip.hidden = true;
      return;
    }
    const qty = rowField(row, "ingredient_quantity").value;
    const qtyMax = rowField(row, "ingredient_quantity_max").value;
    const unit = rowField(row, "ingredient_unit").value || "count";
    const item = rowField(row, "ingredient_item").value;
    chip.textContent = `${qty}${qtyMax ? "–" + qtyMax : ""} · ${unit} · ${item}`;
    chip.hidden = false;
  }

  function openSplitModal(row) {
    activeRow = row;
    const text = row.querySelector(".ingredient-text").value;
    splitRawText.textContent = `Raw text: "${text}"`;

    const isSplit = rowField(row, "ingredient_is_split").value === "1";
    if (isSplit) {
      splitQuantity.value = rowField(row, "ingredient_quantity").value;
      splitQuantityMax.value = rowField(row, "ingredient_quantity_max").value;
      splitUnit.value = rowField(row, "ingredient_unit").value;
      splitItem.value = rowField(row, "ingredient_item").value;
      splitModal.hidden = false;
    } else if (parseUrl) {
      fetch(`${parseUrl}?text=${encodeURIComponent(text)}`)
        .then((res) => res.json())
        .then((data) => {
          splitQuantity.value = data.quantity != null ? data.quantity : "";
          splitQuantityMax.value = data.quantity_max != null ? data.quantity_max : "";
          splitUnit.value = data.unit || "";
          splitItem.value = data.item || "";
          splitModal.hidden = false;
        })
        .catch(() => {
          splitQuantity.value = "";
          splitQuantityMax.value = "";
          splitUnit.value = "";
          splitItem.value = "";
          splitModal.hidden = false;
        });
    } else {
      splitModal.hidden = false;
    }
  }

  if (splitSaveBtn) {
    splitSaveBtn.addEventListener("click", () => {
      if (!activeRow) return;
      const qty = splitQuantity.value.trim();
      if (!qty) {
        window.alert("Enter a quantity, or use Clear split for items with no amount.");
        return;
      }
      rowField(activeRow, "ingredient_is_split").value = "1";
      rowField(activeRow, "ingredient_quantity").value = qty;
      rowField(activeRow, "ingredient_quantity_max").value = splitQuantityMax.value.trim();
      rowField(activeRow, "ingredient_unit").value = splitUnit.value;
      rowField(activeRow, "ingredient_item").value = splitItem.value.trim();
      updateChip(activeRow);
      splitModal.hidden = true;
    });
  }

  if (splitClearBtn) {
    splitClearBtn.addEventListener("click", () => {
      if (!activeRow) return;
      rowField(activeRow, "ingredient_is_split").value = "0";
      rowField(activeRow, "ingredient_quantity").value = "";
      rowField(activeRow, "ingredient_quantity_max").value = "";
      rowField(activeRow, "ingredient_unit").value = "";
      rowField(activeRow, "ingredient_item").value = "";
      updateChip(activeRow);
      splitModal.hidden = true;
    });
  }

  if (rowsContainer) {
    rowsContainer.addEventListener("click", (e) => {
      const row = e.target.closest(".ingredient-row");
      if (!row) return;

      if (e.target.closest("[data-remove]")) {
        row.remove();
        return;
      }

      if (e.target.closest("[data-move='up']")) {
        const prev = row.previousElementSibling;
        if (prev) rowsContainer.insertBefore(row, prev);
        return;
      }

      if (e.target.closest("[data-move='down']")) {
        const next = row.nextElementSibling;
        if (next) rowsContainer.insertBefore(next, row);
        return;
      }

      if (e.target.closest("[data-action='split']")) {
        openSplitModal(row);
        return;
      }

      const toggleBtn = e.target.closest("[data-toggle]");
      if (toggleBtn) {
        const toggleType = toggleBtn.dataset.toggle;
        if (toggleType === "heading") {
          const kindInput = row.querySelector("input[name=ingredient_kind]");
          const isHeading = kindInput.value === "heading";
          kindInput.value = isHeading ? "item" : "heading";
          row.dataset.kind = kindInput.value;
          toggleBtn.textContent = isHeading ? "Heading" : "Item";
        } else if (toggleType === "no_scale") {
          const noScaleInput = row.querySelector("input[name=ingredient_no_scale]");
          const isNoScale = noScaleInput.value === "1";
          noScaleInput.value = isNoScale ? "0" : "1";
          toggleBtn.textContent = isNoScale ? "Scale: on" : "Don't scale";
        }
      }
    });
  }

  let quill = null;
  if (quillEl && window.Quill) {
    quill = new Quill("#quill-editor", {
      theme: "snow",
      modules: {
        toolbar: [["bold", "italic"], [{ list: "bullet" }, { list: "ordered" }], ["clean"]],
      },
    });
  }

  if (form) {
    form.addEventListener("submit", () => {
      if (quill && instructionsInput) {
        instructionsInput.value = quill.root.innerHTML;
      }
    });
  }
})();
