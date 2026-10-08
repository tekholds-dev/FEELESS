import React, { useEffect, useState } from 'react';
import { usePumpProfile } from '../PumpProfile';
import { useCoinEdge } from '../../lib/coinEdge';
import { sharedJson } from '../../lib/sharedJson';
import { CoinVital, TrenchVital } from '../CoinVital';
import '../../styles/chartVitals.css';

const big = v => { const n = Number(v); if (!(n > 0)) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1)}K` : `$${n.toFixed(0)}`; };
const ageOf = ms => { if (!ms) return '—'; const h = (Date.now() - ms) / 36e5; return h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)}h` : `${Math.round(h / 24)}d`; };
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

// 🫀 one coin's FEELESS edge (GET /api/reputation/coin-read/{mint}): its vital + the read that fits it — shared, re-read every 20s
export function useCoinRead(mint) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true; setD(null);
    if (!mint) return undefined;
    const load = () => sharedJson(`/api/reputation/coin-read/${mint}`, { maxAge: 15000 }).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000);
    return () => { alive = false; clearInterval(t); };
  }, [mint]);
  return d;
}

// The strip above a coin chart = THE FEELESS EDGE (owner, 2026-10-08: "the stuff on top of the chart isn't vitals to give the FEELESS edge"):
// status chips + socials, then the 🫀 vital (grade ring, five bars, the deciding facts, crew) beside the read that fits the coin (🔥 SEND IT ·
// 🎢 curve · 🧲 dip, with its meters and its own record), then one quiet line of plain numbers.
export function ChartVitals({ pair }) {
  const mint = pair?.baseToken?.address;
  const pump = usePumpProfile(mint);
  const edge = useCoinEdge(mint);
  const read = useCoinRead(mint);
  if (!pair) return null;
  const socials = socialsOf(pair, pump);
  const pulse = edge?.pulse; const run = edge?.runner;
  const off = pump?.offAthPct;
  const sym = pair.baseToken?.symbol || 'COIN';
  const row = { ...(read?.row || {}), symbol: sym, vital: read?.vital, tv: read?.tv, mcap: pair.marketCap ?? pair.fdv ?? pump?.mcapUsd, vol1h: pair.volume?.h1 ?? pump?.vol1hUsd,
    ageH: read?.row?.ageH ?? (pair.pairCreatedAt ? (Date.now() - pair.pairCreatedAt) / 36e5 : pump?.ageH), buyShare: pulse?.buyShare ?? read?.row?.buyShare };
  const nums = [['cap', big(row.mcap)], ['1h', big(row.vol1h)], ['pool', big(pair.liquidity?.usd ?? pump?.liqUsd)], ['age', ageOf(pair.pairCreatedAt) !== '—' ? ageOf(pair.pairCreatedAt) : (pump?.ageH != null ? `${pump.ageH.toFixed(1)}h` : '—')],
    ['5m', pulse ? `${move(pulse.m5Change)} · ${pulse.buys + pulse.sells} trades` : '—']];
  return <div className="cv" data-testid="chart-vitals">
    <div className="cv-row cv-top">
      {pump?.mint && <span className={`m-chip ${pump.graduated ? 'is-grad' : 'is-curve'}`} data-tip={pump.graduated ? 'Bonded: it left Pump\'s launch curve' : 'Still on Pump\'s launch curve'}>{pump.graduated ? '🎓 graduated' : '📈 on the curve'}</span>}
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
    <div className="cv-edge" data-testid="chart-edge">
      {read ? <>{row.vital && <CoinVital r={row} only="vital" />}{row.tv && <TrenchVital r={row} />}
        {!row.vital && !row.tv && <small className="m-dim">No FEELESS read for this coin yet.</small>}</> : <small className="m-dim cv-reading">reading the FEELESS edge…</small>}
    </div>
    <div className="cv-nums">{nums.map(([k, v]) => <span key={k}><small>{k}</small> {v}</span>)}</div>
  </div>;
}
