/* Shared by the console and the landing page: call /ask and render the answer. */
window.ExitZero = (function () {
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  function icon(name) {
    var i = document.createElement("i");
    i.setAttribute("data-lucide", name);
    return i;
  }

  // navigator.clipboard only exists on https or localhost, so keep a fallback
  function copy(text) {
    return rawCopy(text).then(function () {
      document.dispatchEvent(new CustomEvent("exitzero:copied"));
    });
  }

  function rawCopy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var t = document.createElement("textarea");
      t.value = text;
      t.setAttribute("readonly", "");
      t.style.position = "fixed";
      t.style.opacity = "0";
      document.body.append(t);
      t.select();
      var ok = document.execCommand("copy");
      t.remove();
      ok ? resolve() : reject(new Error("copy failed"));
    });
  }

  function flash(labelNode, done, idle) {
    labelNode.textContent = done;
    setTimeout(function () {
      labelNode.textContent = idle;
    }, 1500);
  }

  function block(cls, title, body) {
    var b = el("div", "block " + cls);
    b.append(el("h3", null, title), el("p", null, body));
    return b;
  }

  function commandButton(cmd) {
    var b = el("button", "cmd");
    b.type = "button";
    b.title = "Click to copy";
    b.setAttribute("aria-label", "Copy command: " + cmd);
    var label = el("span", null, "Copy");
    var hint = el("span", "cmd-copy");
    hint.append(icon("copy"), label);
    b.append(el("code", null, cmd), hint);
    b.addEventListener("click", function () {
      copy(cmd).then(function () {
        b.classList.add("is-copied");
        flash(label, "Copied", "Copy");
        setTimeout(function () {
          b.classList.remove("is-copied");
        }, 1500);
      });
    });
    return b;
  }

  function render(target, data) {
    target.replaceChildren();

    var head = el("div", "result-head");
    var title = el("div", "result-title");
    title.append(el("h2", null, data.found ? "Likely match" : "No match"));
    if (data.tool) title.append(el("span", "badge badge-tool", "Detected: " + data.tool));
    var right = el("div", "head-right");
    right.append(el("span", "badge", data.backend));
    head.append(title, right);
    target.append(head);

    if (!data.found) {
      target.append(
        block("block-miss", "Not in my runbooks yet", "Nothing in the knowledge base looks like this error. Check the raw logs, and if you solve it, add it as an incident so the next search finds it.")
      );
    } else {
      var copyAll = el("button", "btn btn-ghost copy");
      copyAll.type = "button";
      var copyLabel = el("span", null, "Copy answer");
      copyAll.append(icon("clipboard"), copyLabel);
      copyAll.addEventListener("click", function () {
        var text = "Likely cause: " + data.cause + "\nWhat to do: " + data.fix;
        if (data.commands.length) text += "\n\n" + data.commands.join("\n");
        copy(text).then(function () {
          flash(copyLabel, "Copied", "Copy answer");
        });
      });
      right.append(copyAll);

      target.append(block("block-cause", "Likely cause", data.cause));
      target.append(block("block-fix", "What to do", data.fix));

      if (data.commands.length) {
        var cmds = el("div", "cmds");
        cmds.append(el("h3", null, "Run this"));
        var risks = data.command_risks || [];
        var notes = {
          destructive: "Changes or deletes things. Read it before you run it.",
          sensitive: "Prints a secret. Don't paste the output anywhere."
        };
        data.commands.forEach(function (c, i) {
          var risk = risks[i];
          if (notes[risk]) {
            var warn = el("p", "cmd-risk cmd-risk-" + risk);
            warn.append(icon("triangle-alert"), el("span", null, notes[risk]));
            cmds.append(warn);
          }
          cmds.append(commandButton(c));
        });
        target.append(cmds);
      }
      if (data.blocked) {
        var gone = el("p", "cmd-risk cmd-risk-blocked");
        gone.append(icon("shield-alert"), el("span", null, data.blocked + (data.blocked === 1 ? " unsafe command was" : " unsafe commands were") + " removed by the safety check."));
        target.append(gone);
      }
      if (data.related.length) {
        target.append(el("p", "related", "Also similar: " + data.related.join("; ")));
      }
      var src = el("div", "sources");
      src.append(el("h3", null, "Sources"));
      data.sources.forEach(function (s) {
        var row = el("div", "src");
        row.append(icon("file-text"), el("span", null, s.snippet), el("small", null, s.title));
        src.append(row);
      });
      target.append(src);
    }
    target.hidden = false;
    if (window.lucide) window.lucide.createIcons();
  }

  function ask(text) {
    return fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: text }),
    }).then(function (res) {
      if (!res.ok) throw new Error("The server answered " + res.status + ".");
      return res.json();
    });
  }

  return { ask: ask, render: render, copy: copy, el: el };
})();
