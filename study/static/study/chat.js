(function () {
  const C = window.CHAT;
  const log = document.getElementById("log");
  const text = document.getElementById("text");
  const send = document.getElementById("send");
  const status = document.getElementById("status");
  const composer = document.getElementById("composer");
  const next = document.getElementById("next");
  const donemsg = document.getElementById("donemsg");
  const timerEl = document.getElementById("timer");
  const stopBtn = document.getElementById("stop");
  let sent = C.sent, open = C.open, busy = false, timerId = null;

  function add(role, t, cls) {
    const d = document.createElement("div");
    d.className = "msg " + role + (cls ? " " + cls : "");
    d.textContent = t;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  function remaining() { return Math.max(C.maxMessages - sent, 0); }
  function updateStatus(msg) {
    if (msg) { status.textContent = msg; return; }
    status.textContent = open && C.mode !== "probe" ? remaining() + " message(s) left in this round" : "";
  }
  function finish(reason) {
    open = false;
    composer.classList.add("hidden");
    next.classList.remove("hidden");
    if (timerId) clearInterval(timerId);
    const msgs = { agreed: C.partner + " agreed. This round has ended.", timeout: "Time is up. This round has ended.",
                   max_messages: "You reached the message limit. This round has ended.", probe_done: "This conversation has ended.",
                   skipped: "You stopped this round. That is completely fine." };
    const sw = document.getElementById("stopwrap"); if (sw) sw.classList.add("hidden");
    donemsg.textContent = msgs[reason] || "This conversation has ended.";
    updateStatus("");
  }
  async function post(url, body) {
    const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": C.csrf }, body: JSON.stringify(body || {}) });
    return r.json();
  }
  async function submit() {
    const t = text.value.trim();
    if (!t || busy || !open) return;
    busy = true; send.disabled = true; text.value = "";
    add("learner", t);
    sent += 1;
    const typing = add("drlee", C.partner + " is typing...", "typing");
    try {
      const res = await post(C.url, { text: t });
      typing.remove();
      if (res.error) {
        log.lastChild && log.lastChild.classList.contains("learner") && log.lastChild.remove();
        sent -= 1;
        text.value = res.restore || t;
        updateStatus(res.error);
      } else {
        if (res.reply) add("drlee", res.reply);
        if (res.done) finish(res.reason || (C.mode === "probe" ? "probe_done" : ""));
        else updateStatus();
      }
    } catch (e) {
      typing.remove();
      updateStatus("Connection problem. Please try again.");
      text.value = t;
    }
    busy = false; send.disabled = false; text.focus();
  }
  send.addEventListener("click", submit);
  // Stopping a round needs two clicks, so it cannot happen by accident (no browser dialogs).
  if (stopBtn) stopBtn.addEventListener("click", async () => {
    if (!open || busy) return;
    if (!stopBtn.dataset.armed) { stopBtn.dataset.armed = "1"; stopBtn.textContent = "Click again to stop this round"; return; }
    await post(C.timeoutUrl, { reason: "skipped" });
    finish("skipped");
  });
  text.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } });

  if (timerEl && open) {
    const total = parseInt(timerEl.dataset.seconds, 10);
    const started = parseInt(timerEl.dataset.started, 10) * 1000;
    const tick = async () => {
      const left = Math.max(0, Math.round(total - (Date.now() - started) / 1000));
      timerEl.textContent = Math.floor(left / 60) + ":" + String(left % 60).padStart(2, "0");
      if (left <= 0 && open) {
        clearInterval(timerId);
        if (busy) { setTimeout(tick, 500); return; }
        await post(C.timeoutUrl, {});
        finish("timeout");
      }
    };
    timerId = setInterval(tick, 1000); tick();
  }
  if (!open) { finish(""); } else { updateStatus(); text.focus(); }
})();
