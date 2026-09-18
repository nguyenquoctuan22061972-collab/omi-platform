// Contacts UI (PRD-006 A): list, detail, search, filter, pagination. Vanilla JS.
import { getContacts, applySearchFilter, paginate } from "./api.js";

const state = { all: [], q: "", source: "", page: 1, size: 5, selected: null, degraded: false };
const root = document.getElementById("app");

const SOURCES = ["", "facebook_messenger", "zalo_oa", "telegram", "email", "form_landing_page", "api_webhook"];

function view() {
  const filtered = applySearchFilter(state.all, { q: state.q, source: state.source });
  const pg = paginate(filtered, state.page, state.size);
  const rows = pg.slice.map((c) => `
    <tr data-id="${c.id}" class="row">
      <td>${c.name}</td><td>${c.phone}</td><td>${c.source}</td>
      <td>${(c.tags || []).join(", ")}</td><td>${c.stage}</td>
    </tr>`).join("");
  const opts = SOURCES.map((s) => `<option value="${s}"${s === state.source ? " selected" : ""}>${s || "Tất cả kênh"}</option>`).join("");
  const banner = state.degraded ? '<div class="banner">Dữ liệu tạm (mock).</div>' : "";
  const detail = state.selected ? detailView(state.selected) : "";
  root.innerHTML = `
    <nav class="nav"><span class="brand">OMI ▸ Contacts</span>
      <a href="../index.html">Dashboard</a></nav>
    <main class="content">
      ${banner}
      <div class="toolbar">
        <input id="q" placeholder="Tìm tên/phone/email" value="${state.q}" />
        <select id="source">${opts}</select>
      </div>
      <table class="tbl"><thead><tr><th>Tên</th><th>Phone</th><th>Kênh</th><th>Tags</th><th>Stage</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="muted">Không có kết quả</td></tr>'}</tbody></table>
      <div class="pager">
        <button id="prev" ${pg.page <= 1 ? "disabled" : ""}>‹</button>
        <span>Trang ${pg.page}/${pg.pages} · ${pg.total} contact</span>
        <button id="next" ${pg.page >= pg.pages ? "disabled" : ""}>›</button>
      </div>
      ${detail}
    </main>`;
  bind();
}

function detailView(c) {
  return `<section class="card detail">
    <h2>${c.name}</h2>
    <p>Phone: ${c.phone} · Email: ${c.email}</p>
    <p>Kênh: ${c.source} · Stage: ${c.stage}</p>
    <p>Tags: ${(c.tags || []).join(", ") || "—"}</p>
    <button id="close">Đóng</button>
  </section>`;
}

function bind() {
  const q = document.getElementById("q");
  if (q) q.oninput = (e) => { state.q = e.target.value; state.page = 1; view(); };
  const src = document.getElementById("source");
  if (src) src.onchange = (e) => { state.source = e.target.value; state.page = 1; view(); };
  const prev = document.getElementById("prev");
  if (prev) prev.onclick = () => { state.page--; view(); };
  const next = document.getElementById("next");
  if (next) next.onclick = () => { state.page++; view(); };
  document.querySelectorAll(".row").forEach((tr) => {
    tr.onclick = () => { state.selected = state.all.find((c) => c.id === tr.dataset.id); view(); };
  });
  const close = document.getElementById("close");
  if (close) close.onclick = () => { state.selected = null; view(); };
}

async function boot() {
  const { data, degraded } = await getContacts();
  state.all = data; state.degraded = degraded;
  view();
}
boot();
