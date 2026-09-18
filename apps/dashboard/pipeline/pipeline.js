// Pipeline Kanban UI (PRD-006 C). Stages đồng bộ PRD-001; deal detail + activity timeline; mock state.
const STAGES = ["lead", "contacted", "qualified", "proposal", "won", "lost"];
const state = { deals: [], selected: null };
const root = document.getElementById("app");

function money(n) { return (n || 0).toLocaleString("vi-VN") + "₫"; }

function board() {
  return `<div class="kanban">${STAGES.map((s) => {
    const cards = state.deals.filter((d) => d.stage === s).map((d) => `
      <div class="deal" data-id="${d.id}">
        <b>${d.title}</b><div class="muted">${money(d.value)} · ${d.owner}</div>
      </div>`).join("");
    return `<div class="col"><h3>${s}</h3>${cards || '<div class="muted">—</div>'}</div>`;
  }).join("")}</div>`;
}

function detail(d) {
  const tl = (d.activity || []).map((a) =>
    `<li><span class="muted">${new Date(a.ts).toLocaleString("vi-VN")}</span> — ${a.text}</li>`).join("");
  return `<section class="card detail">
    <h2>${d.title}</h2>
    <p>Stage: ${d.stage} · Giá trị: ${money(d.value)} · Owner: ${d.owner}</p>
    <h3>Activity timeline</h3><ul class="timeline">${tl || "<li class='muted'>—</li>"}</ul>
    <button id="close">Đóng</button>
  </section>`;
}

function view() {
  root.innerHTML = `
    <nav class="nav"><span class="brand">OMI ▸ Pipeline</span><a href="../index.html">Dashboard</a></nav>
    <main class="content">
      <div class="banner">Pipeline Kanban (skeleton) — mock state, integration layer sẵn.</div>
      ${board()}
      ${state.selected ? detail(state.selected) : ""}
    </main>`;
  document.querySelectorAll(".deal").forEach((el) => {
    el.onclick = () => { state.selected = state.deals.find((d) => d.id === el.dataset.id); view(); };
  });
  const close = document.getElementById("close");
  if (close) close.onclick = () => { state.selected = null; view(); };
}

async function boot() {
  const res = await fetch("mock/deals.json");
  state.deals = await res.json();
  view();
}
boot();
