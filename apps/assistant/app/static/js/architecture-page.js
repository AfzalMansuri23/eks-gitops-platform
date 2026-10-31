/* /architecture: load the diagram config and render it. */
(function () {
  var root = document.getElementById("arch");
  fetch("/static/data/architecture.json")
    .then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .then(function (cfg) {
      root.textContent = "";
      window.ArchDiagram.mount(root, cfg);
    })
    .catch(function () {
      root.textContent = "Could not load the diagram data.";
    });
})();
