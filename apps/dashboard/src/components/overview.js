// overview.js — layout màn Dashboard. PRD-004 component map.
import { kpiCards } from "./kpiCards.js";
import { pipelineChart } from "./pipelineChart.js";

export function overview(state) {
  const banner = state.degraded
    ? `<div class="banner" role="status">Dữ liệu tạm (mock) — chưa kết nối CRM Core.</div>`
    : "";
  if (!state.kpi) {
    return `<main class="content"><div class="skeleton">Đang tải KPI…</div></main>`;
  }
  return `<main class="content">
    ${banner}
    ${kpiCards(state.kpi)}
    ${pipelineChart(state.kpi)}
  </main>`;
}

// Skeleton cho các route khác (theo wireframe PRD-001 §8).
export function placeholder(title) {
  return `<main class="content"><h1>${title}</h1>
    <p class="muted">Màn hình dự kiến (skeleton) — sẽ hoàn thiện ở PRD kế tiếp.</p></main>`;
}
