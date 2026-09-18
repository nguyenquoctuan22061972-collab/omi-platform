// pipelineChart.js — bar theo 6 stage (thuần CSS, không thư viện). PRD-004 component map.
const STAGES = ["lead", "contacted", "qualified", "proposal", "won", "lost"];

export function pipelineChart(kpi) {
  const by = (kpi && kpi.pipeline_by_stage) || {};
  const max = Math.max(1, ...STAGES.map((s) => by[s] || 0));
  const bars = STAGES.map((s) => {
    const v = by[s] || 0;
    const pct = Math.round((v / max) * 100);
    return `<div class="bar-row">
      <span class="bar-label">${s}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${pct}%"></span></span>
      <span class="bar-val">${v}</span>
    </div>`;
  }).join("");
  return `<section class="chart"><h2>Pipeline theo stage</h2>${bars}</section>`;
}
