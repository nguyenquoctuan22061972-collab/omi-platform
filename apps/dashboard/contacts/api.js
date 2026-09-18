// Contacts integration layer (PRD-006 A). Mock-first; điểm nối GET /contacts sau (không đổi API).
const CFG = (typeof window !== "undefined" && window.OMI_CONFIG) || {};
const CRM_BASE = CFG.CRM_BASE || "";

// getContacts: hiện đọc mock. Khi go-live sẽ trỏ GET {CRM_BASE}/contacts (list endpoint tương lai).
export async function getContacts() {
  try {
    const res = await fetch("mock/contacts.json");
    return { data: await res.json(), degraded: !CRM_BASE };
  } catch (e) {
    console.error("getContacts mock lỗi", e);
    return { data: [], degraded: true };
  }
}

// Thao tác client-side trên tập đã tải.
export function applySearchFilter(items, { q = "", source = "" } = {}) {
  const term = q.trim().toLowerCase();
  return items.filter((c) => {
    const matchQ = !term ||
      [c.name, c.phone, c.email].some((v) => (v || "").toLowerCase().includes(term));
    const matchSource = !source || c.source === source;
    return matchQ && matchSource;
  });
}

export function paginate(items, page = 1, size = 5) {
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / size));
  const p = Math.min(Math.max(1, page), pages);
  return { page: p, pages, total, slice: items.slice((p - 1) * size, p * size) };
}
