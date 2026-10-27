import React, { useEffect, useRef, useState } from 'react';
import { useLivePrice } from '../lib/livePriceHub';
import { usd } from '../lib/cityPlan';
import '../styles/trenchTowers.css';

// 🗼 TRENCH TOWERS (owner 2026-10-26: "a list with no real line data is a no go"): every intake coin is a live tower card — its REAL price line
// (the agents' own tape: one price a pass, ~1 min apart, from /familia/intake) with the live price (FEELESS price hub, every 2s) ticking at the
// end, the 5-minute move flashing on change, who's buying (buy share), liquidity drift, 5-min volume and the desk's rank as a ring. Nothing
// is drawn that the data does not have: no tape → no line, the card says "tape filling".
const pct = v => (v == null || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : ''}${Math.abs(v) >= 100 ? Math.round(v) : v.toFixed(1)}%`);
const px = v => (!(v > 0) ? '—' : v >= 1 ? `$${v.toFixed(3)}` : `$${v.toPrecision(3)}`);
export const ageWord = m => (m < 60 ? `${Math.round(m)}m` : m < 2880 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`);

// pure: the tape (+ the live tick) → an SVG path in a W×H box, and whether it ends up or down from where it started
export function sparkPath(pts, W = 160, H = 44) {
  const p = (pts || []).filter(v => v > 0);
  if (p.length < 2) return null;
  const lo = Math.min(...p); const hi = Math.max(...p); const span = hi - lo || hi * 0.001 || 1;
  const xy = p.map((v, i) => [(i / (p.length - 1)) * W, H - 3 - ((v - lo) / span) * (H - 6)]);
  const line = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  return { line, area: `${line} L${W},${H} L0,${H} Z`, up: p[p.length - 1] >= p[0], last: xy[xy.length - 1], move: (p[p.length - 1] / p[0] - 1) * 100 };
}

function Flash({ v, children, cls = '' }) {   // flashes green / pink when the number moves
  const prev = useRef(v); const [d, setD] = useState('');
  useEffect(() => { if (v != null && prev.current != null && v !== prev.current) { setD(v > prev.current ? 'is-up' : 'is-dn'); const t = setTimeout(() => setD(''), 700); prev.current = v; return () => clearTimeout(t); } prev.current = v; return undefined; }, [v]);
  return <b className={`tw-flash ${d} ${cls}`}>{children}</b>;
}

function TowerCard({ r, i, onTrade }) {
  const live = useLivePrice(r.mint ? { chainId: 'solana', baseToken: { address: r.mint } } : null);
  const now = live?.live ? live.usd : null;
  const tape = [...(r.line || []), ...(now ? [now] : [])];
  const sp = sparkPath(tape);
  const ready = /READY/i.test(r.status || ''); const buy = Number(r.buy); const rank = Math.max(0, Math.min(1, (Number(r.rank) || 0) / 250));
  return <li className={`tw-card ${ready ? 'is-ready' : ''} ${sp ? (sp.up ? 'is-up' : 'is-dn') : ''}`} style={{ '--i': i }} data-testid={`tw-${i}`}>
    <header><em className="m-num">{i + 1}</em><span className="tw-sym"><b>${r.sym || r.mint?.slice(0, 4)}</b><small>{[r.status, r.ageMin != null ? `${ageWord(r.ageMin)} old` : null].filter(Boolean).join(' · ')}</small></span>
      <span className="tw-rank" style={{ '--r': rank }} data-tip={`The desk's rank ${r.rank != null ? Math.round(r.rank) : '—'} (READY from ~200)`}><i aria-hidden="true" /><b className="m-num">{r.rank != null ? Math.round(r.rank) : '—'}</b></span></header>
    <div className="tw-chart" data-tip={sp ? `Its last ${tape.length} reads (≈1 min apart) + the live price` : 'The agents\' tape for this coin is filling — a line appears after 2 reads'}>
      {sp ? <svg viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true"><path d={sp.area} className="tw-area" /><path d={sp.line} className="tw-line" /><circle cx={sp.last[0]} cy={sp.last[1]} r="2.6" className="tw-dot" /></svg>
        : <span className="tw-fill">tape filling…</span>}
      <span className="tw-px"><Flash v={now ?? r.line?.[r.line.length - 1] ?? null}>{px(now ?? r.line?.[r.line.length - 1])}</Flash><small className={(r.ch ?? 0) >= 0 ? 'is-up' : 'is-dn'}>5m {pct(r.ch)}</small></span>
    </div>
    <div className="tw-vit">
      <span data-tip="Share of the last hour's trades that were buys"><em>BUYERS</em><u aria-hidden="true"><s style={{ transform: `scaleX(${Number.isFinite(buy) ? Math.max(0.02, Math.min(1, buy > 1 ? buy / 100 : buy)) : 0})` }} /></u><b className="m-num">{Number.isFinite(buy) ? `${Math.round(buy > 1 ? buy : buy * 100)}%` : '—'}</b></span>
      <span data-tip="Market cap"><em>MC</em><b className="m-num">{r.mc ? usd(r.mc) : '—'}</b></span>
      <span data-tip="Liquidity change since the agents first read it"><em>LIQ Δ</em><b className={`m-num ${(r.liqD ?? 0) < -10 ? 'is-dn' : ''}`}>{pct(r.liqD)}</b></span>
      <span data-tip="Dollars traded in the last 5 minutes"><em>5M VOL</em><b className="m-num">{r.v5 != null ? usd(r.v5) : '—'}</b></span>
    </div>
    {r.read || r.theory ? <p className="tw-read" data-tip={r.theory || ''}>{r.read || r.theory}</p> : null}
    <button type="button" className="m-btn m-go tw-go" disabled={!r.pair} onClick={() => onTrade(r)} data-tip="Chart + Quick trade slide over the room — your wallet signs" data-testid={`av-tt-${i}`}>⚡ TRADE ${r.sym}</button>
  </li>;
}

export function TrenchTowers({ rows, onTrade }) {
  const ready = rows.filter(r => /READY/i.test(r.status || '')).length;
  const up = rows.filter(r => (r.ch ?? 0) > 0).length;
  return <section className="tw" data-testid="av-tt">
    <div className="tw-head"><span><b>🗼 {rows.length} COINS ON THE DESK</b><small>the agents' intake · real tape · live price</small></span>
      <span className="tw-sum"><i className="is-ready">{ready} READY</i><i className="is-up">▲ {up}</i><i className="is-dn">▼ {rows.length - up}</i></span></div>
    <ol className="tw-grid">{rows.map((r, i) => <TowerCard key={r.mint} r={r} i={i} onTrade={onTrade} />)}</ol>
  </section>;
}
