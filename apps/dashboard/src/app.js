// app.js — bootstrap: router + store + poll. PRD-004 §9.
import { store } from "./store.js";
import { getKpi } from "./api.js";
import { currentRoute, onRouteChange, ROUTES } from "./router.js";
import { nav } from "./components/nav.js";
import { overview, placeholder } from "./components/overview.js";

const root = document.getElementById("app");
const CFG = (typeof window !== "undefined" && window.OMI_CONFIG) || {};

function render(state) {
  const route = state.route;
  const body =
    route === "overview" ? overview(state) : placeholder(ROUTES[route].title);
  root.innerHTML = nav(route, state.degraded) + body;
}

async function refreshKpi() {
  const { kpi, degraded, error } = await getKpi();
  store.set({ kpi, degraded, error });
}

function boot() {
  store.subscribe(render);
  store.set({ route: currentRoute() });
  onRouteChange((route) => store.set({ route }));
  refreshKpi();
  const poll = CFG.POLL_MS ?? 30000;
  if (poll > 0) setInterval(refreshKpi, poll);
}

boot();
