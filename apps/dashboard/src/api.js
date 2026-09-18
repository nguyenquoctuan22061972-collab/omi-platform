// api.js — integration layer: GET /dashboard/kpi (CR-001) + mock fallback. PRD-004 §6-7.

const CFG = (typeof window !== "undefined" && window.OMI_CONFIG) || {};
const CRM_BASE = CFG.CRM_BASE || ""; // không hardcode host; đọc từ config.js

const REQUIRED_KEYS = ["total_contacts", "total_messages", "pipeline_by_stage", "win_rate"];

function _valid(k) {
  return k && REQUIRED_KEYS.every((key) => key in k);
}

async function _fetchOnce(timeoutMs = 4000) {
  const url = `${CRM_BASE}/dashboard/kpi`;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!_valid(data)) throw new Error("payload thiếu trường KPI");
    return data;
  } finally {
    clearTimeout(t);
  }
}

async function _mock() {
  const res = await fetch("mock/kpi.json");
  return res.json();
}

// getKpi: thử CRM_BASE (retry x2 backoff), lỗi -> mock + degraded. PRD-004 §7.
export async function getKpi() {
  if (!CRM_BASE) {
    console.warn("CRM_BASE chưa cấu hình — dùng mock");
    return { kpi: await _mock(), degraded: true, error: "no-config" };
  }
  const delays = [0, 500, 1500];
  let lastErr;
  for (const d of delays) {
    if (d) await new Promise((r) => setTimeout(r, d));
    try {
      return { kpi: await _fetchOnce(), degraded: false, error: null };
    } catch (e) {
      lastErr = e;
      console.warn("getKpi retry:", e.message);
    }
  }
  console.error("getKpi thất bại, fallback mock:", lastErr && lastErr.message);
  return { kpi: await _mock(), degraded: true, error: String(lastErr && lastErr.message) };
}

export const _internal = { CRM_BASE, REQUIRED_KEYS, _valid };
