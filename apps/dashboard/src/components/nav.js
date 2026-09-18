// nav.js — thanh điều hướng + responsive toggle. PRD-004 component map.
import { ROUTES } from "../router.js";

export function nav(activeRoute, degraded) {
  const links = Object.entries(ROUTES)
    .map(([key, r]) => {
      const active = key === activeRoute ? ' class="active" aria-current="page"' : "";
      return `<a href="#/${key}"${active}>${r.title}</a>`;
    })
    .join("");
  const badge = degraded ? '<span class="badge" title="Dữ liệu tạm">degraded</span>' : "";
  return `
    <nav class="nav">
      <button class="nav-toggle" aria-label="Menu" onclick="document.body.classList.toggle('nav-open')">☰</button>
      <span class="brand">OMI ▸</span>
      <div class="nav-links">${links}</div>
      ${badge}
    </nav>`;
}
