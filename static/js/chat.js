/* Ask Ukulima chatbox: renders replies safely, streams them in, keeps history
   for the tab, and wires suggestion chips + quick prompts to the chat API. */
(function () {
  "use strict";
  var META = window.CHAT_META || {};
  var log = document.getElementById("chatLog");
  var form = document.getElementById("chatForm");
  var input = document.getElementById("chatInput");
  var sendBtn = document.getElementById("sendBtn");
  var charCount = document.getElementById("charCount");
  var quickRow = document.getElementById("quickRow");
  if (!log || !form || !input) return;

  var STORE = "ukulima-chat-v1";
  var busy = false;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var history = [];
  try { history = JSON.parse(sessionStorage.getItem(STORE) || "[]"); } catch (e) { history = []; }

  /* ---- markdown-lite (escape first, then format; only internal links) ---- */
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function inline(s) {
    return esc(s)
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
      .replace(/(^|[\s(])\*([^*]+)\*(?=[\s).,!?]|$)/g, "$1<i>$2</i>")
      .replace(/\[([^\]]+)\]\((\/[a-z0-9\/_-]*)\)/gi, '<a href="$2">$1</a>');
  }
  function mdLite(text) {
    var lines = String(text).split(/\r?\n/), html = [], list = null;
    function closeList() { if (list) { html.push("</" + list + ">"); list = null; } }
    lines.forEach(function (ln) {
      var bullet = ln.match(/^\s*[-•]\s+(.*)$/);
      var numbered = ln.match(/^\s*\d+[.)]\s+(.*)$/);
      if (bullet) {
        if (list !== "ul") { closeList(); html.push("<ul>"); list = "ul"; }
        html.push("<li>" + inline(bullet[1]) + "</li>");
      } else if (numbered) {
        if (list !== "ol") { closeList(); html.push("<ol>"); list = "ol"; }
        html.push("<li>" + inline(numbered[1]) + "</li>");
      } else if (ln.trim() === "") {
        closeList();
      } else {
        closeList(); html.push("<p>" + inline(ln) + "</p>");
      }
    });
    closeList();
    return html.join("");
  }

  /* ---- message DOM ---- */
  function scrollDown() { log.scrollTop = log.scrollHeight; }
  function avatarEl(role) {
    var a = document.createElement("span");
    a.className = "m-avatar " + (role === "me" ? "me" : "bot");
    if (role === "me") {
      a.textContent = (META.name || "U").charAt(0).toUpperCase();
    } else {
      var img = document.createElement("img");
      img.src = "/static/img/logo.svg"; img.alt = "";
      a.appendChild(img);
    }
    return a;
  }
  function makeMsg(role) {
    var wrap = document.createElement("div");
    wrap.className = "m-row " + role;
    wrap.appendChild(avatarEl(role));
    var bubble = document.createElement("div");
    bubble.className = "m-bubble";
    wrap.appendChild(bubble);
    log.appendChild(wrap);
    scrollDown();
    return { wrap: wrap, bubble: bubble };
  }
  function addExtras(msg, data) {
    if (data.related && data.related.length) {
      var rel = document.createElement("div");
      rel.className = "m-related";
      var label = document.createElement("span");
      label.textContent = (META.related || "Library") + ":";
      rel.appendChild(label);
      data.related.forEach(function (k) {
        var a = document.createElement("a");
        a.className = "chip tiny";
        a.href = "/knowledge/" + encodeURIComponent(k.id);
        a.textContent = "📖 " + k.name;
        rel.appendChild(a);
      });
      msg.wrap.appendChild(rel);
    }
    if (data.suggestions && data.suggestions.length) {
      var sug = document.createElement("div");
      sug.className = "m-suggest";
      data.suggestions.slice(0, 3).forEach(function (s) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "chip"; b.textContent = s;
        b.addEventListener("click", function () { send(s); });
        sug.appendChild(b);
      });
      msg.wrap.appendChild(sug);
    }
    scrollDown();
  }
  function renderStored(m) {
    var msg = makeMsg(m.role);
    msg.bubble.innerHTML = mdLite(m.text);
    addExtras(msg, m);
  }

  /* ---- typing + streaming ---- */
  function showTyping() {
    var msg = makeMsg("bot");
    msg.bubble.classList.add("typing-bubble");
    msg.bubble.innerHTML = '<span class="typing"><i></i><i></i><i></i></span> ' + esc(META.thinking || "Thinking…");
    return msg;
  }
  function streamText(msg, text, done) {
    if (reduceMotion || text.length < 80) {
      msg.bubble.classList.remove("typing-bubble");
      msg.bubble.innerHTML = mdLite(text);
      scrollDown(); done(); return;
    }
    msg.bubble.classList.remove("typing-bubble");
    msg.bubble.classList.add("streaming");
    var duration = Math.min(2200, Math.max(450, text.length * 6));
    var start = performance.now();
    var timer = setInterval(function () {
      var t = Math.min(1, (performance.now() - start) / duration);
      var i = Math.ceil(text.length * t);
      msg.bubble.textContent = text.slice(0, i);
      scrollDown();
      if (t >= 1) {
        clearInterval(timer);
        msg.bubble.classList.remove("streaming");
        msg.bubble.innerHTML = mdLite(text);
        scrollDown(); done();
      }
    }, 14);
  }

  function setBusy(v) {
    busy = v;
    sendBtn.disabled = v;
    input.disabled = v;
    sendBtn.classList.toggle("loading", v);
  }
  function persist() {
    try { sessionStorage.setItem(STORE, JSON.stringify(history.slice(-40))); } catch (e) {}
  }

  /* ---- send ---- */
  function send(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    var mine = makeMsg("me");
    mine.bubble.textContent = text;
    history.push({ role: "me", text: text });
    persist();
    input.value = ""; autoGrow(); updateCount();
    setBusy(true);
    var typing = showTyping();

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF": document.body.dataset.csrf || "" },
      body: JSON.stringify({ question: text })
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        streamText(typing, data.answer || "", function () {
          addExtras(typing, data);
          history.push({ role: "bot", text: data.answer || "", related: data.related || [], suggestions: data.suggestions || [] });
          persist();
          setBusy(false);
          input.focus();
        });
      })
      .catch(function () {
        typing.bubble.classList.remove("typing-bubble");
        typing.bubble.innerHTML = "<p>⚠️ " + esc(META.error || "Could not reach the assistant.") + "</p>";
        var retry = document.createElement("button");
        retry.type = "button"; retry.className = "chip";
        retry.textContent = "↻ " + (META.retry || "Retry");
        retry.addEventListener("click", function () {
          typing.wrap.remove();
          history.pop();
          setBusy(false);
          send(text);
        });
        typing.wrap.appendChild(retry);
        scrollDown();
        setBusy(false);
      });
  }

  /* ---- composer ---- */
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  }
  function updateCount() { charCount.textContent = input.value.length + " / 600"; }
  input.addEventListener("input", function () { autoGrow(); updateCount(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", function (e) { e.preventDefault(); send(input.value); });

  quickRow.querySelectorAll(".chip").forEach(function (b) {
    b.addEventListener("click", function () { send(b.textContent); });
  });

  document.getElementById("newChat").addEventListener("click", function () {
    if (busy) return;
    history = [];
    try { sessionStorage.removeItem(STORE); } catch (e) {}
    log.innerHTML = "";
    welcome();
    input.focus();
  });

  /* ---- boot ---- */
  function welcome() {
    var countyPhrase = META.county
      ? (META.lang === "sw" ? " Naona unalima katika **" + META.county + "**." : " I see you farm in **" + META.county + "**.")
      : "";
    var text = (META.welcome || "Hello! 🌱 I'm Ukulima. Tell me your crop and what you see, and I'll suggest what it is and how to control it safely.")
      .replace(/\{name\}/g, META.name || "rafiki").replace(/\{county\}/g, countyPhrase);
    var chips = [];
    quickRow.querySelectorAll(".chip").forEach(function (b) { chips.push(b.textContent); });
    var msg = makeMsg("bot");
    msg.bubble.innerHTML = mdLite(text);
    addExtras(msg, { suggestions: chips });
    history.push({ role: "bot", text: text, suggestions: chips });
    persist();
  }
  if (history.length) {
    history.forEach(renderStored);
  } else {
    welcome();
  }
  updateCount();
})();