/* /architecture: load both diagram configs and render them behind a view switch. */
(function () {
  var root = document.getElementById("arch");
  var views = [
    { id: "kind", label: "kind (today)", url: "/static/data/architecture.json" },
    { id: "aws", label: "AWS (EKS lab day)", url: "/static/data/architecture-eks.json" }
  ];
  Promise.all(
    views.map(function (v) {
      return fetch(v.url).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      });
    })
  )
    .then(function (configs) {
      root.textContent = "";
      window.ArchDiagram.mountViews(
        root,
        views.map(function (v, i) {
          return { id: v.id, label: v.label, config: configs[i] };
        })
      );
    })
    .catch(function () {
      root.textContent = "Could not load the diagram data.";
    });
})();
