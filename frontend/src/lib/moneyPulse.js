import { useEffect, useState } from 'react';

// One owner-side poller for every HQ money card (reserve, pools, Circle, treasury, preflight).
// One request a minute, paused while the tab is hidden, shared by every card that subscribes.
const EVERY = 60_000;
let state = { data: null, error: '', at: 0 };
let caller = null;
let timer = null;
let inflight = null;
const subs = new Set();
const emit = () => subs.forEach(fn => fn(state));

export function refreshPulse(fresh = false) {
  if (!caller) return Promise.resolve(null);
  if (inflight && !fresh) return inflight;
  inflight = caller(`/admin/money-pulse${fresh ? '?fresh=1' : ''}`)
    .then(d => { state = { data: d, error: '', at: Date.now() }; emit(); return d; })
    .catch(e => { state = { ...state, error: e.message || 'Pulse failed' }; emit(); return null; })
    .finally(() => { inflight = null; });
  return inflight;
}

function tick() { if (typeof document === 'undefined' || !document.hidden) refreshPulse(); }

function start() {
  if (timer) return;
  timer = setInterval(tick, EVERY);
  if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisible);
}
function stop() {
  clearInterval(timer); timer = null;
  if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisible);
}
function onVisible() { if (!document.hidden && Date.now() - state.at > EVERY) refreshPulse(); }

// `call` is the HQ's admin-signed fetch. Pass null for read-only subscribers.
export function useMoneyPulse(call) {
  const [s, setS] = useState(state);
  useEffect(() => {
    if (call) caller = call;
    subs.add(setS);
    if (caller && !state.data && !inflight) refreshPulse(); else setS(state);
    start();
    return () => { subs.delete(setS); if (!subs.size) stop(); };
  }, [call]);
  return s;
}

export const circleFor = (pulse, address) => (address && pulse?.circle?.wallets?.find(w => w.address === address)) || null;

// test hook
export function _resetPulse() { state = { data: null, error: '', at: 0 }; caller = null; inflight = null; stop(); subs.clear(); }
