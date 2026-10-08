import React, { useEffect, useState } from 'react';
import { usePumpProfile } from '../PumpProfile';
import { useCoinEdge, fetchEdgeIntel } from '../../lib/coinEdge';
import '../../styles/chartVitals.css';

// 🧬 The strip under a coin chart's title: its socials, the vitals a trader checks first (cap, 1h volume, pool, age, top-10,
// dev, insiders, buyers) and the Pump radar (5m flow + FEELESS read). Reads the SAME shared pollers as everything else
// (usePumpProfile · useCoinEdge · one intel scan per coin per minute) — no poller of its own.
const big = v => { const n = Number(v); if (!(n > 0)) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1)}K` : `$${n.toFixed(0)}`; };
const ageOf = ms => { if (!ms) return '—'; const h = (Date.now() - ms) / 36e5; return h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)}h` : `${Math.round(h / 24)}d`; };
const pct = v => (Number.isFinite(Number(v)) && v !== null ? `${Number(v).toFixed(Number(v) < 10 ? 1 : 0)}%` : '—');
const move = v => (Number.isFinite(Number(v)) && v !== null ? `${v >= 0 ? '+' : ''}${Number(v).toFixed(Math.abs(v) < 100 ? 1 : 0)}%` : '—');
const SOC = { x: ['𝕏', 'X / Twitter'], twitter: ['𝕏', 'X / Twitter'], telegram: ['✈', 'Telegram'], website: ['🌐', 'Website'], discord: ['💬', 'Discord'] };

export function socialsOf(pair, pump) {
  const out = []; const seen = new Set();
  const add = (type, url) => {
    if (!/^https?:\/\//i.test(url || '')) return;
    const k = SOC[type] ? type.replace('twitter', 'x') : 'website';
    if (seen.has(k)) return; seen.add(k); out.push({ type: k, url });
  };
  (pump?.links || []).forEach(l => add(l.type, l.url));
  (pair?.info?.socials || []).forEach(s => add(s.type, s.url));
  (pair?.info?.websites || []).forEach(w => add('website', w.url));
  return out;
}

export function ChartVitals({ pair }) {
  const mint = pair?.baseToken?.address;
  const pump = usePumpProfile(mint);
  const edge = useCoinEdge(mint);
  const [intel, setIntel] = useState(null);
  useEffect(() => {
    let alive = true; setIntel(null);
    if (mint) fetchEdgeIntel(mint).then(i => alive && setIntel(i)).catch(() => {});
    return () => { alive = false; };
  }, [mint]);
  if (!pair) return null;
  const socials = socialsOf(pair, pump);
  const t10 = intel?.top10Pct; const dev = intel?.devHoldingPct; const ins = intel?.insidersHoldingPct;
  const pulse = edge?.pulse; const run = edge?.runner;
  const buys = Number.isFinite(pulse?.buyShare) ? pulse.buyShare : null;
  const vit = [
    ['CAP', big(pair.marketCap ?? pair.fdv ?? pump?.mcapUsd), '', 'Market cap right now'],
    ['1H VOL', big(pair.volume?.h1 ?? pump?.vol1hUsd), '', 'Traded in the last hour'],
    ['POOL', big(pair.liquidity?.usd ?? pump?.liqUsd), '', 'Liquidity in the pool: what a sale can really get'],
    ['AGE', ageOf(pair.pairCreatedAt) !== '—' ? ageOf(pair.pairCreatedAt) : (pump?.ageH != null ? `${pump.ageH.toFixed(1)}h` : '—'), '', 'Time since the pool opened'],
    ['TOP 10', pct(t10), t10 > 30 ? 'bad' : t10 != null && t10 < 20 ? 'good' : '', 'Share of the supply held by the 10 biggest wallets (lower = safer)'],
    ['DEV', pct(dev), dev > 10 ? 'bad' : dev != null && dev <= 3 ? 'good' : '', 'Share the creator still holds'],
    ['INSIDERS', pct(ins), ins > 15 ? 'bad' : ins != null && ins < 5 ? 'good' : '', 'Share held by wallets that were in at the start'],
    ['BUYERS 5M', buys == null ? '—' : `${buys}%`, buys != null && buys >= 55 ? 'good' : buys != null && buys < 45 ? 'bad' : '', 'Share of the last 5 minutes\' trades that were buys'],
  ];
  const off = pump?.offAthPct;
  return <div className="cv" data-testid="chart-vitals">
    <div className="cv-row cv-top">
      {pump?.mint && <span className={`m-chip ${pump.graduated ? 'is-grad' : 'is-curve'}`} data-tip={pump.graduated ? 'Bonded: it left Pump\'s launch curve' : 'Still on Pump\'s launch curve'}>{pump.graduated ? '🎓 graduated' : '📈 on the curve'}</span>}
      {run?.lane && <span className="m-chip" data-tip="The Fuse Runners lane this coin would play in">{run.lane}</span>}
      {edge?.snipersOut && <span className="m-chip is-grad" data-tip="Every flagged sniper has sold out">🎯 snipers out</span>}
      {edge?.verify && ['gold', 'verified'].includes(edge.verify.level) && <span className="m-chip is-grad" data-tip="FEELESS verified">✔ verified</span>}
      {run && run.passing === false && <span className="m-chip is-bad" data-tip={(run.gates || []).join(' · ')}>⚠ fails {run.gates?.[0] ? run.gates[0].split(' ').slice(0, 3).join(' ') : 'a gate'}</span>}
      {off != null && <span className={`m-chip ${off <= -50 ? 'is-bad' : ''}`} data-tip="Market cap against its all-time high on Pump">{move(off)} from ATH</span>}
      <span className="cv-soc">
        {socials.map(s => <a key={s.type} className="m-btn cv-link" href={s.url} target="_blank" rel="noopener noreferrer" data-tip={SOC[s.type]?.[1] || 'Website'} aria-label={SOC[s.type]?.[1] || 'Website'}>{SOC[s.type]?.[0] || '🌐'}</a>)}
        {!socials.length && <small className="m-dim" data-tip="No website, X or Telegram was set for this coin">no socials set</small>}
        {pump?.creator && <a className="m-btn cv-link cv-dev" href={`/terminal/profile/${pump.creator}`} data-tip="Open the creator's FEELESS case file">👤 dev</a>}
        {pump?.url && <a className="m-btn cv-link" href={pump.url} target="_blank" rel="noopener noreferrer" data-tip="This coin on pump.fun">Pump ↗</a>}
      </span>
    </div>
    <div className="cv-grid">{vit.map(([l, v, tone, tip], i) => <div key={l} className={`cv-t ${tone}`} data-tip={tip} style={{ '--i': i }}><small className="m-label">{l}</small><b>{v}</b></div>)}</div>
    <div className="cv-radar" data-testid="chart-pump-radar" data-tip="Pump radar: the last 5 minutes of flow on this coin">
      <span className="m-label">📡 PUMP RADAR · 5M</span>
      {pulse ? <>
        <span className={`cv-mv ${pulse.m5Change >= 0 ? 'up' : 'down'}`}>{move(pulse.m5Change)}</span>
        <span className="cv-bar" aria-hidden="true"><i style={{ transform: `scaleX(${(buys ?? 50) / 100})` }} /></span>
        <small>{buys ?? '—'}% buys · {pulse.buys + pulse.sells} trades · {big(pulse.volumeM5)}</small>
      </> : <small className="m-dim">reading flow…</small>}
      {run?.score != null && <span className="m-chip" data-tip="FEELESS runner score, 0–100, with cited parts in the case file">score {Math.round(run.score)}</span>}
    </div>
  </div>;
}
