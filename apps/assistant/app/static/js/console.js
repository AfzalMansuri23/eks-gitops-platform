(function () {
  var form = document.getElementById("ask-form");
  var input = document.getElementById("error");
  var btn = document.getElementById("ask-btn");
  var result = document.getElementById("result");
  var errBox = document.getElementById("error-box");
  var errText = document.getElementById("error-text");
  var el = ExitZero.el;
  var bot = ExitZeroBot.mount(document.getElementById("bot-stage"));
  var busy = false;

  var RECENT_KEY = "exitzero-recent";
  var recentWrap = document.getElementById("recent-wrap");
  var recentBox = document.getElementById("recent");

  function loadRecent() {
    try {
      return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }
  function storeRecent(list) {
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(list));
    } catch (e) {}
  }
  function drawRecent() {
    var list = loadRecent();
    recentWrap.hidden = !list.length;
    recentBox.replaceChildren();
    list.forEach(function (text) {
      var first = text.split("\n")[0];
      var b = el("button", "example", first.length > 36 ? first.slice(0, 36) + "..." : first);
      b.type = "button";
      b.title = text;
      b.addEventListener("click", function () {
        input.value = text;
        input.focus();
        bot.set("typing");
      });
      recentBox.append(b);
    });
  }
  function saveRecent(text) {
    var list = loadRecent().filter(function (t) {
      return t !== text;
    });
    list.unshift(text);
    storeRecent(list.slice(0, 5));
    drawRecent();
  }
  document.getElementById("clear-recent").addEventListener("click", function () {
    storeRecent([]);
    drawRecent();
  });
  drawRecent();

  function setBusy(on) {
    busy = on;
    btn.disabled = on;
    btn.querySelector("span").textContent = on ? "Searching" : "Find the fix";
    var icon = btn.querySelector(".lucide");
    if (icon) icon.classList.toggle("spin", on);
  }

  // local answers come back in milliseconds; hold the thinking face long enough to read
  function atLeast(ms, promise) {
    return Promise.all([promise, new Promise(function (r) { setTimeout(r, ms); })]).then(function (v) {
      return v[0];
    });
  }

  function ask() {
    var text = input.value.trim();
    if (text.length < 3) {
      bot.set("short");
      input.focus();
      return;
    }
    errBox.hidden = true;
    setBusy(true);
    bot.set("thinking");
    atLeast(700, ExitZero.ask(text))
      .then(function (data) {
        ExitZero.render(result, data);
        bot.set(data.found ? "found" : "miss");
        saveRecent(text);
      })
      .catch(function (e) {
        result.hidden = true;
        errText.textContent = "Couldn't reach the assistant. " + e.message + " Try again in a moment.";
        errBox.hidden = false;
        bot.set("error");
      })
      .finally(function () {
        setBusy(false);
      });
  }

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
  input.addEventListener("input", function () {
    if (busy) return;
    var mood = bot.mood();
    if (!input.value.trim()) bot.set("idle");
    else if (mood !== "typing") bot.set("typing");
  });
  document.querySelectorAll(".example[data-text]").forEach(function (b) {
    b.addEventListener("click", function () {
      input.value = b.getAttribute("data-text");
      input.focus();
      bot.set("typing");
    });
  });
})();
