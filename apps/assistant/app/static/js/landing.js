(function () {
  var HERO = [
    {
      err: 'Back-off pulling image "docker.elastic.co/elasticsearch/elasticsearch:9.5.6"\nError: ErrImagePull: manifest unknown',
      cause: "That tag was never published, so the registry has nothing to serve.",
      fix: "Run `docker manifest inspect <image>` before you apply, then pin the newest tag that exists.",
      src: "README · Logging",
    },
    {
      err: "Error: Error acquiring the state lock\nConditionalCheckFailedException: The conditional request failed",
      cause: "Another run holds the lock, or an earlier run died before letting go.",
      fix: "Make sure nobody is applying, then run `terraform force-unlock <lock-id>`.",
      src: "Study notes · Terraform",
    },
    {
      err: "Not authorized to perform sts:AssumeRoleWithWebIdentity",
      cause: "The repo uses immutable OIDC subject claims, so the trust policy never matched.",
      fix: "Put the immutable subject form in the role's trust policy and re-apply it.",
      src: "README · CI/CD",
    },
    {
      err: "flood stage disk watermark [95%] exceeded on [logging-es-default-0]",
      cause: "Disk passed the flood-stage watermark, so Elasticsearch blocked writes.",
      fix: "Free disk space first, then clear `index.blocks.read_only_allow_delete`.",
      src: "Known issue · Elasticsearch",
    },
  ];
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* put `code` spans in text without using innerHTML */
  function fill(node, text) {
    node.replaceChildren();
    text.split("`").forEach(function (part, i) {
      if (i % 2) {
        var c = document.createElement("code");
        c.textContent = part;
        node.append(c);
      } else {
        node.append(document.createTextNode(part));
      }
    });
  }

  /* hero demo */
  var heroErr = document.getElementById("demo-err");
  if (heroErr) {
    var heroAns = document.getElementById("demo-answer");
    var idx = 0;

    var show = function (s) {
      document.getElementById("demo-cause").textContent = s.cause;
      fill(document.getElementById("demo-fix"), s.fix);
      document.getElementById("demo-src").textContent = s.src;
      heroAns.classList.add("is-on");
    };

    var play = function () {
      var s = HERO[idx++ % HERO.length];
      heroAns.classList.remove("is-on");
      heroErr.textContent = "";
      var i = 0;
      var type = function () {
        i += 2;
        heroErr.textContent = s.err.slice(0, i);
        if (i < s.err.length) {
          setTimeout(type, 22);
        } else {
          setTimeout(function () {
            show(s);
            setTimeout(play, 5200);
          }, 350);
        }
      };
      type();
    };

    if (reduced) {
      heroErr.textContent = HERO[0].err;
      show(HERO[0]);
    } else {
      play();
    }
  }

  /* live box */
  var form = document.getElementById("live-form");
  if (form) {
    var input = document.getElementById("live-input");
    var btn = document.getElementById("live-btn");
    var out = document.getElementById("live-result");
    var bot = ExitZeroBot.mount(document.getElementById("bot-stage"));
    var busy = false;
    var wait = function (ms) {
      return new Promise(function (r) { setTimeout(r, ms); });
    };

    var ask = function () {
      var text = input.value.trim();
      if (text.length < 3) {
        bot.set("short");
        input.focus();
        return;
      }
      busy = true;
      btn.disabled = true;
      btn.querySelector("span").textContent = "Searching";
      bot.set("thinking");
      Promise.all([ExitZero.ask(text), wait(700)])
        .then(function (v) {
          ExitZero.render(out, v[0]);
          bot.set(v[0].found ? "found" : "miss");
        })
        .catch(function (e) {
          out.replaceChildren(ExitZero.el("p", "related", "Couldn't reach the assistant. " + e.message));
          out.hidden = false;
          bot.set("error");
        })
        .finally(function () {
          busy = false;
          btn.disabled = false;
          btn.querySelector("span").textContent = "Find the fix";
        });
    };

    input.addEventListener("input", function () {
      if (busy) return;
      if (!input.value.trim()) bot.set("idle");
      else if (bot.mood() !== "typing") bot.set("typing");
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      ask();
    });
    input.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        ask();
      }
    });
    form.querySelectorAll(".example").forEach(function (b) {
      b.addEventListener("click", function () {
        input.value = b.getAttribute("data-text");
        ask();
      });
    });
  }

  /* keep the tool list and counts in step with the knowledge base */
  fetch("/tools")
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(function (d) {
      if (!d) return;
      var list = document.getElementById("tool-list");
      list.replaceChildren();
      d.tools.forEach(function (t) {
        list.append(ExitZero.el("li", null, t));
      });
      document.getElementById("stat-tools").textContent = d.tools.length;
      document.getElementById("stat-entries").textContent = d.entries;
    })
    .catch(function () {});
})();
