// Copy thành config.js và đặt URL CRM Core. KHÔNG commit secret ở đây.
window.OMI_CONFIG = {
  CRM_BASE: "http://localhost:8080", // URL CRM Core (CR-001: GET /dashboard/kpi)
  POLL_MS: 30000                     // chu kỳ refresh KPI (ms); 0 = tắt poll
};
