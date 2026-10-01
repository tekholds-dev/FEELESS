import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { LiveFuseCard } from './FuseCard';
import { Countdown } from './RunnersPanel';
import { CardEarnings } from './CardEarnings';

// ⭐ ARENA PRIME: FEELESS's own top-tier cards, FULLY AUTO on paper — auto TP/SL, auto-compound, 2 coins rotate every 6h. Different
// from creator picks: these are the public proof the automation works before any trader's config goes auto. "Buy now" loads the
// card into the Lab (traders: up to 3 pools + 3 runners; you approve one wallet transaction).
const KIND = { tp: '💰 Auto TP', sl: '🛑 Auto stop', rotate: '⇄ Rotate', compound: '♻ Compound', deal: '🃏 Dealt' };
export const primeRow = c => ({ id: c.id, name: c.label, closed: false, costUsd: c.startUsd, valueUsd: c.valueUsd, realizedUsd: c.takenUsd || 0,
  pnlUsd: c.valueUsd - c.startUsd, pnlPct: c.pnlPct,
  legs: c.legs.map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, mint: l.mint, usd: l.costUsd, tokens: l.units, valueUsd: l.usd,
    pnlUsd: l.usd - l.costUsd, pnlPct: l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0, priced: true, priceNow: l.now })) });

export function usePrime(ms = 60000) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/prime')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), ms); return () => { alive = false; clearInterval(t); }; }, [ms]);
  return d;
}

export function ArenaPrime({ onLoad }) {
  const d = usePrime();
  const [open, setOpen] = useState(null);
  if (!d?.cards?.length) return null;
  return <section className="prime" data-testid="arena-prime">
    <header className="prime-head m-card m-live"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO · WE RUN ${d.cfg.sizeUsd} EACH</span>
      <h3>Top-tier cards. Every automation on.</h3>
      <p className="m-dim">Auto take-profit / stop-loss per coin · {d.cfg.compound ? 'gains auto-compound into the other coins' : 'gains kept as cash'} · the {d.cfg.rotateCount} weakest coins rotate every {d.cfg.rotateHours}h. Paper money, real prices — the proof before any config goes auto for you. Fees are tracked apart, never inside P&L.</p></header>
    <div className="prime-row">{d.cards.map(c => <article key={c.id} className={`prime-card t-${c.tpl}`} data-testid={`prime-${c.tpl}`}>
      <LiveFuseCard r={primeRow(c)} aura={c.pnlPct >= 10 ? 'fire' : c.pnlPct >= 0 ? 'sparkle' : ''} />
      <div className="prime-stats"><span data-tip="Value now vs the start, fees not included"><small>P&L</small><b className={`m-num ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{c.pnlPct >= 0 ? '+' : ''}{c.pnlPct.toFixed(1)}%</b></span>
        <span data-tip="Gains from auto take-profits rolled back into the card"><small>COMPOUNDED</small><b className="m-num">${c.compoundedUsd.toFixed(2)}</b></span>
        <span data-tip="Next auto-rotation of the weakest coins"><small>ROTATES IN</small><b className="m-num"><Countdown at={c.lastRotateAt + d.cfg.rotateHours * 3600} /></b></span></div>
      <div className="prime-acts"><button type="button" className="m-btn" onClick={() => setOpen(open === c.id ? null : c.id)} data-testid={`prime-earn-${c.tpl}`}>📜 Where the profit went</button>
        <button type="button" className="m-btn primary m-go" onClick={() => { onLoad?.(c.legs.map(l => ({ chainId: 'solana', pairAddress: l.pairAddress, symbol: l.symbol, baseAddress: l.mint, runner: l.role === 'runner', role: l.role }))); toast.success(`${c.label} loaded into the Lab — you approve the buy`); }} data-testid={`prime-buy-${c.tpl}`}>⚡ Buy now</button></div>
      {open === c.id && <CardEarnings title={c.label} events={c.events.map(e => ({ ...e, label: KIND[e.kind] || e.kind }))} taken={c.takenUsd} compounded={c.compoundedUsd} fees={c.feesUsd} onClose={() => setOpen(null)} paper />}
    </article>)}</div>
  </section>;
}

// Cmd Ctr › ⚔ Arena: Prime controls — on/off, size, rotation (hours + coins), compound, deal fresh cards.
export function PrimeControls({ call }) {
  const d = usePrime(30000);
  const [cfg, setCfg] = useState(null);
  useEffect(() => { if (d?.cfg && !cfg) setCfg(d.cfg); }, [d, cfg]);
  if (!cfg) return null;
  const save = (patch, reset = false) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ cfg: patch, reset }) })
    .then(r => { setCfg(r.cfg); toast.success(reset ? 'Fresh Prime cards dealt' : 'Prime config saved'); }).catch(e => toast.error(e.message));
  const seg = (k, vals, fmt) => <div className="m-seg">{vals.map(v => <button key={v} type="button" className={cfg[k] === v ? 'active' : ''} onClick={() => save({ [k]: v })}>{fmt(v)}</button>)}</div>;
  return <section className="m-card fops" data-testid="prime-controls"><div className="m-row"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO (PAPER)</span>
    <label className="m-toggle"><input type="checkbox" checked={cfg.on} onChange={e => save({ on: e.target.checked })} /><span>{cfg.on ? 'Running' : 'Off'}</span></label></div>
    <div className="prime-ctl"><span>Size</span>{seg('sizeUsd', [25, 100, 500], v => `$${v}`)}<span>Rotate every</span>{seg('rotateHours', [3, 6, 12], v => `${v}h`)}
      <span>Coins per rotation</span>{seg('rotateCount', [1, 2, 3], v => `${v}`)}
      <label className="m-toggle"><input type="checkbox" checked={cfg.compound} onChange={e => save({ compound: e.target.checked })} /><span>Auto-compound gains</span></label></div>
    <div className="m-row"><button type="button" className="m-btn" onClick={() => save({}, true)} data-testid="prime-reset">🃏 Deal fresh Prime cards</button>
      <small className="m-dim">{(d?.cards || []).map(c => `${c.label} ${c.pnlPct >= 0 ? '+' : ''}${c.pnlPct.toFixed(1)}%`).join(' · ') || 'dealing…'}</small></div></section>;
}
