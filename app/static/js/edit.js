(function () {
  const rowsContainer = document.getElementById("ingredient-rows");
  const rowTemplate = document.getElementById("ingredient-row-template");
  const form = document.getElementById("edit-form");
  const quillEl = document.getElementById("quill-editor");
  const instructionsInput = document.getElementById("instructions_html");

  function field(row, name) {
    return row.querySelector(`[name=${name}]`);
  }

  function setKind(row, kind) {
    row.dataset.kind = kind;
    field(row, "ingredient_kind").value = kind;
    row.querySelector("[data-toggle='heading']").setAttribute(
      "aria-label", kind === "heading" ? "Make it an ingredient" : "Make it a heading",
    );
  }

  function addRow(kind) {
    const row = rowTemplate.content.firstElementChild.cloneNode(true);
    setKind(row, kind);
    rowsContainer.appendChild(row);
    row.querySelector(kind === "heading" ? ".ing-heading" : ".ing-qty").focus();
  }

  const addItemBtn = document.getElementById("add-ingredient-row");
  const addHeadingBtn = document.getElementById("add-heading-row");
  if (rowsContainer && rowTemplate) {
    if (addItemBtn) addItemBtn.addEventListener("click", () => addRow("item"));
    if (addHeadingBtn) addHeadingBtn.addEventListener("click", () => addRow("heading"));

    // Enter in the last field of a row starts a new ingredient instead of
    // submitting the whole form.
    rowsContainer.addEventListener("keydown", (e) => {
      if (e.key !== "Enter" || e.target.tagName !== "INPUT") return;
      e.preventDefault();
      const row = e.target.closest(".ingredient-row");
      if (row && row === rowsContainer.lastElementChild) addRow("item");
    });

    // An emptied range field folds back into the "+ range" link.
    rowsContainer.addEventListener("focusout", (e) => {
      if (!e.target.matches("[name=ingredient_quantity_max]") || e.target.value.trim()) return;
      e.target.hidden = true;
      e.target.closest(".ing-range").querySelector("[data-range-add]").hidden = false;
    });

    // Editing a pre-filled guess counts as checking it.
    rowsContainer.addEventListener("input", (e) => {
      const row = e.target.closest(".ingredient-row.is-guess");
      if (row) row.classList.remove("is-guess");
    });

    rowsContainer.addEventListener("click", (e) => {
      const row = e.target.closest(".ingredient-row");
      if (!row) return;

      const rangeAdd = e.target.closest("[data-range-add]");
      if (rangeAdd) {
        const input = field(row, "ingredient_quantity_max");
        rangeAdd.hidden = true;
        input.hidden = false;
        input.focus();
        return;
      }

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

      const toggleBtn = e.target.closest("[data-toggle]");
      if (!toggleBtn) return;
      if (toggleBtn.dataset.toggle === "heading") {
        const toHeading = row.dataset.kind !== "heading";
        const heading = field(row, "ingredient_heading");
        const item = field(row, "ingredient_item");
        // Carry the text across so switching doesn't lose what was typed.
        if (toHeading && !heading.value) heading.value = item.value;
        if (!toHeading && !item.value) item.value = heading.value;
        setKind(row, toHeading ? "heading" : "item");
        row.classList.remove("is-guess");
      } else if (toggleBtn.dataset.toggle === "no_scale") {
        const input = field(row, "ingredient_no_scale");
        const on = input.value !== "1";
        input.value = on ? "1" : "0";
        toggleBtn.classList.toggle("is-on", on);
        toggleBtn.setAttribute("aria-pressed", on ? "true" : "false");
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
