import { useEffect, useMemo, useState } from 'react';
import { sharedJson } from './sharedJson';

// 🐱 FEE'S CALLS ON EVERY CHART (owner, 2026-10-19: "users should see her calls only as chat bubbles, never agents or AIs — her thoughts come from the
// agents or OSSY / G4"): her paper BUY / SELL events (public `/api/cats/activity?catId=leader`, ONE shared read for every chart, 20s) become
// pins at the candle + market cap she called it at. Her words already carry where the call came from (the agents' desk, OSSY / G4).
const URL = '/api/cats/activity?catId=leader';
export const FEE_PINS = 12;
export function feePins(events, pair) {
  if (!pair) return [];
  return (events || []).filter(e => e && e.pairAddress === pair && (e.type === 'BUY' || e.type === 'SELL') && Number(e.marketCapUsd) > 0 && Number(e.ts) > 0)
    .slice(0, FEE_PINS).reverse()
    .map(e => ({ id: `fee-${e.id}`, at: Number(e.ts) / 1000, cap: Number(e.marketCapUsd), who: 'Fee', kind: 'feecat', action: e.type,
      text: String(e.detail || '').replace(/\s*\(paper[^)]*\)\.?/g, '').slice(0, 240), img: '/assets/feecat-mark.png', icon: '🐱' }));
}
export function useFeeCatCalls(pair, on = true) {
  const [ev, setEv] = useState(null);
  useEffect(() => {
    if (!pair || !on) return undefined;
    let live = true; let t = null;
    const go = () => sharedJson(URL, { maxAge: 18000 }).then(d => { if (live) setEv(d?.events || []); }).catch(() => {}).finally(() => { if (live) t = setTimeout(go, document.hidden ? 60000 : 20000); });
    go(); return () => { live = false; clearTimeout(t); };
  }, [pair, on]);
  return useMemo(() => feePins(ev, pair), [ev, pair]);
}
