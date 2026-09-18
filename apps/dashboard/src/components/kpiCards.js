// kpiCards.js — 3 thẻ KPI. PRD-004 component map.
function fmt(n) {
  return (n ?? 0).toLocaleString("vi-VN");
}

export function kpiCards(kpi) {
  const k = kpi || {};
  const winPct = Math.round((k.win_rate ?? 0) * 100);
  const cards = [
    { label: "Contacts", value: fmt(k.total_contacts) },
    { label: "Messages", value: fmt(k.total_messages) },
    { label: "Win rate", value: `${winPct}%` },
  ];
  return `<div class="kpi-grid">${cards
    .map(
      (c) => `<div class="card" role="group" aria-label="${c.label}">
        <div class="card-value">${c.value}</div>
        <div class="card-label">${c.label}</div>
      </div>`
    )
    .join("")}</div>`;
}
