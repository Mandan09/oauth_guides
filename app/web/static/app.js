const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, cls, html) => Object.assign(document.createElement(tag), { className: cls || "", innerHTML: html || "" });
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const rich = (s) => esc(s)
  .replace(/^#{1,4}\s+(.+)$/gm, "<b>$1</b>").replace(/^-{3,}$/gm, "<hr>")
  .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  .replace(/\[(https?:\/\/[^\]\s]+)\]/g, (_, u) => `<a class="src" href="${u}" target="_blank" rel="noopener">${host(u)}</a>`)
  .replace(/(^|[\s(])(https?:\/\/[^\s<)\]]+)/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>')
  .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/^\s*[*-]\s+/gm, "• ").replace(/\*([^*\n]+)\*/g, "<i>$1</i>")
  .replace(/`([^`\n]+)`/g, "<code>$1</code>").replace(/\n/g, "<br>");
const clock = (iso) => { const d = new Date(iso || Date.now()); return `<time class="at" title="${d.toLocaleString()}">${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>`; };
const kTokens = (u) => u ? ` · ${u.searches} searches · ${((u.input_tokens + u.output_tokens) / 1000).toFixed(1)}k tokens` : "";
const host = (url) => { try { return new URL(url.includes("//") ? url : `https://${url}`).hostname.replace(/^www\./, ""); } catch { return url; } };
const icon = (domain, size = 14) => `<img class="fav" src="https://www.google.com/s2/favicons?domain=${esc(domain)}&sz=32" alt="" width="${size}" height="${size}">`;
const KIND = { search: "🔎", read: "📄", probe: "🧪", write: "✍️", tool: "⚙️" };
const uuid = () => crypto.randomUUID();
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
};

// ---------- guide interactions (canvas and standalone page) ----------
function initGuide(root) {
  const guide = $(".guide", root);
  if (!guide) return;
  root.querySelectorAll(".filters").forEach((bar) => bar.addEventListener("click", (e) => {
    const value = e.target.dataset.value;
    if (!value) return;
    bar.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === e.target));
    const attr = bar.dataset.filter;
    const scope = attr === "owner" ? $(".stages", guide) : bar.parentElement;
    scope.querySelectorAll(`[data-${attr}]`).forEach((li) => (li.hidden = value !== "all" && li.dataset[attr] !== value));
  }));
  // Progress checkboxes are remembered per guide in this browser
  const key = `progress:${guide.dataset.slug}`;
  const done = JSON.parse(store.get(key) || "[]");
  guide.querySelectorAll("[data-step]").forEach((box) => {
    box.checked = done.includes(box.dataset.step);
    box.addEventListener("change", () =>
      store.set(key, JSON.stringify([...guide.querySelectorAll("[data-step]:checked")].map((b) => b.dataset.step))));
  });
}

if (!$("#composer")) {
  initGuide(document);
  if (new URLSearchParams(location.search).get("print")) setTimeout(print, 300);
}

// ---------- canvas ----------
let openSlug = null;

async function openCanvas(slug) {
  const res = await fetch(`/g/${slug}/fragment`);
  if (!res.ok) return;
  $("#canvas-body").innerHTML = await res.text();
  $("#canvas-title").textContent = $(".guide", $("#canvas-body")).dataset.title + " · OAuth guide";
  $("#canvas").hidden = false;
  $("#layout").classList.add("with-canvas");
  $("#canvas-body").scrollTop = 0;
  openSlug = slug;
  initGuide($("#canvas-body"));
}

// While the writer works, the canvas shows the guide itself being written (rendered server-side from partial JSON).
function showWriting(title, html) {
  const body = $("#canvas-body");
  const follow = body.scrollHeight - body.scrollTop - body.clientHeight < 80;  // keep following unless the user scrolled up
  if (openSlug !== null || $("#canvas").hidden) {
    openSlug = null;
    $("#canvas-title").textContent = `${title} · writing…`;
    $("#canvas").hidden = false;
    $("#layout").classList.add("with-canvas");
  }
  body.innerHTML = `<p class="draft-badge"><span class="spin inline"></span>Writing the guide…</p>${html}<span class="caret"></span>`;
  if (follow) body.scrollTop = body.scrollHeight;
}

function closeCanvas() {
  $("#canvas").hidden = true;
  $("#layout").classList.remove("with-canvas", "canvas-full");
}

async function exportGuide(fmt) {
  $("#export-menu").hidden = true;
  if (!openSlug) return flash($("#export-btn"), "Available when the guide is ready");
  if (fmt === "copy-md") {
    await navigator.clipboard.writeText(await (await fetch(`/g/${openSlug}.md`)).text());
    return flash($("#export-btn"), "Copied");
  }
  location.href = `/g/${openSlug}.${fmt}`;
}

function flash(btn, text) {
  const old = btn.textContent;
  btn.textContent = text;
  setTimeout(() => (btn.textContent = old), 1500);
}

// ---------- chats: saved per anonymous browser id ----------
const clientId = store.get("client_id") || uuid();
store.set("client_id", clientId);
let chat = { id: uuid(), title: "", items: [] };

let saving = Promise.resolve();
function saveChat(c = chat) {
  if (!c.items.length) return;
  // saves run one at a time, so a new chat is never created twice
  saving = saving.then(() => fetch(`/api/chats/${c.id}`, {
    method: "PUT", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, title: c.title, items: c.items }),
  })).then(loadChatList, () => {});
}

async function loadChatList() {
  const res = await fetch(`/api/chats?client_id=${clientId}`);
  if (!res.ok) return;
  const chats = await res.json();
  const list = $("#chat-list");
  list.innerHTML = chats.length ? "" : `<li class="muted small empty">No chats yet</li>`;
  for (const c of chats) {
    const li = el("li", c.id === chat.id ? "active" : "",
      `<button class="chat-link">${esc(c.title)}</button><button class="del" title="Delete chat" aria-label="Delete chat">✕</button>`);
    $(".chat-link", li).addEventListener("click", () => openChat(c.id));
    $(".del", li).addEventListener("click", async () => {
      await fetch(`/api/chats/${c.id}?client_id=${clientId}`, { method: "DELETE" });
      if (c.id === chat.id) newChat(); else loadChatList();
    });
    list.appendChild(li);
  }
}

function resetThread() {
  $("#thread").innerHTML = "";
  closeCanvas();
}

function newChat() {
  chat = { id: uuid(), title: "", items: [] };
  history.replaceState(null, "", "/");
  location.reload();
}

async function openChat(id) {
  const res = await fetch(`/api/chats/${id}?client_id=${clientId}`);
  if (!res.ok) return newChat();
  chat = await res.json();
  resetThread();
  $("#chat-title").textContent = chat.title;
  history.replaceState(null, "", `/?chat=${id}`);
  chat.items.forEach((item) => render(item, { replay: true }));
  loadChatList();
  $("#layout").classList.remove("show-sidebar");
}

// Every async flow passes the chat it started in, so a reply never lands in a chat the user switched to.
function push(item, owner = chat) {
  item.at ||= new Date().toISOString();
  if (!owner.title && item.type === "user") owner.title = item.text.slice(0, 60);
  owner.items.push(item);
  if (owner === chat) {
    $("#chat-title").textContent = chat.title;
    history.replaceState(null, "", `/?chat=${chat.id}`);
    render(item, {});
  }
  saveChat(owner);
}

// ---------- rendering ----------
// Draw into the thread only if `owner` is still the open chat; otherwise build a detached element.
function messageFor(owner, role, html) {
  return owner === chat ? addMessage(role, html) : el("div", `msg ${role}`, html);
}

function addMessage(role, html, at) {
  $("#welcome")?.remove();
  const msg = el("div", `msg ${role}`, html + (at ? clock(at) : ""));
  $("#thread").appendChild(msg);
  msg.scrollIntoView({ behavior: "smooth", block: "end" });
  return msg;
}

function render(item, opts) {
  if (item.type === "user") return addMessage("user", rich(item.text), item.at);
  if (item.type === "error") return addMessage("assistant", `<p class="error">${esc(item.text)}</p>`, item.at);
  if (item.type === "answer") {
    const meta = item.meta || (item.usage ? `Answered${kTokens(item.usage)} (this chat so far)` : "");
    return addMessage("assistant", `<div class="answer">${rich(item.text)}</div><p class="muted small">${esc(meta)}</p>`, item.at);
  }
  if (item.type === "reply") return renderReply(item, opts);
  if (item.type === "run") return followRun(item, opts, chat);
  if (item.type === "guide") {
    const msg = addMessage("assistant", `<p>${item.intro}</p>`, item.at);
    msg.insertBefore(artifactCard(item), $(".at", msg));
    if (!opts.replay) openCanvas(item.slug);  // saved chats open as a conversation; the card opens the guide
  }
}

function artifactCard(g) {
  const card = el("button", "artifact", `
    ${icon(host(g.website || g.title), 28)}
    <span><strong>${esc(g.title)} OAuth setup & approval guide</strong>
    <span class="muted small">Document · <span class="badge ${esc(g.difficulty)}">${esc(g.difficulty)}</span> · approval wait: ${esc(g.wait)}</span></span>
    <span class="open">Open</span>`);
  card.addEventListener("click", () => openCanvas(g.slug));
  return card;
}

function renderReply(item, { replay }) {
  const msg = addMessage("assistant", item.text ? `<p>${rich(item.text)}</p>` : "", item.at);
  if (item.use_case) msg.appendChild(el("p", "muted small", `Your agent needs to: ${esc(item.use_case)}`));
  if (!item.candidates?.length) return;
  const list = el("div", "candidates");
  item.candidates.forEach((c, i) => {
    const card = el("div", "candidate", `
      ${icon(host(c.website), 20)}
      <div><strong>${esc(c.name)}</strong> ${i === 0 ? '<span class="pill">Recommended</span>' : ""}<br><span class="muted small">${esc(c.why)}</span></div>
      <button class="ghost-btn">${c.slug ? "Open guide" : i === 0 && !replay ? "Researching ↓" : "Get guide"}</button>`);
    $("button", card).addEventListener("click", () => (c.slug ? openCanvas(c.slug) : guideFor(c.name, item.use_case)));
    list.appendChild(card);
  });
  msg.appendChild(list);
}

// ---------- asking ----------
function showGuideItem(g, intro, owner = chat) {
  push({ type: "guide", slug: g.slug, title: g.app || g.title, difficulty: g.difficulty,
         wait: g.approval_wait, website: g.website, intro }, owner);
}

async function fromStart(started, name, owner) {
  if (started.error) return push({ type: "error", text: started.error }, owner);
  if (started.slug) {
    const g = await (await fetch(`/api/guides/${started.slug}`)).json();
    return showGuideItem(g, `<b>${esc(g.app)}</b> is already in the library. Here's the guide.`, owner);
  }
  if (started.run_id) push({ type: "run", run_id: started.run_id, query: name }, owner);
}

async function ask(message) {
  const owner = chat, slug = openSlug || "";
  push({ type: "user", text: message }, owner);
  const thinking = messageFor(owner, "assistant", `<p class="muted"><span class="spin inline"></span> Reading your request…</p>`);
  const res = await fetch("/api/runs/ask", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, slug }),
  });
  thinking.remove();
  const body = await res.json().catch(() => ({}));
  if (!res.ok) return push({ type: "error", text: body.detail?.[0]?.msg || body.detail || "Something went wrong." }, owner);
  if (body.kind === "followup") return streamAnswer(message, owner, slug);
  if (body.reply || body.candidates?.length) push({ type: "reply", text: body.reply, use_case: body.use_case, candidates: body.candidates }, owner);
  await fromStart(body, body.app, owner);
  // a library guide may predate this use case, so map the developer's needs to scopes right away
  if (body.slug && body.use_case) streamAnswer(`Which OAuth scopes and approvals does my agent need to: ${body.use_case}`, owner, body.slug);
}

// Reads a POSTed SSE response (EventSource only supports GET).
async function* readSSE(res) {
  const reader = res.body.getReader(), decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const event = /^event: (.*)$/m.exec(raw)?.[1], data = /^data: (.*)$/m.exec(raw)?.[1];
      if (event && data) yield [event, JSON.parse(data)];
    }
  }
}

// Follow-up answers stream token by token, grounded in the guide that is open.
async function streamAnswer(message, owner, slug) {
  const msg = messageFor(owner, "assistant", `<ul class="answer-steps"></ul><div class="answer typing"><span class="muted">Thinking…</span></div>`);
  const box = $(".answer", msg), list = $(".answer-steps", msg), stepEls = {};
  let text = "", usage = null;
  const res = await fetch(`/api/chats/${owner.id}/answer`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, message, slug }),
  });
  for await (const [event, d] of readSSE(res)) {
    if (event === "token") { text += d.delta; box.textContent = text; }
    else if (event === "step" && d.status === "started") {
      const fav = d.url ? icon(host(d.url)) : `<span class="kind">${KIND[d.kind] || "•"}</span>`;
      stepEls[d.id] = list.appendChild(el("li", "step running", `${fav}<span class="step-text">${esc(d.text)}</span><span class="result muted small"></span>`));
    } else if (event === "step" && stepEls[d.id]) {
      stepEls[d.id].classList.replace("running", "done");
      $(".result", stepEls[d.id]).innerHTML = (d.domains || []).map((x) => icon(x)).join("") + " " + esc(d.result || "");
    } else if (event === "done") usage = d.usage;
    else if (event === "error") text = text || d.message;
  }
  box.classList.remove("typing");
  box.innerHTML = rich(text);
  const meta = usage ? `Answered from ${slug ? "the open guide" : "general knowledge"}${kTokens(usage)} (this chat so far)` : "";
  msg.insertAdjacentHTML("beforeend", `<p class="muted small">${esc(meta)}</p>${clock()}`);
  owner.items.push({ type: "answer", text, meta, at: new Date().toISOString() });  // the server already saved it
}

async function guideFor(name, useCase) {
  const owner = chat;
  push({ type: "user", text: `Show me the guide for ${name}` }, owner);
  const res = await fetch("/api/runs", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: name, use_case: useCase || "" }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) return push({ type: "error", text: body.detail?.[0]?.msg || body.detail || "Something went wrong." }, owner);
  await fromStart(body, name, owner);
}

// Renders a run as one chronological feed, like Claude: narration, searches with results, reads, probes.
function followRun(item, { replay }, owner) {
  const msg = addMessage("assistant", `
    <div class="run">
      <button class="run-head"><span class="spin"></span><span class="run-title">Researching ${esc(item.query || "app")}</span>
      <span class="muted small timer"></span><span class="chev">▾</span></button>
      <p class="live-status muted small">Starting…</p>
      <div class="progress-row"><div class="progress"><i></i></div><span class="muted small eta">Usually 2–3 minutes</span>
        <button class="ghost-btn stop">Stop</button></div>
      <p class="muted small hint">You can keep asking questions while this runs. The guide opens on the right as it is written.</p>
      <ol class="feed"></ol>
    </div>`);
  const run = $(".run", msg), feed = $(".feed", msg);
  $(".run-head", msg).addEventListener("click", () => run.classList.toggle("open"));
  const t0 = Date.now();
  const live = !replay && owner === chat;
  // progress: identify 15%, three researchers 60% (by steps, budget-weighted), writer 22% by section, check 3%
  const progress = { resolver: 0, review_researcher: 0, oauth_researcher: 0, prober: 0, writer: 0, validator: 0 };
  const WEIGHT = { resolver: 15, review_researcher: 20, oauth_researcher: 20, prober: 20, writer: 22, validator: 3 };
  const BUDGET = { review_researcher: 7, oauth_researcher: 6, prober: 6, writer: 8 };
  const stepsBy = {};
  const pct = () => Math.min(99, Math.round(Object.keys(WEIGHT).reduce((sum, k) => sum + WEIGHT[k] * progress[k], 0)));
  const bump = (stage, value) => { if (stage in progress) progress[stage] = Math.max(progress[stage], Math.min(value, 1)); };
  const tick = () => {
    const secs = Math.round((Date.now() - t0) / 1000), p = pct();
    $(".timer", msg).textContent = `${secs}s`;
    $(".progress i", msg).style.width = `${p}%`;
    if (p >= 15) $(".eta", msg).textContent = `${p}% · about ${Math.max(10, Math.round(secs * (100 - p) / p / 10) * 10)}s left`;
    if (live) document.title = `${p}% · Researching ${item.query || ""}`;
  };
  const timer = setInterval(tick, 1000);
  $(".stop", msg).addEventListener("click", (e) => { e.target.disabled = true; fetch(`/api/runs/${item.run_id}/cancel`, { method: "POST" }); });
  const lanes = {}, markers = {}, notes = {}, stepEls = {};
  const status = (text) => text && ($(".live-status", msg).textContent = text);
  let steps = 0;
  const lane = (stage) => `<span class="lane lane-${esc(stage)}">${esc(lanes[stage] || "")}</span>`;
  const add = (li) => { feed.appendChild(li); if (run.classList.contains("open") && !replay) li.scrollIntoView({ block: "nearest" }); return li; };
  const source = new EventSource(`/api/runs/${item.run_id}/events`);

  source.addEventListener("stage", (e) => {
    const d = JSON.parse(e.data);
    if (d.status === "started") {
      lanes[d.id] = d.lane || "";
      markers[d.id] = add(el("li", "marker running", `<span class="state"></span>${esc(d.label)}`));
      status(`${d.label}…`);
    } else {
      markers[d.id]?.classList.replace("running", "done");
      bump(d.id, 1);
    }
  });

  source.addEventListener("text", (e) => {
    const d = JSON.parse(e.data);
    notes[d.id] ??= add(el("li", "note typing", `${lane(d.stage)}<span class="note-text"></span>`));
    $(".note-text", notes[d.id]).textContent += d.delta;
    status($(".note-text", notes[d.id]).textContent.split(/(?<=[.!?])\s/)[0].slice(0, 140));
  });

  source.addEventListener("text_end", (e) => {
    const d = JSON.parse(e.data), note = notes[d.id];
    if (!note) return;
    note.classList.remove("typing");
    const text = $(".note-text", note), raw = text.textContent;
    text.innerHTML = rich(raw);
    if (d.final) {
      note.classList.add("findings");
      note.addEventListener("click", () => note.classList.toggle("expanded"));
    }
  });

  source.addEventListener("step", (e) => {
    const d = JSON.parse(e.data);
    if (d.status === "started") {
      steps++;
      stepsBy[d.stage] = (stepsBy[d.stage] || 0) + 1;
      bump(d.stage, stepsBy[d.stage] / (BUDGET[d.stage] || 4) * 0.9);
      const fav = d.url ? icon(host(d.url)) : `<span class="kind">${KIND[d.kind] || "•"}</span>`;
      stepEls[d.id] = add(el("li", "step running", `${lane(d.stage)}${fav}<span class="step-text">${esc(d.text)}</span><span class="result muted small"></span>`));
      $(".run-title", msg).textContent = `Researching ${item.query || ""} · ${steps} steps`;
      status(d.text);
      return;
    }
    const li = stepEls[d.id];
    if (!li) return;
    if (d.result?.startsWith("skipped: Tool budget")) return li.remove(); // over-budget calls are noise
    li.classList.replace("running", "done");
    $(".result", li).innerHTML = (d.domains || []).map((x) => icon(x)).join("") + " " + esc(d.result || "");
    if (d.links?.length) {
      const links = el("ul", "links", d.links.map((l) =>
        `<li>${icon(host(l.url))}<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.title)}</a><span class="muted small">${esc(host(l.url))}</span></li>`).join(""));
      links.hidden = true;
      li.after(links);
      li.classList.add("expandable");
      li.addEventListener("click", () => (links.hidden = !links.hidden));
    }
  });

  const finish = (text) => {
    clearInterval(timer);
    $(".progress-row", msg)?.remove();
    $(".hint", msg)?.remove();
    $(".live-status", msg)?.remove();
    source.close();
    run.classList.remove("open");
    $(".spin", msg).className = "state-done";
    $(".run-title", msg).textContent = text;
    $(".timer", msg).textContent = "";
  };

  source.addEventListener("draft", (e) => {
    bump("writer", 0.5);
    if (live && owner === chat) showWriting(item.query || "Guide", JSON.parse(e.data).html);
  });

  source.addEventListener("done", (e) => {
    const d = JSON.parse(e.data);
    finish(`Researched ${d.title} · ${steps} steps${kTokens(d.usage)}${d.seconds ? ` · ${d.seconds}s` : ""}`);
    if (live && document.hidden) document.title = `✓ Guide ready · ${d.title}`;
    else document.title = "OAuth App Guides";
    // add the guide card unless this chat already has it (e.g. the user left before the run ended)
    if (!owner.items.some((i) => i.type === "guide" && i.slug === d.slug && i.at >= item.at))
      showGuideItem({ slug: d.slug, title: d.title, difficulty: d.difficulty, approval_wait: d.approval_wait },
      `Done. ${esc(d.headline || "")}`, owner);
  });

  source.addEventListener("error", (e) => {
    if (!e.data) return; // network blip: EventSource reconnects and resumes from the last id
    const d = JSON.parse(e.data);
    finish(d.finding ? "Research finished" : "Research stopped");
    document.title = "OAuth App Guides";
    if (!owner.items.some((i) => i.at > item.at && i.text === d.message))
      push(d.finding ? { type: "reply", text: d.message } : { type: "error", text: d.message }, owner);
  });
}

// ---------- wiring ----------
if ($("#composer")) {
  const input = $("#query");
  const grow = () => { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 220)}px`; };
  input.addEventListener("input", grow);
  $("#composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (q.length < 2) return;
    input.value = "";
    grow();
    ask(q);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#composer").requestSubmit(); }
  });
  document.querySelectorAll("[data-prompt]").forEach((b) => b.addEventListener("click", () => ask(b.dataset.prompt)));
  // the library just opens the guide; it does not add messages to a chat
  document.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => openCanvas(b.dataset.open)));
  $("#new-chat").addEventListener("click", newChat);
  const layout = $("#layout");
  $("#hide-sidebar").addEventListener("click", () => { layout.classList.remove("show-sidebar"); layout.classList.add("no-sidebar"); });
  $("#show-sidebar").addEventListener("click", () => { layout.classList.remove("no-sidebar"); layout.classList.add("show-sidebar"); });
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#sidebar, #show-sidebar") || e.target.closest("[data-open], .chat-link")) layout.classList.remove("show-sidebar");
  });
  document.addEventListener("visibilitychange", () => !document.hidden && document.title.startsWith("✓") && (document.title = "OAuth App Guides"));
  $("#close-canvas").addEventListener("click", closeCanvas);
  $("#full-canvas").addEventListener("click", () => layout.classList.toggle("canvas-full"));
  document.addEventListener("keydown", (e) => e.key === "Escape" && layout.classList.remove("canvas-full"));
  $("#copy-link").addEventListener("click", async (e) => {
    await navigator.clipboard.writeText(`${location.origin}/g/${openSlug}`);
    flash(e.target, "Copied");
  });
  $("#export-btn").addEventListener("click", () => ($("#export-menu").hidden = !$("#export-menu").hidden));
  $("#export-menu").addEventListener("click", (e) => e.target.dataset.fmt && exportGuide(e.target.dataset.fmt));

  const params = new URLSearchParams(location.search);
  if (params.get("chat")) openChat(params.get("chat"));
  else loadChatList();
  if (params.get("run")) push({ type: "run", run_id: params.get("run"), query: "" });
  if (params.get("g")) openCanvas(params.get("g"));
}
