(function () {
  const menu = document.querySelector("[data-user-menu]");
  if (!menu) return;

  const trigger = menu.querySelector(".user-menu-trigger");
  const panel = menu.querySelector(".user-menu-panel");
  const subTrigger = menu.querySelector(".user-menu-item--expand");
  const submenu = menu.querySelector(".user-menu-submenu");

  function setOpen(open) {
    panel.hidden = !open;
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
  }

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    setOpen(panel.hidden);
  });

  if (subTrigger && submenu) {
    subTrigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = submenu.hidden;
      submenu.hidden = !open;
      subTrigger.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  document.addEventListener("click", (e) => {
    if (!panel.hidden && !menu.contains(e.target)) setOpen(false);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) {
      setOpen(false);
      trigger.focus();
    }
  });
})();
