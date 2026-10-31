/* Architecture diagram: renders static/data/architecture.json into SVG.
   Everything on the diagram comes from the config; this file only draws it.
   Used by /architecture and inlined into docs/architecture.html. */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var NODE_W = 200;
  var NODE_H = 60;
  var STEP_MS = 2500;
  var SPEED = 90; // packet speed, px per second
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function svg(tag, attrs, parent) {
    var el = document.createElementNS(NS, tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  }

  function html(tag, cls, parent, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null) el.textContent = text;
    if (parent) parent.appendChild(el);
    return el;
  }

  // orthogonal polyline with small rounded corners
  function roundedPath(pts, r) {
    var d = "M" + pts[0][0] + "," + pts[0][1];
    for (var i = 1; i < pts.length - 1; i++) {
      var p = pts[i - 1], c = pts[i], n = pts[i + 1];
      var r1 = Math.min(r, dist(p, c) / 2), r2 = Math.min(r, dist(c, n) / 2);
      var a = toward(c, p, r1), b = toward(c, n, r2);
      d += " L" + a[0] + "," + a[1] + " Q" + c[0] + "," + c[1] + " " + b[0] + "," + b[1];
    }
    var last = pts[pts.length - 1];
    return d + " L" + last[0] + "," + last[1];
  }

  function dist(a, b) {
    return Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);
  }

  function toward(from, to, len) {
    var dx = Math.sign(to[0] - from[0]), dy = Math.sign(to[1] - from[1]);
    return [from[0] + dx * len, from[1] + dy * len];
  }

  function pathLength(pts) {
    var total = 0;
    for (var i = 1; i < pts.length; i++) total += dist(pts[i - 1], pts[i]);
    return total;
  }

  function flowStyles(cfg, scope) {
    var dark = [], light = [];
    cfg.flows.forEach(function (f) {
      dark.push("--flow-" + f.id + ":" + f.color.dark);
      light.push("--flow-" + f.id + ":" + f.color.light);
    });
    // one element, replaced on every mount, so switching views does not pile up rules
    var style = document.getElementById("arch-flow-colors") || document.createElement("style");
    style.id = "arch-flow-colors";
    style.textContent =
      scope + "{" + dark.join(";") + "}" + ':root[data-theme="light"] ' + scope + "{" + light.join(";") + "}";
    document.head.appendChild(style);
  }

  function mount(root, cfg) {
    var nodes = {}, edges = {}, flows = {};
    cfg.nodes.forEach(function (n) { nodes[n.id] = n; });
    cfg.edges.forEach(function (e) { edges[e.id] = e; });
    cfg.flows.forEach(function (f) { flows[f.id] = f; });

    root.classList.add("arch");
    flowStyles(cfg, ".arch");

    // ---- layout: chips, diagram, panels
    var chips = html("div", "arch-chips", root);
    chips.setAttribute("role", "toolbar");
    chips.setAttribute("aria-label", "Filter by flow");
    var scroller = html("div", "arch-scroll", root);
    scroller.setAttribute("tabindex", "0");
    scroller.setAttribute("aria-label", "Architecture diagram, scrolls sideways on small screens");
    var panels = html("div", "arch-panels", root);
    var stepsPanel = html("section", "arch-panel arch-steps", panels);
    var detailPanel = html("section", "arch-panel arch-detail", panels);
    detailPanel.setAttribute("aria-live", "polite");

    var W = cfg.canvas.width, H = cfg.canvas.height;
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, class: "arch-svg", role: "group", "aria-label": "Platform architecture" }, scroller);
    var defs = svg("defs", {}, s);
    cfg.flows.forEach(function (f) {
      var m = svg("marker", {
        id: "arch-arrow-" + f.id, viewBox: "0 0 10 10", refX: "9", refY: "5",
        markerWidth: "9", markerHeight: "9", markerUnits: "userSpaceOnUse", orient: "auto"
      }, defs);
      svg("path", { d: "M0,1 L9,5 L0,9 z", style: "fill:var(--flow-" + f.id + ")" }, m);
    });
    // grey arrowhead for the calm overview (no flow picked)
    var muted = svg("marker", {
      id: "arch-arrow-muted", viewBox: "0 0 10 10", refX: "9", refY: "5",
      markerWidth: "8", markerHeight: "8", markerUnits: "userSpaceOnUse", orient: "auto"
    }, defs);
    svg("path", { d: "M0,1 L9,5 L0,9 z", class: "arch-arrow-muted" }, muted);

    var gZones = svg("g", { class: "arch-zones" }, s);
    var gEdges = svg("g", { class: "arch-edges" }, s);
    var gNodes = svg("g", { class: "arch-nodes" }, s);

    var zoneEls = [];
    cfg.zones.forEach(function (z) {
      var g = svg("g", { class: "zone" }, gZones);
      svg("rect", { class: "zone-box", x: z.x, y: z.y, width: z.w, height: z.h, rx: 14 }, g);
      var t = svg("text", { class: "zone-label", x: z.x + 14, y: z.y + 20 }, g);
      t.textContent = z.label.toUpperCase();
      zoneEls.push({ z: z, g: g });
    });

    function inside(z, n) {
      var cx = n.x + NODE_W / 2, cy = n.y + NODE_H / 2;
      return cx > z.x && cx < z.x + z.w && cy > z.y && cy < z.y + z.h;
    }

    var edgeEls = {};
    cfg.edges.forEach(function (e) {
      var d = roundedPath(e.path, 8);
      var g = svg("g", { class: "edge" + (e.status === "planned" ? " is-planned" : ""), "data-flow": e.flow, style: "--c:var(--flow-" + e.flow + ")" }, gEdges);
      svg("path", { class: "edge-track", d: d }, g);
      svg("path", { class: "edge-line", d: d, id: "arch-edge-" + e.id, "marker-end": "url(#arch-arrow-" + e.flow + ")" }, g);
      var len = pathLength(e.path);
      var dur = Math.max(1.4, len / SPEED);
      var count = len > 500 ? 3 : 2;
      for (var i = 0; i < count; i++) {
        var pk = svg("path", { class: "packet", d: "M-4,-4 L1,0 L-4,4" }, g);
        var am = svg("animateMotion", {
          dur: dur.toFixed(2) + "s", begin: (-(dur / count) * i).toFixed(2) + "s",
          repeatCount: "indefinite", rotate: "auto"
        }, pk);
        svg("mpath", { href: "#arch-edge-" + e.id }, am);
      }
      edgeEls[e.id] = g;
    });

    var nodeEls = {};
    cfg.nodes.forEach(function (n) {
      var g = svg("g", {
        class: "node" + (n.status === "planned" ? " is-planned" : ""), transform: "translate(" + n.x + "," + n.y + ")", tabindex: "0", role: "button",
        "aria-label": n.title + ", " + n.subtitle + ". Show details", style: "--c:var(--flow-" + n.flow + ")"
      }, gNodes);
      svg("rect", { class: "node-box", width: NODE_W, height: NODE_H, rx: 10 }, g);
      svg("rect", { class: "node-tag", x: 10, y: 15, width: 38, height: 30, rx: 7 }, g);
      var tag = svg("text", { class: "node-tag-text", x: 29, y: 34.5, "text-anchor": "middle" }, g);
      tag.textContent = n.tag;
      var title = svg("text", { class: "node-title", x: 58, y: 27 }, g);
      title.textContent = n.title;
      var sub = svg("text", { class: "node-sub", x: 58, y: 45 }, g);
      sub.textContent = n.subtitle;
      nodeEls[n.id] = g;
      g.addEventListener("mouseenter", function () { hover(n.id); });
      g.addEventListener("mouseleave", function () { hover(null); });
      g.addEventListener("focus", function () { hover(n.id); });
      g.addEventListener("blur", function () { hover(null); });
      g.addEventListener("click", function () { showNode(n.id); });
      g.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          showNode(n.id);
        }
      });
    });

    // keep long subtitles inside the card
    requestAnimationFrame(function () {
      s.querySelectorAll(".node-sub, .node-title").forEach(function (t) {
        var max = NODE_W - 66;
        if (t.getComputedTextLength && t.getComputedTextLength() > max) {
          t.setAttribute("textLength", max);
          t.setAttribute("lengthAdjust", "spacingAndGlyphs");
        }
      });
    });

    // ---- state
    var state = { flow: null, step: 0, playing: !reduced, hover: null, timer: null, details: false };

    function flowsOfNode(id) {
      var out = [nodes[id].flow];
      cfg.edges.forEach(function (e) {
        if ((e.from === id || e.to === id) && out.indexOf(e.flow) < 0) out.push(e.flow);
      });
      return out;
    }

    function paint() {
      var onE = {}, onN = {}, active = {}, lit = {};
      var focus = state.hover || state.flow;
      if (state.hover) {
        onN[state.hover] = true;
        cfg.edges.forEach(function (e) {
          if (e.from === state.hover || e.to === state.hover) {
            onE[e.id] = true;
            onN[e.from] = onN[e.to] = true;
          }
        });
      } else if (state.flow) {
        cfg.edges.forEach(function (e) {
          if (e.flow === state.flow) {
            onE[e.id] = true;
            onN[e.from] = onN[e.to] = true;
          }
        });
        // a flow's steps may also walk edges drawn in another flow's colour
        flows[state.flow].steps.forEach(function (st) {
          st.edges.forEach(function (id) {
            onE[id] = true;
            onN[edges[id].from] = onN[edges[id].to] = true;
          });
        });
        var step = flows[state.flow].steps[state.step];
        step.edges.forEach(function (id) {
          active[id] = true;
          lit[edges[id].to] = true;
        });
      }
      s.classList.toggle("has-focus", !!focus);
      // calm overview: grey, still lines until a flow is picked or a card hovered
      s.classList.toggle("is-overview", !focus);
      // detail cards stay hidden unless asked for, or used by the flow or hover in view
      var hidden = {};
      cfg.nodes.forEach(function (n) {
        hidden[n.id] = !!n.detail && !state.details && !onN[n.id];
      });
      for (var id in edgeEls) {
        var e = edges[id];
        edgeEls[id].classList.toggle("on", !!onE[id]);
        edgeEls[id].classList.toggle("active", !!active[id] && !state.hover);
        // flow-only edges (long lab-day lines) show only while their flow or a hover uses them
        edgeEls[id].classList.toggle("is-hidden", (!!e.flowOnly && !onE[id]) || hidden[e.from] || hidden[e.to]);
      }
      for (var nid in nodeEls) {
        nodeEls[nid].classList.toggle("on", !!onN[nid]);
        nodeEls[nid].classList.toggle("lit", !!lit[nid] && !state.hover);
        nodeEls[nid].classList.toggle("is-hidden", hidden[nid]);
      }
      // a detail zone shows once anything inside it is visible
      zoneEls.forEach(function (ze) {
        var show = !ze.z.detail || cfg.nodes.some(function (n) { return inside(ze.z, n) && !hidden[n.id]; });
        ze.g.classList.toggle("is-hidden", !show);
      });
    }

    function hover(id) {
      state.hover = id;
      paint();
    }

    // ---- flow chips
    function chip(label, flowId) {
      var b = html("button", "arch-chip", chips, null);
      b.type = "button";
      if (flowId) {
        b.style.setProperty("--c", "var(--flow-" + flowId + ")");
        html("span", "arch-dot", b);
      }
      b.appendChild(document.createTextNode(label));
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () { selectFlow(flowId); });
      b.dataset.flow = flowId || "";
      return b;
    }
    chip("All flows", null);
    cfg.flows.forEach(function (f) { chip(f.name, f.id); });

    if (cfg.nodes.some(function (n) { return n.detail; })) {
      var more = html("button", "arch-chip arch-details", chips, "Show details");
      more.type = "button";
      more.setAttribute("aria-pressed", "false");
      more.addEventListener("click", function () {
        state.details = !state.details;
        more.setAttribute("aria-pressed", String(state.details));
        more.textContent = state.details ? "Hide details" : "Show details";
        paint();
      });
    }

    function selectFlow(id) {
      state.flow = id;
      state.step = 0;
      chips.querySelectorAll(".arch-chip[data-flow]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.flow === (id || "")));
      });
      renderSteps();
      paint();
      schedule();
    }

    function schedule() {
      clearInterval(state.timer);
      if (state.flow && state.playing) {
        state.timer = setInterval(function () {
          var steps = flows[state.flow].steps;
          state.step = (state.step + 1) % steps.length;
          renderSteps();
          paint();
        }, STEP_MS);
      }
    }

    function renderSteps() {
      stepsPanel.textContent = "";
      if (!state.flow) {
        html("h2", "arch-panel-title", stepsPanel, "Flows");
        html("p", "arch-muted", stepsPanel, "Pick a flow to play it hop by hop. Hover a component to see what it talks to.");
        var list = html("ul", "arch-legend", stepsPanel);
        cfg.flows.forEach(function (f) {
          var li = html("li", null, list);
          var b = html("button", "arch-legend-btn", li);
          b.type = "button";
          b.style.setProperty("--c", "var(--flow-" + f.id + ")");
          html("span", "arch-dot", b);
          b.appendChild(document.createTextNode(f.name + " · " + f.steps.length + " steps"));
          b.addEventListener("click", function () { selectFlow(f.id); });
        });
        return;
      }
      var f = flows[state.flow];
      var head = html("div", "arch-steps-head", stepsPanel);
      var h = html("h2", "arch-panel-title", head, f.name);
      h.style.setProperty("--c", "var(--flow-" + f.id + ")");
      var toggle = html("button", "arch-play", head, state.playing ? "Pause" : "Play");
      toggle.type = "button";
      toggle.setAttribute("aria-label", state.playing ? "Pause the walkthrough" : "Play the walkthrough");
      toggle.addEventListener("click", function () {
        state.playing = !state.playing;
        renderSteps();
        schedule();
        stepsPanel.querySelector(".arch-play").focus();
      });
      var ol = html("ol", "arch-step-list", stepsPanel);
      ol.style.setProperty("--c", "var(--flow-" + f.id + ")");
      f.steps.forEach(function (st, i) {
        var li = html("li", null, ol);
        var b = html("button", "arch-step" + (i === state.step ? " is-current" : ""), li);
        b.type = "button";
        if (i === state.step) b.setAttribute("aria-current", "step");
        html("span", "arch-step-n", b, String(i + 1));
        html("span", "arch-step-text", b, st.text);
        b.addEventListener("click", function () {
          state.step = i;
          renderSteps();
          paint();
          schedule();
          stepsPanel.querySelectorAll(".arch-step")[i].focus();
        });
      });
    }

    function showNode(id) {
      var n = nodes[id];
      detailPanel.textContent = "";
      var head = html("div", "arch-detail-head", detailPanel);
      var tag = html("span", "arch-tag", head, n.tag);
      tag.style.setProperty("--c", "var(--flow-" + n.flow + ")");
      var titles = html("div", null, head);
      html("h2", "arch-panel-title", titles, n.title);
      html("p", "arch-mono arch-muted", titles, n.subtitle);
      html("p", "arch-desc", detailPanel, n.description);
      var facts = html("ul", "arch-facts", detailPanel);
      n.facts.forEach(function (f) { html("li", null, facts, f); });
      var fl = html("div", "arch-node-flows", detailPanel);
      html("span", "arch-muted", fl, "Flows: ");
      flowsOfNode(id).forEach(function (fid) {
        var b = html("button", "arch-chip arch-chip-sm", fl);
        b.type = "button";
        b.style.setProperty("--c", "var(--flow-" + fid + ")");
        html("span", "arch-dot", b);
        b.appendChild(document.createTextNode(flows[fid].name));
        b.addEventListener("click", function () { selectFlow(fid); });
      });
      var a = html("a", "arch-source", detailPanel);
      a.href = cfg.repo + n.source;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = n.source;
      html("span", "arch-muted", a, "  view source");
    }

    function emptyDetail() {
      detailPanel.textContent = "";
      html("h2", "arch-panel-title", detailPanel, "Details");
      html("p", "arch-muted", detailPanel, "Click or press Enter on a component to see what it does, its key settings, and the file that defines it.");
    }

    emptyDetail();
    selectFlow(null);
  }

  // several configs on one page: a switch above the diagram, the choice kept in the URL hash
  function mountViews(root, views) {
    var bar = html("div", "arch-views");
    bar.setAttribute("role", "tablist");
    bar.setAttribute("aria-label", "Diagram view");
    var holder = html("div", null);
    root.append(bar, holder);
    var buttons = views.map(function (v, i) {
      var b = html("button", "arch-view", bar, v.label);
      b.type = "button";
      b.setAttribute("role", "tab");
      b.addEventListener("click", function () { show(i, true); });
      return b;
    });
    html("span", "arch-views-key", bar, "Dashed: in the plan, not in the code yet");

    function show(i, push) {
      buttons.forEach(function (b, j) { b.setAttribute("aria-selected", String(i === j)); });
      var fresh = html("div", null);
      holder.replaceWith(fresh);
      holder = fresh;
      mount(holder, views[i].config);
      if (push) history.replaceState(null, "", "#" + views[i].id);
    }
    var start = views.findIndex(function (v) { return "#" + v.id === location.hash; });
    show(start < 0 ? 0 : start, false);
  }

  window.ArchDiagram = { mount: mount, mountViews: mountViews };
})();
