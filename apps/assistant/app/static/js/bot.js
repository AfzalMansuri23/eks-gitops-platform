/* The ExitZero bot: peeks over the top edge of a panel and reacts to what's happening. */
window.ExitZeroBot = (function () {
  var INK = "#0a1114";
  var SKIN = "#eef7f5";

  var EYES = {
    open:
      '<circle cx="17.5" cy="11.5" r="2.7" fill="' + INK + '"/><circle cx="26.5" cy="11.5" r="2.7" fill="' + INK + '"/>' +
      '<circle cx="18.4" cy="10.6" r=".85" fill="#fff"/><circle cx="27.4" cy="10.6" r=".85" fill="#fff"/>',
    down: '<circle cx="17.5" cy="13.4" r="2.4" fill="' + INK + '"/><circle cx="26.5" cy="13.4" r="2.4" fill="' + INK + '"/>',
    up: '<circle cx="18.6" cy="10" r="2.5" fill="' + INK + '"/><circle cx="27.4" cy="10" r="2.5" fill="' + INK + '"/>',
    side: '<circle cx="16" cy="11.8" r="2.5" fill="' + INK + '"/><circle cx="25" cy="11.8" r="2.5" fill="' + INK + '"/>',
    happy:
      '<path d="M14.8 12.6 q2.7 -3.4 5.4 0" fill="none" stroke="' + INK + '" stroke-width="2.1" stroke-linecap="round"/>' +
      '<path d="M23.8 12.6 q2.7 -3.4 5.4 0" fill="none" stroke="' + INK + '" stroke-width="2.1" stroke-linecap="round"/>',
    wink:
      '<path d="M14.8 12.6 q2.7 -3.4 5.4 0" fill="none" stroke="' + INK + '" stroke-width="2.1" stroke-linecap="round"/>' +
      '<circle cx="26.5" cy="11.5" r="2.7" fill="' + INK + '"/><circle cx="27.4" cy="10.6" r=".85" fill="#fff"/>',
    x:
      '<path d="M15.6 9.6 l3.8 3.8 M19.4 9.6 l-3.8 3.8 M24.6 9.6 l3.8 3.8 M28.4 9.6 l-3.8 3.8" stroke="' + INK + '" stroke-width="2" stroke-linecap="round"/>',
  };

  var MOUTHS = {
    smile: '<path d="M19 16.6 q3 3 6 0" fill="none" stroke="' + INK + '" stroke-width="1.8" stroke-linecap="round"/>',
    grin: '<path d="M18 16 q4 5.2 8 0 z" fill="' + INK + '"/>',
    o: '<ellipse cx="22" cy="17.5" rx="1.7" ry="1.4" fill="' + INK + '"/>',
    hmm: '<line x1="19.5" y1="17.8" x2="24.5" y2="17" stroke="' + INK + '" stroke-width="1.8" stroke-linecap="round"/>',
    flat: '<line x1="19.5" y1="17.5" x2="24.5" y2="17.5" stroke="' + INK + '" stroke-width="1.8" stroke-linecap="round"/>',
    wavy: '<path d="M17.8 17.8 q1.05 -1.4 2.1 0 t2.1 0 t2.1 0 t2.1 0" fill="none" stroke="' + INK + '" stroke-width="1.6" stroke-linecap="round"/>',
  };

  var SYMBOLS = {
    bang: function (c) {
      return '<line x1="40.5" y1="-6" x2="40.5" y2="2.5" stroke="' + c + '" stroke-width="3.2" stroke-linecap="round"/><circle cx="40.5" cy="7" r="1.9" fill="' + c + '"/>';
    },
    dots: function () {
      return '<circle class="bdot d1" cx="36.5" cy="3" r="1.6" fill="#f2a649"/><circle class="bdot d2" cx="40" cy="-1.2" r="2.1" fill="#f2a649"/>' +
        '<circle class="bdot d3" cx="43.6" cy="-6" r="2.6" fill="#f2a649"/>';
    },
    check: function () {
      return '<polyline points="36 -1.5 39.4 2 45.5 -5.5" fill="none" stroke="#2fa36b" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>';
    },
    question: function () {
      return '<path d="M37.6 -4.4 a3.1 3.1 0 1 1 4.6 2.7 c-1.1 .6 -1.6 1.2 -1.6 2.6" fill="none" stroke="#f2a649" stroke-width="2.6" stroke-linecap="round"/>' +
        '<circle cx="40.6" cy="5" r="1.6" fill="#f2a649"/>';
    },
    spark: function () {
      return '<path d="M41 -8 L42.2 -4.2 L46 -3 L42.2 -1.8 L41 2 L39.8 -1.8 L36 -3 L39.8 -4.2 Z" fill="#f2a649"/>';
    },
  };

  var HANDS = {
    grip:
      '<rect x="5" y="18.5" width="6" height="6" rx="3" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="1.6"/>' +
      '<rect x="33" y="18.5" width="6" height="6" rx="3" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="1.6"/>',
    shrug:
      '<rect x="1.5" y="9" width="6" height="6" rx="3" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="1.6"/>' +
      '<rect x="36.5" y="9" width="6" height="6" rx="3" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="1.6"/>',
  };

  var MOODS = {
    idle: { eyes: "open", mouth: "smile", hands: "grip", ball: "#1fb5a4", say: "Paste an error. I'll take a look." },
    typing: { eyes: "down", mouth: "smile", hands: "grip", ball: "#1fb5a4", say: "Reading along..." },
    thinking: { eyes: "up", mouth: "hmm", hands: "grip", ball: "#f2a649", sym: "dots", say: "Checking the runbooks..." },
    found: { eyes: "happy", mouth: "grin", hands: "grip", ball: "#2fa36b", sym: "check", say: "Seen this one before. Here's the fix." },
    miss: { eyes: "side", mouth: "flat", hands: "shrug", ball: "#f2a649", sym: "question", say: "Haven't seen this one. It's not in my runbooks yet." },
    short: { eyes: "open", mouth: "o", hands: "grip", ball: "#1fb5a4", sym: "question", say: "Give me a bit more of the error to work with." },
    error: { eyes: "x", mouth: "wavy", hands: "grip", ball: "#e5484d", sym: "bang", symColor: "#e5484d", say: "I can't reach the server. Is it running?" },
    copied: { eyes: "wink", mouth: "smile", hands: "grip", ball: "#2fa36b", sym: "spark", say: "Copied. Go get that exit 0." },
  };

  function back(m) {
    var sym = m.sym ? SYMBOLS[m.sym](m.symColor || "#f2a649") : "";
    return '<svg viewBox="0 -9 47 37" aria-hidden="true">' +
      '<g class="bot-body">' +
      '<rect x="21" y="-3.5" width="2" height="7" rx="1" fill="#8fa6a9"/>' +
      '<circle cx="22" cy="-4.5" r="2.4" fill="' + m.ball + '" stroke="' + INK + '" stroke-width="1.4"/>' +
      '<rect x="10" y="2.5" width="24" height="23" rx="7" fill="' + SKIN + '" stroke="' + INK + '" stroke-width="2"/>' +
      EYES[m.eyes] + MOUTHS[m.mouth] +
      "</g>" + sym + "</svg>";
  }
  function front(m) {
    return '<svg viewBox="0 -9 47 37" aria-hidden="true">' + HANDS[m.hands] + "</svg>";
  }

  // stage: element wrapping the panel; the bot's head sits behind it, hands in front
  function mount(stage) {
    var b = document.createElement("div");
    b.className = "bot-back";
    var f = document.createElement("div");
    f.className = "bot-front";
    var say = document.createElement("p");
    say.className = "bot-say";
    say.setAttribute("aria-live", "polite");
    stage.prepend(b);
    stage.append(f, say);

    var current = "idle";
    var revertTimer = null;

    function set(name, text) {
      var m = MOODS[name];
      if (!m) return;
      clearTimeout(revertTimer);
      if (name !== "copied") current = name;
      stage.dataset.mood = name;
      b.innerHTML = back(m);
      f.innerHTML = front(m);
      say.textContent = text || m.say;
      say.classList.remove("pop");
      void say.offsetWidth;
      say.classList.add("pop");
      if (name === "copied") {
        revertTimer = setTimeout(function () {
          set(current);
        }, 2200);
      }
    }

    document.addEventListener("exitzero:copied", function () {
      if (stage.isConnected) set("copied");
    });

    set("idle");
    return {
      set: set,
      mood: function () {
        return current;
      },
    };
  }

  return { mount: mount };
})();
