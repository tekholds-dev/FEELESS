import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { CardFx } from './CardFx';
import '../styles/pumpProfile.css';

const big = v => { const n = Number(v); if (!(n > 0)) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
const age = h => h == null ? '—' : h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)}h` : `${Math.round(h / 24)}d`;
const short = a => a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '';
const LINK = { x: '𝕏', telegram: '✈ Telegram', website: '🌐 Website' };
const cache = new Map();   // mint → {at, data}: one read a minute per coin, shared by the page, the drawer and the chart

export function usePumpProfile(mint) {
  const [p, setP] = useState(() => cache.get(mint)?.data || null);
  useEffect(() => {
    if (!mint) return undefined;
    let alive = true;
    const load = () => {
      const hit = cache.get(mint);
      if (hit && Date.now() - hit.at < 60000) { setP(hit.data); return; }
      fetch(apiUrl(`/api/reputation/pump-profile/${mint}`)).then(r => (r.ok ? r.json() : {})).then(d => { cache.set(mint, { at: Date.now(), data: d?.mint ? d : {} }); if (alive) setP(d?.mint ? d : {}); }).catch(() => alive && setP({}));
    };
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [mint]);
  return p;
}

// 🟢 The coin's FULL Pump profile, wherever a coin is opened (coin page, coin drawer, war room chart): who it is, its links,
// its creator, graduated or still on the curve, cap against its all-time high, the hour's volume, replies, live stream.
// Renders nothing for a coin Pump has no record of. `compact` = the drawer / chart strip.
export function PumpProfile({ mint, compact = false }) {
  const p = usePumpProfile(mint);
  if (!p?.mint) return null;
  const off = p.offAthPct;
  const tiles = [['MARKET CAP', big(p.mcapUsd)], ['ALL-TIME HIGH', big(p.athUsd)], ['FROM ATH', off == null ? '—' : `${off >= 0 ? '+' : ''}${off.toFixed(0)}%`, off != null && off <= -50 ? 'bad' : ''],
    ['1H VOLUME', big(p.vol1hUsd)], ['POOL', big(p.liqUsd)], ['AGE', age(p.ageH)]];
  return <section className={`pp m-card cfx-host ${compact ? 'is-compact' : ''}`} data-testid="pump-profile">
    <CardFx kind="beam" tone={off != null && off <= -70 ? 'down' : undefined} />
    <header className="pp-head">
      {p.image ? <img className="pp-logo" src={p.image} alt="" loading="lazy" onError={e => { e.currentTarget.style.visibility = 'hidden'; }} /> : <span className="pp-logo pp-glyph">{p.symbol.slice(0, 2)}</span>}
      <div className="pp-id"><b>${p.symbol} <small>{p.name}</small></b>
        <span className="pp-chips"><span className={`m-chip ${p.graduated ? 'is-grad' : 'is-curve'}`} data-tip={p.graduated ? 'Bonded: it left Pump\'s launch curve and trades in a real pool' : 'Still on Pump\'s launch curve — no pool yet'}>{p.graduated ? '🎓 graduated' : '📈 on the curve'}</span>
          {p.live && <span className="m-chip is-live" data-tip="The creator is streaming on Pump right now">🔴 live</span>}
          {p.verified && <span className="m-chip" data-tip="Marked verified by Pump">✔ verified</span>}
          {p.cashback && <span className="m-chip" data-tip="Pump cashback is on for this coin">💸 cashback</span>}
          {p.banned && <span className="m-chip is-bad" data-tip="Pump has banned this coin">⛔ banned</span>}
          <span className="m-chip" data-tip="Replies on its Pump page">💬 {p.replies}</span></span></div>
    </header>
    {p.description && !compact && <p className="pp-desc">{p.description}</p>}
    <div className="pp-tiles">{tiles.map(([l, v, bad], i) => <div key={l} className={bad || ''} style={{ '--i': i }}><small className="m-label">{l}</small><b className="m-num">{v}</b></div>)}</div>
    <footer className="pp-foot">
      {p.links.map(x => <a key={x.url} className="m-btn" href={x.url} target="_blank" rel="noopener noreferrer">{LINK[x.type] || x.type}</a>)}
      {!p.links.length && <small className="m-dim" data-tip="The creator set no website, X or Telegram on Pump">no links set</small>}
      {p.creator && <a className="m-btn pp-dev" href={`/terminal/profile/${p.creator}`} data-tip="Open the creator's FEELESS case file">👤 dev {short(p.creator)}</a>}
      <a className="m-btn pp-out" href={p.url} target="_blank" rel="noopener noreferrer">Pump ↗</a>
    </footer>
  </section>;
}
