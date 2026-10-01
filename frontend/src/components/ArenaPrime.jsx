import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../lib/api';
import { LiveFuseCard } from './FuseCard';
import { Countdown } from './RunnersPanel';
import { CardEarnings } from './CardEarnings';

// ⭐ ARENA PRIME: FEELESS's own top-tier cards, FULLY AUTO on paper — auto TP/SL, auto-compound, 2 coins rotate every 6h. Different
// from creator picks: these are the public proof the automation works before any trader's config goes auto. "Buy now" loads the
// card into the Lab (traders: up to 3 pools + 3 runners; you approve one wallet transaction).
const KIND = { tp: '💰 Auto TP', sl: '🛑 Auto stop', rotate: '⇄ Rotate', compound: '♻ Compound', deal: '🃏 Dealt', floor: '🛡 Floor' };
// Tier FX: 💎 Diamond = frost aura + prism ring + glints · 🥇 Gold = gold dust + shine sweep · 🔥 Blaze = fire + embers.
// They burn brighter (is-hot) when the card is up ≥ +10%. Transform/opacity only; frozen under fx-lite / reduced motion.
const TIER = { diamond: { aura: 'frost', name: 'DIAMOND' }, gold: { aura: 'gold', name: 'GOLD' }, blaze: { aura: 'fire', name: 'BLAZE' } };
export const primeRow = c => ({ id: c.id, name: c.label, closed: false, costUsd: c.startUsd, valueUsd: c.valueUsd, realizedUsd: c.takenUsd || 0,
  pnlUsd: c.valueUsd - c.startUsd, pnlPct: c.pnlPct,
  legs: c.legs.map(l => ({ pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, mint: l.mint, usd: l.costUsd, tokens: l.units, valueUsd: l.usd,
    pnlUsd: l.usd - l.costUsd, pnlPct: l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0, priced: true, priceNow: l.now, stars: l.stars })) });

export function usePrime(ms = 60000) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = first => (first || !document.hidden) && fetch(apiUrl('/api/reputation/fuses/prime')).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(true); const t = setInterval(() => load(false), ms); const now = () => load(true); window.addEventListener('feeless:prime', now);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:prime', now); }; }, [ms]);
  return d;
}

export function ArenaPrime({ onLoad }) {
  const d = usePrime();
  const [open, setOpen] = useState(null);
  if (!d?.cards?.length) return null;
  return <section className="prime" data-testid="arena-prime">
    <header className="prime-head m-card m-live"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO · WE RUN ${d.cfg.sizeUsd} EACH</span>
      <h3>Top-tier cards. Every automation on.</h3>
      <p className="m-dim">Only 3–5★ coins: a stable major anchor (SOL / JitoSOL / cbBTC — never rotated) + deep pools + gated runners. Auto TP / SL per coin · {d.cfg.compound ? 'gains auto-compound into the other coins' : 'gains kept as cash'} · the {d.cfg.rotateCount} weakest rotate every {d.cfg.rotateHours}h · 🛡 card floor at −{d.cfg.floorPct}% (everything into the anchor). Paper money, real prices. Fees tracked apart, never in P&L.</p></header>
    <div className="prime-row">{d.cards.map(c => { const t = TIER[c.tier] || TIER.gold; return <article key={c.id} className={`prime-card t-${c.tpl} tier-${c.tier || 'gold'} ${c.pnlPct >= 10 ? 'is-hot' : ''}`} data-testid={`prime-${c.tpl}`}>
      <span className="prime-tier" aria-hidden="true"><i className="pt-ring" /><i className="pt-sweep" />{Array.from({ length: 6 }, (_, i) => <i key={i} className="pt-spark" style={{ '--i': i }} />)}</span>
      <b className="prime-badge">{t.name}</b>
      <LiveFuseCard r={primeRow(c)} aura={t.aura} />
      <ul className="prime-legs">{c.legs.map(l => ({ ...l, pnlPct: l.pnlPct ?? (l.costUsd ? (l.usd / l.costUsd - 1) * 100 : 0) })).map(l => <li key={l.pairAddress}><b>${l.symbol}</b><small className={`pl-${l.role}`}>{l.role === 'anchor' ? '⚓ anchor' : l.role}</small><i data-tip={`${l.stars || 3}★ — ${l.role === 'anchor' ? 'real major, the stable base' : l.role === 'pool' ? 'depth + volume' : 'runner score'}`}>{'★'.repeat(l.stars || 3)}</i>
        <em className={`m-num ${l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{l.pnlPct >= 0 ? '+' : ''}{l.pnlPct.toFixed(1)}%</em></li>)}</ul>
      <div className="prime-rec" data-testid={`prime-rec-${c.tpl}`}><span data-tip="Of the last logged days (max 10), how many the card was up ≥ +10% over 24h. The goal is 8/10 — the Arena shows the truth, never a promise.">
        <small>GOOD DAYS (+10%)</small><b className="m-num">{c.loggedDays ? `${c.goodDays}/${c.loggedDays}` : '—'}</b></span>
        <span data-tip={`Lowest this run has been. The floor moves everything into the anchor at −${d.cfg.floorPct}%, so −25% is never reached short of a price gap.`}><small>WORST</small><b className={`m-num ${(c.lowPct || 0) < 0 ? 'm-neg' : ''}`}>{(c.lowPct || 0).toFixed(1)}%</b></span>
        {c.floored && <span className="prime-floored" data-tip="Floored: holding the anchor until tomorrow's fresh deal">🛡 FLOORED</span>}</div>
      <div className="prime-stats"><span data-tip="Value now vs the start, fees not included"><small>P&L</small><b className={`m-num ${c.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{c.pnlPct >= 0 ? '+' : ''}{c.pnlPct.toFixed(1)}%</b></span>
        <span data-tip="Gains from auto take-profits rolled back into the card"><small>COMPOUNDED</small><b className="m-num">${c.compoundedUsd.toFixed(2)}</b></span>
        <span data-tip="Next auto-rotation of the weakest coins"><small>ROTATES IN</small><b className="m-num"><Countdown at={c.lastRotateAt + d.cfg.rotateHours * 3600} /></b></span></div>
      <div className="prime-acts"><button type="button" className="m-btn" onClick={() => setOpen(open === c.id ? null : c.id)} data-testid={`prime-earn-${c.tpl}`}>🪟 Open card · profit trail</button>
        <button type="button" className="m-btn primary m-go" onClick={() => { onLoad?.(c.legs.map(l => ({ chainId: 'solana', pairAddress: l.pairAddress, symbol: l.symbol, baseAddress: l.mint, runner: l.role === 'runner', role: l.role }))); toast.success(`${c.label} loaded into the Lab — you approve the buy`); }} data-testid={`prime-buy-${c.tpl}`}>⚡ Buy now</button></div>
      {open === c.id && <CardEarnings title={c.label} events={c.events.map(e => ({ ...e, label: e.kind === 'tp' ? ({ ride: '🚀 Ride · house money', bank: '🏦 Banked 75%' }[e.mode] || KIND.tp) : KIND[e.kind] || e.kind }))} taken={c.takenUsd} compounded={c.compoundedUsd} fees={c.feesUsd} onClose={() => setOpen(null)} paper
        legs={c.legs.map(l => ({ ...l, rundown: l.role === 'anchor' ? 'Solid hold — never stopped or rotated; the floor moves everything here' : `TP +${c.tp}% (momentum decides ride / gain / bank) · stop −${c.sl}% (cut at −${c.sl / 2}% if fading) · rotates when weakest` }))} autos={c.events.filter(e => Date.now() / 1000 - e.at < 86400 && e.kind !== 'deal').map(e => ({ at: e.at, text: `${KIND[e.kind] || e.kind} ${e.symbol ? `$${e.symbol} ` : ''}— ${e.why || ''}`, url: '#' }))} />}
    </article>; })}</div>
  </section>;
}

// Cmd Ctr › ⚔ Arena: Prime controls — on/off, size, rotation (hours + coins), compound, deal fresh cards.
export function PrimeControls({ call }) {
  const d = usePrime(30000);
  const [cfg, setCfg] = useState(null);
  useEffect(() => { if (d?.cfg && !cfg) setCfg(d.cfg); }, [d, cfg]);
  const [mins, setMins] = useState('');
  useEffect(() => { if (cfg) setMins(String(Math.round(cfg.rotateHours * 60))); }, [cfg]);
  if (!cfg) return null;
  const save = (patch, reset = false) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ cfg: patch, reset }) })
    .then(r => { setCfg(r.cfg); toast.success(reset ? 'Fresh Prime cards dealt' : 'Prime config saved'); }).catch(e => toast.error(e.message));
  // Cmd Ctr ⇄ one coin / 🃏 one tier — paper cards only, audited server-side.
  const act = (body, msg) => call('/admin/arena/prime', { method: 'POST', body: JSON.stringify(body) }).then(() => { toast.success(msg); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message));
  const seg = (k, vals, fmt) => <div className="m-seg">{vals.map(v => <button key={v} type="button" className={cfg[k] === v ? 'active' : ''} onClick={() => save({ [k]: v })}>{fmt(v)}</button>)}</div>;
  return <section className="m-card fops" data-testid="prime-controls"><div className="m-row"><span className="m-label">⭐ ARENA PRIME · FULLY AUTO (PAPER)</span>
    <label className="m-toggle"><input type="checkbox" checked={cfg.on} onChange={e => save({ on: e.target.checked })} /><span>{cfg.on ? 'Running' : 'Off'}</span></label></div>
    <div className="prime-ctl"><span>Size</span>{seg('sizeUsd', [25, 100, 500], v => `$${v}`)}<span>Rotate every</span>{seg('rotateHours', [0.25, 0.5, 1, 3, 6], v => (v < 1 ? `${v * 60}m` : `${v}h`))}
      <label className="prime-min" data-tip="Any interval: 15 min – 48 h. The weakest non-anchor coins rotate out on this clock."><input className="m-input m-num" inputMode="numeric" value={mins} onChange={e => setMins(e.target.value.replace(/[^0-9]/g, ''))}
        onBlur={() => Number(mins) >= 15 && Number(mins) !== Math.round(cfg.rotateHours * 60) && save({ rotateHours: Math.min(48, Number(mins) / 60) })} onKeyDown={e => e.key === 'Enter' && e.currentTarget.blur()} data-testid="prime-rotate-min" /><span>min</span></label>{null}
      <span>Coins per rotation</span>{seg('rotateCount', [1, 2, 3], v => `${v}`)}
      <span data-tip="Card-level floor: at this loss every pool + runner moves into the anchor (re-dealt next day as a new run)">Floor</span>{seg('floorPct', [10, 15, 20, 25], v => `−${v}%`)}
      <label className="m-toggle"><input type="checkbox" checked={cfg.compound} onChange={e => save({ compound: e.target.checked })} /><span>Auto-compound gains</span></label></div>
    <div className="prime-edit">{(d?.cards || []).map(c => <div key={c.id} className="m-row"><b>{c.label}</b>
      {c.legs.map(l => <button key={l.pairAddress} type="button" className="m-btn" data-tip={`Replace $${l.symbol} with the best 3★+ ${l.role} not on the card (same $)`} onClick={() => act({ replace: { tpl: c.tpl, pairAddress: l.pairAddress } }, `$${l.symbol} replaced`)} data-testid={`prime-swap-${c.tpl}-${l.pairAddress}`}>⇄ ${l.symbol}</button>)}
      <button type="button" className="m-btn" onClick={() => act({ redeal: c.tpl }, `${c.label} re-dealt`)} data-testid={`prime-redeal-${c.tpl}`}>🃏 Re-deal</button></div>)}</div>
    <div className="m-row"><button type="button" className="m-btn" onClick={() => save({}, true)} data-testid="prime-reset">🃏 Deal fresh Prime cards</button>
      <small className="m-dim">{(d?.cards || []).map(c => `${c.label} ${c.pnlPct >= 0 ? '+' : ''}${c.pnlPct.toFixed(1)}%`).join(' · ') || 'dealing…'}</small></div></section>;
}
