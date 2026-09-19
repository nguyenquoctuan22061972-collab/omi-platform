// Health widget wiring (PRD-011 D). Additive — KHÔNG sửa operations.js / Dashboard KPI.
// Nạp thêm file này để bơm dữ liệu runtime-health vào phần tử #health-live (nếu có).
// Revenue widget vẫn placeholder (không đụng).

const CFG = (typeof window !== "undefined" && window.OMI_CONFIG) || {};
const HEALTH_BASE = CFG.HEALTH_BASE || ""; // vd /api/health (nginx proxy) — không hardcode host

export async function fetchGateway() {
  if (!HEALTH_BASE) return { status: "not_configured", note: "đặt OMI_CONFIG.HEALTH_BASE" };
  try {
    const res = await fetch(`${HEALTH_BASE}/health/gateway`);
    return await res.json();
  } catch (e) {
    return { status: "unreachable", error: String(e) };
  }
}

export function renderHealth(data) {
  const el = typeof document !== "undefined" && document.getElementById("health-live");
  if (!el) return; // không có chỗ gắn → no-op (an toàn)
  const badge = (s) => `<span class="badge ${/ready|reachable/.test(s) ? "ok" : "warn"}">${s}</span>`;
  el.innerHTML = `
    <section class="card"><h2>Runtime Health (live)</h2>
      <div>Gateway: ${badge(data.status || "?")}</div>
      <div>CRM: ${badge((data.crm && data.crm.status) || "?")}</div>
      <div>n8n: ${badge((data.n8n && data.n8n.status) || "?")}</div>
    </section>`;
}

export async function wireHealth() {
  renderHealth(await fetchGateway());
}

if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => { wireHealth(); });
}
