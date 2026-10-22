import React from 'react';

// 🧭 The HUD around the Familia cities: the five-city rail (Fee City the widest) (the street chat lives in StreetChat.jsx),
// Call-of-Duty style rank emblems (drawn: a shield, chevrons for the division, a crown for the Dons) and the ranked ladder.
const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
const DIV = { III: 1, II: 2, I: 3 };

export function RankBadge({ rank, size = 'md' }) {
  if (!rank) return null;
  const don = String(rank.div || '').startsWith('#');
  return <span className={`fh-emb t-${rank.tier} s-${size} ${don ? 'is-don' : ''}`} data-tip={`${rank.name} ${rank.div}${rank.next ? ` · next division at ${n(rank.next)} power` : ''}`} data-testid="rank-badge">
    <i aria-hidden="true">{don ? <b className="fh-crown" /> : Array.from({ length: DIV[rank.div] || 1 }, (_, k) => <b key={k} className="fh-chev" />)}</i>
    {size !== 'sm' ? <span><em>{rank.name}</em><small>{rank.div}</small></span> : null}</span>;
}

export function CityRail({ cities, city, onGo }) {
  return <nav className="fh-rail" role="tablist" aria-label="Cities" data-testid="city-rail">{(cities || []).map((c, i) => <button key={c.key} type="button" role="tab" aria-selected={city === c.key}
    className={`fh-city k-${c.key} ${city === c.key ? 'active' : ''}`} style={{ '--i': i }} onClick={() => onGo(c.key)} data-testid={`city-${c.key}`} data-tip={`${c.name} — ${c.vibe}`}>
    <b>{c.name}</b><small>{c.vibe}</small><u><s style={{ transform: `scaleX(${c.plots ? Math.max(0.02, c.held / c.plots) : 0})` }} /></u><em key={c.held}>{c.held}/{c.plots} held</em></button>)}</nav>;
}

export function RankLadder({ ranked, mine }) {
  const top = Math.max(1, ...(ranked || []).map(r => r.power || 0));
  return <section className="fh-ladder m-card" data-testid="rank-ladder">
    <header><span className="m-label">🎖 RANKED · FAMILY POWER</span><small>Street Rat → Kingpin in three divisions each · the top 25 Kingpins are Dons of Fee City</small></header>
    {(ranked || []).length ? <ol>{ranked.map((r, i) => <li key={r.id} className={r.id === mine ? 'is-mine' : ''} style={{ '--i': i }}>
      <b className="fh-place">{r.place}</b><RankBadge rank={r.rank} size="sm" /><span><em>[{r.tag}] {r.name}</em><small>{r.rank.name} {r.rank.div}</small></span>
      <u><s style={{ transform: `scaleX(${Math.max(0.02, (r.power || 0) / top)})` }} /></u><strong key={r.power}>{n(r.power)}</strong></li>)}</ol>
      : <p className="m-dim">No families ranked yet — the first Don takes the city.</p>}
  </section>;
}
