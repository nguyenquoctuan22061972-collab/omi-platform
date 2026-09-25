// OMI CEO Console — service worker (offline shell cache).
const CACHE = "omi-ceo-v1";
const ASSETS = ["./index.html", "./manifest.webmanifest"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
});
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  // API: network-first; shell: cache-first
  if (u.pathname.match(/\/(status|report|build|fix|deploy|health)$/)) {
    e.respondWith(fetch(e.request).catch(() => new Response(JSON.stringify({ ok: false, offline: true }), { headers: { "Content-Type": "application/json" } })));
  } else {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});
