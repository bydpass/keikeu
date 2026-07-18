(function () {
  "use strict";

  const body = document.body;
  const themeButton = document.querySelector("[data-theme-toggle]");
  const savedTheme = localStorage.getItem("keikeu-doc-theme");

  if (savedTheme === "dark") body.dataset.theme = "dark";
  if (themeButton) {
    themeButton.textContent = body.dataset.theme === "dark" ? "昼" : "夜";
    themeButton.addEventListener("click", function () {
      body.dataset.theme = body.dataset.theme === "dark" ? "light" : "dark";
      localStorage.setItem("keikeu-doc-theme", body.dataset.theme);
      themeButton.textContent = body.dataset.theme === "dark" ? "昼" : "夜";
    });
  }

  const navLinks = Array.from(document.querySelectorAll(".rail nav a"));
  const sections = navLinks
    .map(function (link) { return document.querySelector(link.getAttribute("href")); })
    .filter(Boolean);
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(function (entries) {
      const visible = entries.filter(function (entry) { return entry.isIntersecting; })[0];
      if (!visible) return;
      navLinks.forEach(function (link) {
        link.classList.toggle("active", link.getAttribute("href") === "#" + visible.target.id);
      });
    }, { rootMargin: "-18% 0px -70% 0px", threshold: 0.01 });
    sections.forEach(function (section) { observer.observe(section); });
  }

  const search = document.querySelector("[data-doc-search]");
  const noResults = document.querySelector("[data-no-results]");
  if (search) {
    search.addEventListener("input", function () {
      const query = search.value.trim().toLocaleLowerCase();
      let visibleCount = 0;
      document.querySelectorAll(".section.searchable").forEach(function (section) {
        const haystack = (section.dataset.search || section.textContent).toLocaleLowerCase();
        const visible = !query || haystack.includes(query);
        section.hidden = !visible;
        if (visible) visibleCount += 1;
      });
      if (noResults) noResults.classList.toggle("visible", visibleCount === 0);
    });
  }

  document.querySelectorAll("[data-panel-group]").forEach(function (group) {
    const name = group.dataset.panelGroup;
    const buttons = Array.from(group.querySelectorAll("[data-panel-target]"));
    const panels = Array.from(document.querySelectorAll('[data-panel="' + name + '"]'));
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        const target = button.dataset.panelTarget;
        buttons.forEach(function (item) {
          const active = item === button;
          item.classList.toggle("active", active);
          item.setAttribute("aria-selected", String(active));
        });
        panels.forEach(function (panel) {
          panel.classList.toggle("active", panel.dataset.panelId === target);
        });
      });
    });
  });

  document.querySelectorAll("[data-layer-filter]").forEach(function (button) {
    button.addEventListener("click", function () {
      const layer = button.dataset.layerFilter;
      document.querySelectorAll("[data-layer-filter]").forEach(function (item) {
        item.classList.toggle("active", item === button);
      });
      document.querySelectorAll(".node[data-layer]").forEach(function (node) {
        node.classList.toggle("dim", layer !== "all" && node.dataset.layer !== layer);
      });
    });
  });
})();
