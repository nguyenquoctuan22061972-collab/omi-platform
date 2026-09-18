// router.js — hash routing. PRD-004 §4.
export const ROUTES = {
  overview: { title: "Dashboard" },
  contacts: { title: "Contacts" },
  inbox: { title: "Inbox" },
  pipeline: { title: "Pipeline" },
};

export function currentRoute() {
  const h = (location.hash || "#/overview").replace(/^#\//, "").split("?")[0];
  return ROUTES[h] ? h : "overview";
}

export function onRouteChange(fn) {
  window.addEventListener("hashchange", () => fn(currentRoute()));
}
