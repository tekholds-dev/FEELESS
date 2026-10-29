import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { useGlide } from '../lib/useGlide';
import '../styles/priceGaps.css';

// 📐 PRICE GAPS (owner 2026-10-29, L02 — the lootcollector idea: "price gaps … add-on to AutoCompound / pools / Night Vault"). READ-ONLY:
// the tokens the Night Vault's pools hold, priced across every real pool they trade in (backend price_gap.py, GET /familia-pools/gaps, 1 min).
// Each token is a drawn RAIL: its pools as lamps at their price (cheap end mint, rich end gold), the bridge between them = the gap after a
// swap's cost each side. A gap OPEN on two reads in a row lights up and its clock ticks. Use: compound / enter through the cheap pool
// (Jupiter routes there for you); a gap that stays open is arbitrage volume — fees for that pool's LPs. Nothing here trades.
const pct = (v, d = 2) => `${v >= 0 ? '+' : ''}${Number(v).toFixed(d)}%`;
const clock = s => (s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m` : s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`);
const px$ = v => (v >= 100 ? `$${v.toFixed(2)}` : v >= 1 ? `$${v.toFixed(4)}` : `$${v.toPrecision(4)}`);
export const gapWord = g => (g.open ? `open ${clock(g.openSec)} — buy side ${g.lo.dex}, rich side ${g.hi.dex}` : g.netPct > 0 ? 'beats its costs — confirming on the next read' : 'inside its swap costs');

function Num({ v, cls }) { const g = useGlide(v); return <b className={`m-num ${cls || ''}`}>{pct(g)}</b>; }

function Rail({ g, i, age }) {
  const span = Math.max(g.gapPct, 0.05);
  const cost = Math.min(100, ((g.gapPct - g.netPct) / span) * 100);
  return <li className={`gp-row${g.open ? ' is-open' : g.netPct > 0 ? ' is-maybe' : ''}`} style={{ '--i': i }} data-testid="gp-row"
    data-tip={`${g.sym} on ${g.n} pools · cheapest ${g.lo.dex} (vs ${g.lo.vs}) ${px$(g.lo.px)} · richest ${g.hi.dex} (vs ${g.hi.vs}) ${px$(g.hi.px)}\nafter a swap each side: ${pct(g.netPct)} · ${gapWord(g)}`}>
    <span className="gp-sym"><b>${g.sym}</b><small>{g.n} pools</small></span>
    <span className="gp-rail" aria-hidden="true">
      <i className="gp-bridge"><s style={{ transform: `scaleX(${Math.max(0, 1 - cost / 100)})` }} /></i>
      {g.pools.map(p => <em key={p.pair} className={p.pair === g.lo.pair ? 'is-lo' : p.pair === g.hi.pair ? 'is-hi' : ''} style={{ left: `${Math.min(100, (p.at / span) * 100)}%` }} />)}
    </span>
    <span className="gp-nums"><Num v={g.gapPct} cls="gp-gap" /><small>net <Num v={g.netPct} cls={g.netPct > 0 ? 'is-up' : 'is-dn'} /></small></span>
    <span className="gp-side"><small>{g.lo.dex} → {g.hi.dex}</small><u className={g.open ? 'is-open' : ''}>{g.open ? `⏱ ${clock(g.openSec + age)}` : g.netPct > 0 ? 'confirming' : 'in costs'}</u></span>
  </li>;
}

export function PriceGaps() {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [age, setAge] = useState(0);
  useEffect(() => {
    let on = true;
    const go = () => sharedJson('/api/reputation/familia-pools/gaps', { maxAge: 55000 }).then(x => { if (on && x) { setD(x); setErr(false); setAge(0); } }).catch(() => on && setErr(true));
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); const c = setInterval(() => { if (!document.hidden) setAge(a => a + 1); }, 1000);
    return () => { on = false; clearInterval(t); clearInterval(c); };
  }, []);
  const rows = d?.gaps || [];
  return <section className="gp m-card" data-testid="price-gaps">
    <header className="gp-head">
      <span className="gp-title" data-tip="The same token, priced in every real pool it trades in (≥ $50K pool, ≥ $10K a day, trades this hour). Read-only — nothing here trades."><em>NIGHT VAULT · ADD-ON</em><b>📐 PRICE GAPS</b></span>
      <span className="gp-k" data-tip="Gaps that beat a swap's cost on each side on two reads in a row"><small>OPEN</small><b className="m-num">{d ? d.open : '…'}</b></span>
      <span className="gp-k" data-tip="Tokens the vault's pools hold, judged this minute"><small>TOKENS</small><b className="m-num">{d ? d.tokens : '…'}</b></span>
      <span className="gp-k" data-tip="What one swap costs (pool fee + slippage at a small size) — taken off each side"><small>COST / SIDE</small><b className="m-num">{d ? `${d.cost}%` : '…'}</b></span>
    </header>
    {rows.length ? <ol className="gp-rails">{rows.map((g, i) => <Rail key={g.mint} g={g} i={i} age={g.open ? age : 0} />)}</ol>
      : <p className="gp-wait">{err ? 'The price feed did not answer — trying again in a minute.' : d ? 'No token trades in two real pools right now.' : 'Pricing every pool…'}</p>}
    <p className="gp-use">⚡ Compound or enter through the <b className="is-lo">cheap</b> pool — Jupiter routes there for you. A gap that stays <b>open</b> is arbitrage volume: fees for the LPs of the <b className="is-hi">rich</b> side.</p>
  </section>;
}
