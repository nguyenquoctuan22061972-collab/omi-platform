// store.js — state management tối giản (pub/sub). PRD-004 §5.
const _state = { kpi: null, degraded: false, error: null, route: "overview" };
const _subs = new Set();

export const store = {
  get() {
    return _state;
  },
  set(patch) {
    Object.assign(_state, patch);
    _subs.forEach((fn) => {
      try { fn(_state); } catch (e) { console.error("subscriber error", e); }
    });
  },
  subscribe(fn) {
    _subs.add(fn);
    return () => _subs.delete(fn);
  },
};
