// Unified Inbox UI (PRD-006 B). Skeleton qua adapter; mock; không credential.
import { ADAPTERS, loadAll } from "./adapters.js";

const state = { all: [], filter: "all" };
const root = document.getElementById("app");

function chips() {
  const items = [{ key: "all", label: "Tất cả", configured: true }, ...ADAPTERS];
  return items.map((a) => {
    const active = a.key === state.filter ? " active" : "";
    const dot = a.configured === false ? ' <span class="muted">(chưa nối)</span>' : "";
    return `<button class="chip${active}" data-k="${a.key}">${a.label}${dot}</button>`;
  }).join("");
}

function list() {
  const msgs = state.filter === "all" ? state.all : state.all.filter((m) => m.channel === state.filter);
  if (!msgs.length) return '<p class="muted">Chưa có tin nhắn.</p>';
  return msgs.map((m) => `<div class="msg">
    <span class="msg-ch">${m.channel}</span>
    <b>${m.from}</b>: ${m.text}
    <span class="muted">${new Date(m.ts).toLocaleString("vi-VN")}</span>
  </div>`).join("");
}

function view() {
  root.innerHTML = `
    <nav class="nav"><span class="brand">OMI ▸ Inbox</span><a href="../index.html">Dashboard</a></nav>
    <main class="content">
      <div class="banner">Unified Inbox (skeleton) — placeholder qua adapter, chưa nối credential.</div>
      <div class="chips">${chips()}</div>
      <div class="inbox-list">${list()}</div>
    </main>`;
  document.querySelectorAll(".chip").forEach((b) => {
    b.onclick = () => { state.filter = b.dataset.k; view(); };
  });
}

async function boot() { state.all = await loadAll(); view(); }
boot();
