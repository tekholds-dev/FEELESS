import { useCallback, useState } from 'react';

// 🔁 REFRESH COMES BACK TO WHERE YOU WERE (owner, 2026-10-16: "load should be the same page and a refresh come back to the recent"): a piece of
// screen state kept in THIS tab's sessionStorage — a refresh restores it, a new tab starts fresh. Private mode / blocked storage = plain state.
export function recall(key, init) {
  try { const v = sessionStorage.getItem(key); return v == null ? init : JSON.parse(v); } catch { return init; }
}

export function useRemembered(key, init) {
  const [v, setV] = useState(() => recall(key, init));
  const set = useCallback(next => setV(prev => {
    const val = typeof next === 'function' ? next(prev) : next;
    try { if (val == null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, JSON.stringify(val)); } catch { /* storage blocked */ }
    return val;
  }), [key]);
  return [v, set];
}
