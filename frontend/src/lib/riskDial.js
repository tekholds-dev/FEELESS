import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// 🎚 Risk dial — ONE choice sets a card's whole plan. Mirrors backend fuse_hq.RISK_DIALS (the server re-expands the id; the
// client copy is only for the live preview). Change both together.
export const RISK_DIALS = {
  safe: { label: '🛡 Safe', pool: [30, 15], runner: [30, 15], at: 25, onProfit: 'collect', mode: 'hold', runners: 1, why: 'Small, quick wins: every coin +30% / −15%, collect at +25%, holds together, 1 runner max' },
  balanced: { label: '⚖ Balanced', pool: [50, 25], runner: [50, 30], at: 50, onProfit: 'collect', mode: 'hold', runners: 2, why: 'Pools +50% / −25%, runners +50% / −30%, collect at +50%, up to 2 runners' },
  degen: { label: '🚀 Degen', pool: [100, 40], runner: [100, 40], at: 100, onProfit: 'compound', mode: 'swap', runners: 3, why: 'Let it run: +100% / −40%, compound at +100%, auto-rotate the weakest coin daily, 3 runners' },
};

export function applyRisk(legs, id) {
  const d = RISK_DIALS[id];
  return { risk: id, at: d.at, onProfit: d.onProfit, mode: d.mode,
    legs: Object.fromEntries(legs.map(l => { const [tp, sl] = d[l.runner || l.role === 'runner' ? 'runner' : 'pool']; return [l.pairAddress, { tp, sl }]; })) };
}

// Arena paper proof per dial (every round also played with each dial's TP/SL) — one shared fetch, 60s.
let proof = null; let at = 0; let req = null;
export function useDialProof() {
  const [p, setP] = useState(proof);
  useEffect(() => {
    let alive = true;
    if (!proof || Date.now() - at > 60000) {
      req = req || Promise.resolve().then(() => fetch(apiUrl('/api/reputation/fuses/arena'))).then(r => (r?.ok ? r.json() : null)).then(d => { proof = d?.dials || null; at = Date.now(); req = null; return proof; }).catch(() => { req = null; return null; });
      req.then(x => alive && setP(x));
    }
    return () => { alive = false; };
  }, []);
  return p;
}
