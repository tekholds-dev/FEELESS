import React, { useMemo, useState } from 'react';
import '../styles/realtor.css';

// 🏷 THE REALTOR (owner P1 #3: "space for users to buy without clutter — a for-sale district per city, plot tiers"): every FREE plot, city by
// city, sorted into tiers by its borough (PRIME · UPTOWN · MIDTOWN · BACKSTREET), each a drawn lot sign with its MP price for YOUR family,
// whether the bank covers it, 📍 fly to it and one-tap Buy (the same `buy` act as the map — the Don / Underboss's call, points only).
export const TIERS = [['prime', 'PRIME', 2.0, '#ffd36b'], ['uptown', 'UPTOWN', 1.3, '#b388ff'], ['midtown', 'MIDTOWN', 0.95, '#45e4c8'], ['back', 'BACKSTREET', 0, '#ff9f45']];
export const tierOf = t => TIERS.find(([, , min]) => (Number(t) || 0) >= min) || TIERS[TIERS.length - 1];
const mp = x => Math.round(Number(x) || 0).toLocaleString('en-US');
// pure: one city's free plots → [{tier, plots: [{id, borough, name, mp, ok}]}] (cheapest first inside a tier, empty tiers left out)
export function forSale(v, cityKey) {
  const c = (v?.cities || []).find(x => x.key === cityKey); if (!c) return [];
  const bor = Object.fromEntries((v.boroughs || []).map(b => [b.key, b]));
  const bank = v.me?.bank || 0; const prices = v.me?.prices || {};
  const free = (v.blocks || []).filter(b => c.boroughs.includes(b.b) && !b.owner);
  const out = TIERS.map(t => ({ tier: t, plots: [] }));
  free.forEach(b => { const bo = bor[b.b] || {}; const t = tierOf(bo.tier); const price = prices[b.id];
    out.find(x => x.tier[0] === t[0]).plots.push({ id: b.id, borough: b.b, name: bo.name || b.b, icon: bo.icon, tierMul: bo.tier, mp: price, ok: price != null && price <= bank }); });
  out.forEach(x => x.plots.sort((a, b) => (a.mp ?? 9e15) - (b.mp ?? 9e15)));
  return out.filter(x => x.plots.length);
}

export function Realtor({ v, act, busy, onFly }) {
  const [city, setCity] = useState(() => (v?.cities || []).find(c => c.plots > c.held)?.key || 'fee');
  const groups = useMemo(() => forSale(v, city), [v, city]);
  const me = v?.me; const turfMax = v?.rules?.turfMax || 12; const turf = (me?.turf || []).length;
  const full = me && turf >= turfMax;
  return <section className="rl" data-testid="realtor">
    <header className="rl-head"><span><em>FOR SALE · EVERY CITY</em><b>🏷 THE REALTOR</b></span>
      {me ? <span className="rl-bank" data-tip="Your family bank — plots are paid in MP"><em>BANK</em><b>{mp(me.bank)} MP</b><small>turf {turf}/{turfMax}</small></span>
        : <span className="rl-bank is-off"><b>Join a family to buy</b></span>}</header>
    <div className="m-seg rl-cities" role="radiogroup" aria-label="City">{(v?.cities || []).map(c => <button key={c.key} type="button" role="radio" aria-checked={city === c.key} className={city === c.key ? 'active' : ''}
      onClick={() => setCity(c.key)} data-tip={`${c.name}: ${c.plots - c.held} of ${c.plots} plots free`} data-testid={`rl-city-${c.key}`}>{c.name}<small>{c.plots - c.held} free</small></button>)}</div>
    {full ? <p className="rl-note">Your family holds {turf}/{turfMax} turf — sell a block before buying another.</p> : null}
    {!groups.length ? <p className="rl-note">Sold out — every plot in this city is held. Raid one, or try another city.</p> : null}
    {groups.map(({ tier: [k, label, , col], plots }) => <div key={k} className={`rl-tier k-${k}`} style={{ '--tc': col }} data-testid={`rl-tier-${k}`}>
      <p className="rl-tlabel"><b>{label}</b><small>{plots.length} plot{plots.length === 1 ? '' : 's'} · from {plots[0].mp != null ? `${mp(plots[0].mp)} MP` : '—'}</small></p>
      <ol className="rl-lots">{plots.slice(0, 12).map((p, i) => <li key={p.id} className={`rl-lot ${p.ok ? 'is-ok' : ''}`} style={{ '--i': i }} data-testid={`rl-lot-${p.id}`}>
        <span className="rl-sign" aria-hidden="true"><i /><b>SOLD?</b></span>
        <span className="rl-id"><b>{p.id}</b><small>{p.icon} {p.name} · ×{p.tierMul}</small></span>
        <strong className="m-num">{p.mp != null ? `${mp(p.mp)} MP` : '—'}</strong>
        <span className="rl-acts">{onFly ? <button type="button" className="m-btn" onClick={() => onFly(p.id)} data-tip="Fly the city camera to this plot" aria-label={`Fly to ${p.id}`}>📍</button> : null}
          <button type="button" className="m-btn m-go" disabled={busy || !me || !p.ok || full} onClick={() => act({ act: 'buy', block: p.id }, `Bought ${p.id}`)}
            data-tip={!me ? 'Join a family first' : !p.ok ? `Needs ${mp((p.mp || 0) - (me.bank || 0))} more MP in the bank` : `Buy ${p.id} for ${mp(p.mp)} MP (Don / Underboss)`} data-testid={`rl-buy-${p.id}`}>Buy</button></span></li>)}</ol>
      {plots.length > 12 ? <p className="rl-note">+{plots.length - 12} more in this tier — the cheapest are listed first.</p> : null}
    </div>)}
  </section>;
}
