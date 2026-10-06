import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { CardFx } from './CardFx';
import { openCoin } from './CoinDrawer';
import '../styles/fuseProof.css';

const ago = (t, now) => { const s = Math.max(0, now - t); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h`; };
const sg = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(Math.abs(v) >= 100 ? 0 : 1)}%`);
const left = s => (s <= 0 ? 'settling…' : s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m left` : `${Math.floor(s / 60)}m left`);
export const PROOF_LENSES = [['setups', '🃏 Pick a card'], ['feed', '🧾 Live proof'], ['duels', '⚔ Real duels']];

export function useProof(ms = 20000) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true;
    const load = first => { if (!first && document.hidden) return; fetch(apiUrl('/api/reputation/fuses/proof')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {}); };
    load(true); const t = setInterval(load, ms); return () => { alive = false; clearInterval(t); }; }, [ms]);
  return d;
}

// 🃏 The front door: every setup beside its OWN record, and where that record comes from (a replay on recorded prices, or a
// real card's on-chain ledger). The card is the product — pick one, not a coin.
export function SetupDoor({ d, onGo, onRun }) {
  const rows = d?.setups || [];
  if (!rows.length) return <p className="m-note">No setup has a record yet — the replay runs every ~15 minutes.</p>;
  return <ul className="fpf-setups" data-testid="proof-setups">{rows.map((s, i) => { const real = s.source === 'real'; const r = s.record || {};
    return <li key={s.key} className={`m-card cfx-host ${s.proven ? 'is-proven' : ''} ${real ? 'is-real' : ''}`} style={{ '--i': i }} data-testid={`setup-${s.key}`}>
      <CardFx kind={real ? 'beam' : s.proven ? 'grid' : 'aurora'} tone={(s.medPct || 0) < 0 ? 'down' : undefined} />
      <span className="m-label">{real ? '💵 REAL MONEY · ON-CHAIN' : `📼 REPLAY · ${s.hours || '—'}H WINDOWS`}{s.proven ? ' · ✅ PROVEN' : ' · 👀 NOT PROVEN'}</span>
      <b className="fpf-name">{s.name}</b><small className="m-dim">{s.why}</small>
      <div className="fpf-big"><em className={`m-num ${(s.medPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(s.medPct)}</em><small>{real ? 'all time, fees apart' : 'typical window'}</small></div>
      <div className="fpf-kv">{real
        ? <><span>put in <b>${r.putIn}</b> → now <b>${r.nowUsd}</b></span><span>{r.closed} closed · <b>{r.wonPct ?? '—'}%</b> won</span><span>profit takes <b>{r.takes?.n || 0}</b> ({r.takes?.wonPct ?? '—'}% won)</span><span>full exits <b>{r.exits?.n || 0}</b> ({r.exits?.wonPct ?? '—'}% won)</span><span>{r.swaps} swaps · {r.days}d</span></>
        : <><span><b>{s.upPct ?? '—'}%</b> of windows up</span><span>worst <b>{sg(s.worstPct)}</b></span><span>{s.n} windows judged</span></>}</div>
      {real ? <button type="button" className="m-btn" disabled={!(d.realLegs?.[r.tpl] || []).length} onClick={() => onRun?.(d.realLegs[r.tpl])} data-testid={`setup-run-${s.key}`}
        data-tip="Loads this card's current coins into the Lab so you can build your own card with them. You sign every buy yourself.">⚡ Build with its coins</button>
        : <button type="button" className="m-btn" onClick={() => onGo?.('cards')} data-testid={`setup-run-${s.key}`} data-tip="Opens My cards, where each card has this setup as a one-tap choice">Use on my card →</button>}
    </li>; })}</ul>;
}

// 🧾 Live proof: the real cards' confirmed swaps, newest first, each with the engine's reason and its transaction.
export function ProofFeed({ d, max = 12 }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 5000); return () => clearInterval(t); }, []);
  const rows = (d?.feed || []).slice(0, max);
  if (!rows.length) return <p className="m-note" data-testid="proof-feed">No real swap in the last 24 hours.</p>;
  return <ol className="fpf-feed" data-testid="proof-feed">{rows.map((x, i) => <li key={x.sig + x.side} className={x.side} style={{ '--i': i }}>
    <i className="fpf-side">{x.side === 'buy' ? 'BUY' : 'SELL'}</i>
    <button type="button" className="fpf-coin" onClick={() => openCoin({ mint: x.mint, pairAddress: x.pair, symbol: x.symbol })} data-tip="Open this coin">${x.symbol}</button>
    {x.pct != null ? <em className={`m-num ${x.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(x.pct)}</em> : <em className="m-dim">in</em>}
    <span className="fpf-why">{x.why || '—'}</span>
    <small className="m-dim">{x.label} · {ago(x.at, now)} ago</small>
    <a className="fpf-tx" href={`https://solscan.io/tx/${x.sig}`} target="_blank" rel="noopener noreferrer" data-tip="The confirmed transaction on-chain">tx ↗</a></li>)}</ol>;
}

// ⚔ Real duels: a real-money card against the best other card for 24h, on % result only. Points and a record — nothing is staked.
export function RealDuels({ d }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 15000); return () => clearInterval(t); }, []);
  const du = d?.duels || {}; const real = new Set(du.real || []);
  const rec = k => { const r = (du.rec || {})[k]; return r ? `${r.w}W ${r.l}L ${r.d}D` : '0W 0L 0D'; };
  const side = (k, label, pct, lead) => <div className={`fpf-side-card ${lead ? 'is-lead' : ''}`}><small className="m-label">{real.has(k) ? '💵 REAL' : '📄 PAPER'} · {rec(k)}</small><b>{label}</b><em className={`m-num ${(pct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{sg(pct)}</em></div>;
  if (!(du.live || []).length && !(du.log || []).length) return <p className="m-note" data-testid="proof-duels">A duel opens as soon as a real-money card is running.</p>;
  return <div className="fpf-duels" data-testid="proof-duels">
    {(du.live || []).map(x => <div key={x.id} className="fpf-duel m-card cfx-host"><CardFx kind="embers" />
      {side(x.a, x.aLabel, x.aPct, x.leader === x.a)}<span className="fpf-vs"><b>VS</b><small>{left(x.endsAt - now)}</small></span>{side(x.b, x.bLabel, x.bPct, x.leader === x.b)}</div>)}
    {(du.log || []).length > 0 && <ul className="fpf-log">{du.log.map(x => <li key={x.id}><b>{x.winner ? `🏆 ${x.winner === x.a ? x.aLabel : x.bLabel}` : '🤝 draw'}</b><span>{x.aLabel} {sg(x.aPct)} · {x.bLabel} {sg(x.bPct)}</span></li>)}</ul>}
    <small className="m-dim">{du.hours || 24}h on % result since the duel opened. A paper card trades at true fills but risks nothing, so this is a measure, not a prize: points and a record only.</small></div>;
}

// One section, three lenses (never three stacked blocks).
export function FuseProof({ onGo, onRun }) {
  const d = useProof();
  const [lens, setLens] = useState('setups');
  return <section className="fpf" data-testid="fuse-proof">
    <header><h3>🧾 PROOF, NOT PROMISES</h3><div className="m-seg" role="tablist" aria-label="Proof">{PROOF_LENSES.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} onClick={() => setLens(k)} data-testid={`proof-lens-${k}`}>{l}</button>)}</div></header>
    {!d ? <p className="m-note">Reading the record…</p> : lens === 'setups' ? <SetupDoor d={d} onGo={onGo} onRun={onRun} /> : lens === 'feed' ? <ProofFeed d={d} /> : <RealDuels d={d} />}
    <small className="m-dim fpf-fine">Every number here is a record of what happened: a replay on recorded prices or a real card's confirmed swaps. None of it says what happens next.</small>
  </section>;
}
