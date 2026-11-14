const log = document.getElementById("log");
const input = document.getElementById("input");
const send = document.getElementById("send");
const history = [];

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function add(html, cls = "msg") {
  const d = document.createElement("div");
  d.className = cls;
  d.innerHTML = html;
  log.querySelector(".empty")?.remove();
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}

fetch("/api/agents").then((r) => r.json()).then((a) => {
  const el = document.getElementById("roster");
  el.innerHTML = `<span class="chip">brain: ${esc(a.drex || "not configured")}</span>` +
    a.workers.map((w) => `<span class="chip" title="${esc(w.role)}">${esc(w.name)} · ${esc(w.model)}</span>`).join("") +
    (a.mock ? '<span class="chip">MOCK</span>' : "");
});

function scoreText(scores) {
  return Object.entries(scores || {})
    .sort((a, b) => b[1] - a[1])
    .map(([n, s]) => `${esc(n)} ${s}`)
    .join(" · ");
}

function render(e, state) {
  switch (e.type) {
    case "reply":
      add(esc(e.text), "msg drex");
      history.push({ role: "assistant", content: e.text });
      break;
    case "status":
      state.status = state.status || add("", "msg status");
      state.status.textContent = e.text;
      break;
    case "decision": {
      const label = e.index === 0 ? "Plan" : `Step ${e.index}: ${esc(e.stage)}`;
      const line = add(
        `<span class="lbl">${label}</span> <span class="arrow">chose</span> <strong>${esc(e.winner)}</strong>` +
        `<span class="sc">${scoreText(e.scores)}</span><span class="state"></span>`, "msg pick");
      state.lines = state.lines || {};
      state.lines[e.index] = line;
      break;
    }
    case "steps":
      add(`<strong>Plan by ${esc(e.planner)}</strong><ol>${e.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`, "msg steps");
      break;
    case "step_result": {
      const line = state.lines?.[e.index];
      if (line) {
        const note = e.agent !== e.winner ? ` (${esc(e.winner)} failed, done by ${esc(e.agent)})` : "";
        line.querySelector(".state").innerHTML = ` ✓${note}`;
        line.classList.add("ok");
      }
      break;
    }
    case "done":
      state.status?.remove();
      add(`${esc(e.text)} <a class="dl" href="${esc(e.zip)}" download>Download ${esc(e.name)}</a>`, "msg drex");
      break;
    case "error":
      add(esc(e.text), "msg drex err");
      break;
  }
}

async function submit(text) {
  add(esc(text), "msg user");
  send.disabled = true;
  const state = {};
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: history.slice(-10) }),
    });
    history.push({ role: "user", content: text });
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (line) render(JSON.parse(line), state);
      }
    }
  } catch (err) {
    add(esc("Connection problem: " + err.message), "msg drex err");
  } finally {
    send.disabled = false;
    input.focus();
  }
}

document.getElementById("composer").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const t = input.value.trim();
  if (!t) return;
  input.value = "";
  input.style.height = "auto";
  submit(t);
});
input.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); document.getElementById("composer").requestSubmit(); }
});
input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = input.scrollHeight + "px"; });