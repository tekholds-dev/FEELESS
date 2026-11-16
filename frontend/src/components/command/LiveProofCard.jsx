import React, { useMemo } from 'react';
import { LineChart, Line, YAxis, ReferenceLine, ResponsiveContainer } from 'recharts';
import { Live } from './PopDesk';
import '../../styles/liveBid.css';

// 📺 WATCH IT LIVE IN CHAT, for PoW and PoP (owner 2026-11-15 "epic live cards for the other proof types … in the main desk chat").
// The same pinned card as a PoB's game: a PoW shows its coin's price against entry / take profit / stop and its P&L; a PoP shows its
// paper perp (side, mark, return, liquidation). Both read the folder the desk already polls every 5 s. Watching only: nothing here trades.
// P&L never includes fees: a closed PoW shows the server's settled pnlPct (money that reached the pool), a live one the price move.
const pctText = v => (v == null || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(2)}%`);
const solText = v => (v == null || !Number.isFinite(v) ? '—' : `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(5)} SOL`);
const pxText = v => { const n = Number(v); return !n ? '—' : n < 0.01 ? n.toPrecision(3) : n.toLocaleString(undefined, { maximumFractionDigits: 4 }); };

// The live numbers of a PoW folder. Pure.
export function powLive(f) {
  if (!f) return null;
  const e = Number(f.entry) || 0; const ys = (f.line || []).map(Number).filter(v => v > 0); const now = Number(f.now) || ys[ys.length - 1] || 0;
  const closed = f.status === 'closed' || f.pnlPct != null;
  const pct = closed && f.pnlPct != null ? Number(f.pnlPct) : e && now ? ((now - e) / e) * 100 : null;
  const sol = closed && (f.netPnlSol ?? f.pnlSol) != null ? Number(f.netPnlSol ?? f.pnlSol) : pct != null && f.sol ? (Number(f.sol) * pct) / 100 : null;
  const tp = e ? e * (1 + (Number(f.tp) || 0) / 100) : null; const sl = e ? e * (1 - (Number(f.sl) || 0) / 100) : null;
  return { sym: f.sym || f.pick?.sym || '', entry: e, now, pct, sol, tp, sl, closed, bought: !!(f.buySig || f.boughtAt), rows: ys.map((v, n) => ({ n, v })), phase: f.phase || f.status };
}

function PowView({ f }) {
  const x = useMemo(() => powLive(f), [f]);
  if (!x) return null;
  const tone = x.pct == null ? 'none' : x.pct >= 0 ? 'good' : 'bad';
  return <div className="lbc-pane" data-testid="lpc-pow">
    <div className="lpc-score"><span><small className="m-label">${x.sym || 'COIN'} · {x.closed ? 'CLOSED' : x.bought ? 'HOLDING' : String(x.phase || 'READING').toUpperCase()}</small><b className={`m-num is-${tone}`} data-testid="lpc-pct">{pctText(x.pct)}</b><small className="m-num">{solText(x.sol)}{x.closed ? ' · settled' : ' · live, before the sell'}</small></span></div>
    {x.rows.length >= 2 ? <div className="lbc-chart" role="img" aria-label={`$${x.sym} price against entry, take profit and stop`}><ResponsiveContainer width="100%" height={120}>
      <LineChart data={x.rows} margin={{ top: 6, right: 6, bottom: 6, left: 6 }}><YAxis hide domain={['auto', 'auto']} />
        {x.tp ? <ReferenceLine y={x.tp} ifOverflow="extendDomain" stroke="var(--m-accent)" strokeDasharray="4 4" /> : null}{x.sl ? <ReferenceLine y={x.sl} ifOverflow="extendDomain" stroke="var(--m-danger)" strokeDasharray="4 4" /> : null}{x.entry ? <ReferenceLine y={x.entry} stroke="var(--m-dim)" /> : null}
        <Line type="monotone" dataKey="v" dot={false} isAnimationActive={false} stroke={tone === 'bad' ? 'var(--m-danger)' : 'var(--m-accent)'} strokeWidth={2} /></LineChart></ResponsiveContainer></div>
      : <p className="dsk-note">The price line draws once it has bought and taken two reads.</p>}
    <div className="pop-nums"><span><em>ENTRY</em><b className="m-num">{pxText(x.entry)}</b></span><span><em>NOW</em><b className="m-num">{pxText(x.now)}</b></span><span><em>TAKE · STOP</em><b className="m-num">+{Number(f.tp) || 0}% · −{Number(f.sl) || 0}%</b></span></div>
  </div>;
}

function PopView({ f }) {
  if (f.market && f.entry != null && f.mark != null && f.openedAt) return <Live t={f} />;
  const r = f.roePct != null ? Number(f.roePct) : null;
  return <div className="lbc-pane" data-testid="lpc-pop"><div className="lpc-score"><span><small className="m-label">{f.market ? `${f.market}-PERP · ${String(f.side || '').toUpperCase()}` : 'PoP'} · paper</small><b className={`m-num is-${r == null ? 'none' : r >= 0 ? 'good' : 'bad'}`}>{f.noTrade ? 'No trade' : r == null ? '—' : `${r >= 0 ? '+' : '−'}${Math.abs(r).toFixed(1)}%`}</b><small>{String(f.exitWhy || f.why || '').slice(0, 140)}</small></span></div></div>;
}

export function LiveProofCard({ kind, f, onClose }) {
  if (!f) return null;
  const title = kind === 'pow' ? `PoW #${f.n || '…'}${f.sym ? ` · $${f.sym}` : ''}` : `PoP #${f.n || '…'}${f.market ? ` · ${f.market}` : ''}`; const live = f.status !== 'closed';
  return <section className="lbc m-glass" aria-label={`Watching ${title} live`} data-testid={`lpc-${kind}-card`}>
    <header className="lbc-h"><span className="lbc-t"><b className="m-num">📺 {title}</b></span><small className={live ? 'is-live' : ''}>{live ? '● LIVE' : 'closed'}</small>
      <button type="button" className="lbc-x" onClick={onClose} aria-label="Stop watching" data-tip="Stop watching (the proof stays in its folder)" data-testid="lpc-close">✕</button></header>
    {kind === 'pow' ? <PowView f={f} /> : <PopView f={f} />}
  </section>;
}
