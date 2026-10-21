// ⏳ EVERY HQ BUTTON REACTS (owner, 2026-10-13: "make sure these btns and endpoints work and react instead of freezing"): HQ buttons
// fired their request and showed NOTHING until the server answered — a top-up waits for the keeper's swap pass (seconds, sometimes a
// minute), so the button looked dead and a second click sent a second request. ONE place fixes all of them: every HQ write goes
// through `hqWrite` (called by HqDeck's `call`), which
//   · marks the button that was just clicked `aria-busy` until the server answers (CSS: pulsing — STILL clickable: owner, 2026-10-21 "a lot stuck not
//     clickable" — a slow server locked every pressed button for up to 12s; a second click joins the same request instead),
//   · shares one request for the same write already in flight (a double click is one request, never two),
//   · counts writes in flight for the bar on top of HQ (`useHqBusy`), which says so in words once a write passes SLOW_MS.
import { useEffect, useState } from 'react';

export const SLOW_MS = 4000;
const CLICK_MS = 500;
export const BUSY_MAX_MS = 12000;
const flights = new Map();
const subs = new Set();
const st = { n: 0, since: 0, label: '' };
let lastBtn = null; let lastAt = 0;
const emit = () => subs.forEach(fn => fn());

if (typeof document !== 'undefined') document.addEventListener('click', e => {   // capture: runs before the button's own handler
  const b = e.target?.closest?.('button');   // a real button only — a role=button card (a whole seat) must never go dead while its write is in flight
  if (b) { lastBtn = b; lastAt = Date.now(); }
}, true);

export function hqWrite(key, fn) {
  if (!key) return fn();
  if (flights.has(key)) return flights.get(key);
  const btn = lastBtn && Date.now() - lastAt < CLICK_MS && lastBtn.isConnected !== false ? lastBtn : null;
  if (btn) btn.setAttribute('aria-busy', 'true');
  const free = btn ? setTimeout(() => btn.removeAttribute('aria-busy'), BUSY_MAX_MS) : null;   // a slow server never leaves a button dead: it is clickable again after 12s (the request keeps going, a second click shares it)
  st.n += 1; if (st.n === 1) { st.since = Date.now(); st.label = (btn?.textContent || '').trim().slice(0, 40); }
  emit();
  const p = Promise.resolve().then(fn).finally(() => {
    flights.delete(key); clearTimeout(free); if (btn) btn.removeAttribute('aria-busy');
    st.n = Math.max(0, st.n - 1); emit();
  });
  flights.set(key, p);
  return p;
}

export const hqBusyNow = () => ({ ...st });

export function useHqBusy() {
  const [v, setV] = useState(hqBusyNow);
  useEffect(() => {
    let t = null;
    const on = () => { setV(hqBusyNow()); clearTimeout(t); if (st.n) t = setTimeout(() => setV(hqBusyNow()), SLOW_MS + 50); };
    subs.add(on); on();
    return () => { subs.delete(on); clearTimeout(t); };
  }, []);
  return { n: v.n, label: v.label, slow: v.n > 0 && Date.now() - v.since >= SLOW_MS };
}
