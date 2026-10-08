import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import '../styles/payMap.css';

// 📊 WHAT PAYS: the real card's closed pieces by how long a coin was held, how it ended, who opened it — from confirmed fills only
// (GET /fuses/pay-map, backend/pay_map.py). Plain-words advice cites the numbers. A record of what happened, never a promise.
const usd = v => `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(2)}`;
const HOLD = ['<5m', '5-15m', '15-30m', '30-60m', '1-3h', '3h+'];
const KIND = [['trim', '💰 profit trims'], ['whole', '🚪 whole coin leaves'], ['recovery', '🧯 dead-coin recovery']];

export function payRows(m) {
  if (!m) return { hold: [], kind: [] };
  const max = Math.max(1, ...HOLD.map(k => Math.abs(m.byHold?.[k]?.usd || 0)));
  return {
    hold: HOLD.filter(k => m.byHold?.[k]?.n).map(k => ({ k, ...m.byHold[k], w: Math.max(0.04, Math.abs(m.byHold[k].usd) / max) })),
    kind: KIND.filter(([k]) => m.byKind?.[k]?.n).map(([k, l]) => ({ k, l, ...m.byKind[k] })),
  };
}

export function PayMap({ card = 'degen' }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = () => sharedJson('/api/reputation/fuses/pay-map', { maxAge: 60000 }).then(x => alive && setD(x)).catch(() => {}); load(); const t = setInterval(() => { if (!document.hidden) load(); }, 120000); return () => { alive = false; clearInterval(t); }; }, []);
  const m = d?.cards?.[card];
  if (!m?.pieces) return null;
  const { hold, kind } = payRows(m);
  return <details className="pm" data-testid="pay-map">
    <summary data-tip="Every closed piece of this card, matched buy → sell. Price result, fees apart. A record, never a promise.">📊 What pays · {m.pieces} pieces · {usd(m.netUsd)}</summary>
    {m.advice?.length > 0 && <ul className="pm-adv">{m.advice.map(a => <li key={a.key} data-testid={`pay-adv-${a.key}`}>{a.text}</li>)}</ul>}
    <div className="pm-grid">
      <div><small className="m-label">HELD FOR</small>{hold.map((r, i) => <p key={r.k} className={r.usd >= 0 ? 'up' : 'dn'} style={{ '--i': i }} data-tip={`${r.n} pieces · ${r.wonPct}% won · avg ${r.avgRet >= 0 ? '+' : ''}${r.avgRet}% a piece`}><b>{r.k}</b><span><i style={{ transform: `scaleX(${r.w})` }} /></span><em>{usd(r.usd)}</em><small>{r.wonPct}% · {r.n}</small></p>)}</div>
      <div><small className="m-label">HOW IT ENDED</small>{kind.map((r, i) => <p key={r.k} className={r.usd >= 0 ? 'up' : 'dn'} style={{ '--i': i }}><b>{r.l}</b><em>{usd(r.usd)}</em><small>{r.wonPct}% won · {r.n}</small></p>)}</div>
    </div>
  </details>;
}
