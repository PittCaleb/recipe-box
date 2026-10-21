(function () {
  const form = document.getElementById("merge-form");
  if (!form) return;

  const titleInput = document.getElementById("merged-title");
  let titleEdited = false;
  titleInput.addEventListener("input", () => {
    titleEdited = true;
  });

  function sync() {
    const keeper = form.querySelector('input[name="keep_id"]:checked');
    form.querySelectorAll(".dup-col").forEach((col) => {
      const isKeeper = keeper && col.dataset.recipeId === keeper.value;
      col.classList.toggle("is-keeper", isKeeper);
      const merge = col.querySelector('input[name="merge_ids"]');
      merge.disabled = isKeeper;
      col.querySelector(".dup-merge").hidden = isKeeper;
      if (isKeeper && !titleEdited) titleInput.value = col.dataset.cleanTitle;
    });
  }

  form.querySelectorAll('input[name="keep_id"]').forEach((radio) => {
    radio.addEventListener("change", sync);
  });
  sync();

  form.addEventListener("submit", (e) => {
    if (e.submitter && e.submitter.getAttribute("form") === "dismiss-form") return;
    const checked = form.querySelectorAll('input[name="merge_ids"]:checked:not(:disabled)');
    if (checked.length === 0) {
      e.preventDefault();
      window.alert("Check at least one other copy to merge in.");
      return;
    }
    if (!window.confirm(form.dataset.confirm)) e.preventDefault();
  });
})();
