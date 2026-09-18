// Operations Dashboard UI (PRD-006 E). Standalone; KHÔNG sửa Dashboard KPI. Mock data.
const root = document.getElementById("app");

function dot(status) {
  const ok = /healthy|running|ok|passing|success|ready/i.test(status);
  return `<span class="badge ${ok ? "ok" : "warn"}">${status}</span>`;
}

function view(d) {
  const containers = d.containers.map((c) => `<tr><td>${c.name}</td><td>${dot(c.status)}</td></tr>`).join("");
  const wf = d.workflows.map((w) => `<tr><td>${w.id}</td><td>${w.name}</td><td>${dot(w.status)}</td><td>${w.enabled ? "on" : "off"}</td></tr>`).join("");
  const deploys = d.deploys.map((x) => `<li>${new Date(x.ts).toLocaleString("vi-VN")} · ${x.tag} · ${dot(x.result)}</li>`).join("");
  const alerts = d.alerts.map((a) => `<li>${new Date(a.ts).toLocaleString("vi-VN")} · [${a.level}] ${a.text}</li>`).join("") || "<li class='muted'>—</li>";
  root.innerHTML = `
    <nav class="nav"><span class="brand">OMI ▸ Operations</span><a href="../index.html">Dashboard KPI</a></nav>
    <main class="content">
      <div class="banner">Operations (mock) — giám sát hạ tầng & vận hành.</div>
      <section class="card"><h2>Container health</h2><table class="tbl">${containers}</table></section>
      <section class="card"><h2>Workflow status</h2><table class="tbl"><thead><tr><th>ID</th><th>Tên</th><th>Trạng thái</th><th>Enabled</th></tr></thead>${wf}</table></section>
      <div class="kpi-grid">
        <div class="card"><div class="card-label">Backup</div><div>${dot(d.backup.status)} · ${new Date(d.backup.last).toLocaleString("vi-VN")}</div></div>
        <div class="card"><div class="card-label">CI</div><div>${dot(d.ci.status)} · ${d.ci.suites} suites</div></div>
        <div class="card"><div class="card-label">Deploy gần nhất</div><div>${d.deploys[0] ? d.deploys[0].tag : "—"}</div></div>
      </div>
      <section class="card"><h2>Deploy history</h2><ul>${deploys}</ul></section>
      <section class="card"><h2>Alert history</h2><ul>${alerts}</ul></section>
    </main>`;
}

async function boot() {
  try {
    const res = await fetch("mock/ops.json");
    view(await res.json());
  } catch (e) {
    root.innerHTML = `<main class="content"><p class="muted">Không tải được ops mock.</p></main>`;
    console.error(e);
  }
}
boot();
