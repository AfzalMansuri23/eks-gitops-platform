(function () {
  var mode = "signin";
  var $ = function (id) {
    return document.getElementById(id);
  };

  var views = { auth: $("view-auth"), forgot: $("view-forgot"), done: $("view-done") };
  function show(name) {
    Object.keys(views).forEach(function (k) {
      views[k].hidden = k !== name;
    });
  }

  function setMsg(input, msgId, text) {
    $(msgId).textContent = text || "";
    if (text) input.setAttribute("aria-invalid", "true");
    else input.removeAttribute("aria-invalid");
    return !text;
  }

  var emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function checkEmail(input, msgId) {
    var v = input.value.trim();
    if (!v) return setMsg(input, msgId, "Enter your email.");
    if (!emailRe.test(v)) return setMsg(input, msgId, "That doesn't look like an email address.");
    return setMsg(input, msgId, "");
  }
  function checkPassword() {
    var v = $("password").value;
    if (!v) return setMsg($("password"), "password-msg", "Enter your password.");
    if (mode === "signup" && v.length < 8) return setMsg($("password"), "password-msg", "Use at least 8 characters.");
    return setMsg($("password"), "password-msg", "");
  }
  function checkName() {
    if (mode !== "signup") return true;
    if (!$("name").value.trim()) return setMsg($("name"), "name-msg", "Tell us what to call you.");
    return setMsg($("name"), "name-msg", "");
  }
  function checkTerms() {
    if (mode !== "signup") return true;
    var ok = $("terms").checked;
    $("terms-msg").textContent = ok ? "" : "Tick the box to continue.";
    return ok;
  }

  /* tabs */
  function setMode(next) {
    mode = next;
    var signup = mode === "signup";
    $("tab-signin").setAttribute("aria-selected", String(!signup));
    $("tab-signup").setAttribute("aria-selected", String(signup));
    $("auth-title").textContent = signup ? "Create your account" : "Welcome back";
    $("auth-sub").textContent = signup ? "Save incidents and build your own runbook." : "Sign in to see your saved incidents.";
    $("field-name").hidden = !signup;
    $("field-terms").hidden = !signup;
    $("strength").hidden = !signup;
    $("to-forgot").hidden = signup;
    $("password").setAttribute("autocomplete", signup ? "new-password" : "current-password");
    $("submit").querySelector("span").textContent = signup ? "Create account" : "Sign in";
    ["name-msg", "email-msg", "password-msg", "terms-msg"].forEach(function (id) {
      $(id).textContent = "";
    });
    ["name", "email", "password"].forEach(function (id) {
      $(id).removeAttribute("aria-invalid");
    });
  }
  $("tab-signin").addEventListener("click", function () {
    setMode("signin");
  });
  $("tab-signup").addEventListener("click", function () {
    setMode("signup");
  });
  if (location.hash === "#signup") setMode("signup");

  /* show / hide password */
  $("reveal").addEventListener("click", function () {
    var input = $("password");
    var shown = input.type === "text";
    input.type = shown ? "password" : "text";
    this.setAttribute("aria-pressed", String(!shown));
    this.setAttribute("aria-label", shown ? "Show password" : "Hide password");
    this.innerHTML = '<i data-lucide="' + (shown ? "eye" : "eye-off") + '"></i>';
    window.lucide.createIcons();
  });

  /* strength meter */
  var levels = [
    { label: "Too short", color: "var(--error)" },
    { label: "Weak", color: "var(--error)" },
    { label: "Okay", color: "var(--warning)" },
    { label: "Good", color: "var(--info)" },
    { label: "Strong", color: "var(--success)" },
  ];
  function score(pw) {
    if (pw.length < 8) return 0;
    var s = 1;
    if (pw.length >= 12) s++;
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw) && /\d/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return Math.min(s, 4);
  }
  $("password").addEventListener("input", function () {
    if (mode !== "signup") return;
    var v = this.value;
    var s = v ? score(v) : -1;
    var bars = $("strength").querySelectorAll(".meter i");
    bars.forEach(function (b, i) {
      b.style.background = s > 0 && i < s ? levels[s].color : "";
    });
    $("meter-label").textContent = s < 0 ? "" : levels[s].label;
    if (this.getAttribute("aria-invalid")) checkPassword();
  });

  /* inline validation on blur */
  $("email").addEventListener("blur", function () {
    if (this.value) checkEmail(this, "email-msg");
  });
  $("forgot-email").addEventListener("blur", function () {
    if (this.value) checkEmail(this, "forgot-msg");
  });

  /* mock submit: no network call, just a believable loading state */
  function fakeRequest(button, label, done) {
    var span = button.querySelector("span");
    button.disabled = true;
    span.textContent = "One moment";
    setTimeout(function () {
      button.disabled = false;
      span.textContent = label;
      done();
    }, 900);
  }

  $("auth-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var ok = [checkName(), checkEmail($("email"), "email-msg"), checkPassword(), checkTerms()].every(Boolean);
    if (!ok) return;
    var signup = mode === "signup";
    fakeRequest($("submit"), signup ? "Create account" : "Sign in", function () {
      $("done-title").textContent = signup ? "Account created" : "You're in";
      $("done-text").textContent = "This is a design mock, so nothing was saved. The console works without an account.";
      show("done");
      window.lucide.createIcons();
    });
  });

  document.querySelectorAll("[data-oauth]").forEach(function (b) {
    b.addEventListener("click", function () {
      var name = b.getAttribute("data-oauth");
      $("done-title").textContent = name + " sign-in isn't connected";
      $("done-text").textContent = "This is a design mock. The console works without an account.";
      show("done");
      window.lucide.createIcons();
    });
  });

  /* forgot password */
  $("to-forgot").addEventListener("click", function () {
    show("forgot");
    $("forgot-email").focus();
  });
  $("back-signin").addEventListener("click", function () {
    show("auth");
  });
  $("forgot-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (!checkEmail($("forgot-email"), "forgot-msg")) return;
    fakeRequest($("forgot-submit"), "Send reset link", function () {
      $("done-title").textContent = "Check your inbox";
      $("done-text").textContent = "In a real product the reset link would be on its way. Here, nothing was sent.";
      show("done");
      window.lucide.createIcons();
    });
  });
})();
