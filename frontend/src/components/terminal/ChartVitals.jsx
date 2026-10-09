import React, { useEffect, useRef, useState } from 'react';
import { usePumpProfile } from '../PumpProfile';
import { useCoinEdge } from '../../lib/coinEdge';
import { BsBar } from '../BsBar';
import { sharedJson } from '../../lib/sharedJson';
import { CoinVital, TrenchVital } from '../CoinVital';
import '../../styles/chartVitals.css';
import '../../styles/quickPulse.css';   // 🌊 the tape chip (sp-tape)

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

// 🫀 one coin's FEELESS edge (GET /api/reputation/coin-read/{mint}): its vital + the read that fits it — shared.
// ⏱ PER ACTIVITY (owner: "all vitals need to update per activity"): re-read at the coin's OWN pace (server `pace`: hot 5s · busy 10s ·
// quiet 20s) and at once when `kick` changes (the live price moved = someone traded), never faster than half its pace.
export const paceMs = d => Math.max(4000, Number(d?.pace?.everyMs) || 20000);
export function useCoinRead(mint, kick) {
  const [d, setD] = useState(null);
  const last = useRef(0); const every = useRef(20000); const loadRef = useRef(null);
  useEffect(() => {
    let alive = true; setD(null); last.current = 0; every.current = 20000;
    if (!mint) return undefined;
    let t = null;
    const load = (maxAge = Math.max(2500, every.current - 1500)) => { last.current = Date.now();
      return sharedJson(`/api/reputation/coin-read/${mint}`, { maxAge }).then(x => { if (!alive) return; every.current = paceMs(x); setD(x); }).catch(() => {}); };
    const loop = () => { t = setTimeout(() => { (document.hidden ? Promise.resolve() : load()).finally(() => alive && loop()); }, every.current); };
    loadRef.current = load;
    load().finally(() => alive && loop());
    return () => { alive = false; clearTimeout(t); loadRef.current = null; };
  }, [mint]);
  useEffect(() => { if (kick == null || !loadRef.current || document.hidden) return; if (Date.now() - last.current >= every.current / 2) loadRef.current(1500); }, [kick]);   /* a trade: only a read from the last 1.5s is shared */
  return d;
}

// The strip above a coin chart = THE FEELESS EDGE (owner, 2026-10-08: "the stuff on top of the chart isn't vitals to give the FEELESS edge"):
// status chips + socials, then the 🫀 vital (grade ring, five bars, the deciding facts, crew) beside the read that fits the coin (🔥 SEND IT ·
// 🎢 curve · 🧲 dip, with its meters and its own record), then one quiet line of plain numbers.
export function ChartVitals({ pair }) {
  const mint = pair?.baseToken?.address;
  const pump = usePumpProfile(mint);
  const edge = useCoinEdge(mint);
  const read = useCoinRead(mint, pair?.priceUsd);   /* ⏱ a new price = a trade: vitals re-read at the coin's pace */
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
      {read?.tape?.read && read.tape.read !== 'calm' && <span className={`m-chip sp-tape is-${read.tape.read}`} data-testid="cv-tape"
        data-tip={`The last 90 seconds of real swaps: $${Math.round(read.tape.buyUsd || 0)} bought vs $${Math.round(read.tape.sellUsd || 0)} sold over ${read.tape.n} trades, price ${read.tape.pxChg >= 0 ? '+' : ''}${(read.tape.pxChg || 0).toFixed(1)}%. The engine times its entries and sells into a buying climax on this read.`}>{read.tape.label}</span>}
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
    <div className="cv-nums">{nums.map(([k, v]) => <span key={k}><small>{k}</small> {v}</span>)}{mint && <BsBar mint={mint} />}</div>
  </div>;
}
