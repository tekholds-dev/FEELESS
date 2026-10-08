import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { RowVitals } from './RowVitals';
import '../styles/coinVital.css';

// 🫀 THE VITAL (replaces the long chip row in pick lists; owner: "the long horizontal vitals aren't vital enough, try something else").
// One verdict you read in a second: a grade ring (A–F + score), four bars — 🧩 holders spread · 👤 dev share · 👥 crew record · 🌱 organic
// flow — and the THREE facts that decide it (bad first), plus a single stats line. Built from backend jup_audit.verdict (`r.vital`) on
// Jupiter's audit + our own scan; a coin not read yet falls back to the old chip line. A reading, never a promise.
const big = v => { const n = Number(v); if (!(n > 0)) return null; return n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : `$${Math.round(n)}`; };
const age = h => (h == null || !Number.isFinite(Number(h)) ? null : h < 1 ? `${Math.max(1, Math.round(h * 60))}m old` : h < 48 ? `${Number(h).toFixed(h < 10 ? 1 : 0)}h old` : `${Math.round(h / 24)}d old`);
export const BARS = [['flow', '🌱', 'Organic flow — share of volume from real traders, not bots'], ['growth', '📈', 'Growth — holders arriving this hour, net buyers, pool not drained'],
  ['holders', '🧩', 'Holders spread (top-10 share, bundles, insiders)'], ['dev', '👤', 'Dev share (lower is safer)'],
  ['crew', '👥', "Crew — the dev's launch record: how many of their coins graduated"]];

// 🎛 Sort + filter for pick lists (per viewer, remembered in this browser). Organic first by default (owner: "organic flow show first").
export const VSORTS = [['organic', '🌱 Organic first'], ['vital', '🫀 Best vital'], ['growth', '📈 Growing'], ['list', '≡ List order']];
export const VFILTERS = [['b', 'B+ only'], ['org', '🌱 10%+ organic'], ['serial', '☠ skip serial'], ['bots', '🤖 hide bots']];
const KEY = 'feeless.vitalView';
export const loadView = () => { try { return { sort: 'organic', on: {}, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; } catch { return { sort: 'organic', on: {} }; } };
export const saveView = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch { /* private window */ } };
const org = r => (r.vital?.organicPct ?? null);
export function applyView(rows, view) {
  const on = view?.on || {};
  let out = (rows || []).filter(r => {
    const v = r.vital; if (!v) return !(on.b || on.org);   // not read yet: kept unless a filter needs a reading
    if (on.b && v.score < 65) return false;
    if (on.org && !(org(r) >= 10)) return false;
    if (on.serial && v.crew?.kind === 'serial') return false;
    if (on.bots && org(r) != null && org(r) < 5) return false;
    return true; });
  const key = { organic: r => org(r) ?? -1, vital: r => r.vital?.score ?? -1, growth: r => r.vital?.bars?.growth ?? -1 }[view?.sort];
  if (key) out = out.map((r, i) => [r, i]).sort((a, b) => key(b[0]) - key(a[0]) || a[1] - b[1]).map(x => x[0]);
  return out;
}
export function VitalView({ view, onChange, count, total }) {
  const set = v => { onChange(v); saveView(v); };
  return <div className="cvl-view" data-testid="vital-view">
    <span className="m-seg cvl-sort" role="radiogroup" aria-label="Sort">{VSORTS.map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={view.sort === k} className={view.sort === k ? 'active' : ''} onClick={() => set({ ...view, sort: k })} data-testid={`vv-sort-${k}`}>{l}</button>)}</span>
    <span className="cvl-chips">{VFILTERS.map(([k, l]) => <button key={k} type="button" aria-pressed={!!view.on?.[k]} className={`cvl-chip ${view.on?.[k] ? 'on' : ''}`} onClick={() => set({ ...view, on: { ...view.on, [k]: !view.on?.[k] } })} data-testid={`vv-f-${k}`}>{l}</button>)}
      {total != null && <small className="m-dim">{count} of {total}</small>}</span>
  </div>;
}

export function statLine(r) {
  return [age(r.ageH), big(r.mcap) && `${big(r.mcap)} cap`, big(r.vol1h) && `${big(r.vol1h)}/h`, r.buyShare != null && `${Math.round(r.buyShare)}% buys`,
    Number(r.holders) > 0 && `${Number(r.holders).toLocaleString()} holders`, r.vital?.organicPct != null && `🌱 ${Math.round(r.vital.organicPct)}% organic`].filter(Boolean);
}

// 🗑 TRENCH VITAL (backend jup_audit.trench_verdict → row `tv`): the degen read for coins under 6h / on the curve / trench rows.
// 🔥 HEAT (is it sending: 5m pace, buyers, holders arriving, net buyers, a sane 5m candle) vs ☠ RUG (top-10, bundles, snipers, insiders, dev,
// serial launcher, bots, no socials, pool drain, minutes old, live authority) → one call. Ten-cell meters light up on arrival.
const Meter = ({ k, label, val }) => <span className={`tvl-m tvl-${k}`} data-tip={`${label} ${val == null ? 'not read yet' : `${val}/100`}`}>
  <span className="tvl-ml">{label}</span><span className="tvl-cells">{Array.from({ length: 10 }, (_, i) => <span key={i} className={`tvl-c ${val != null && val >= (i + 1) * 10 - 5 ? 'on' : ''}`} style={{ '--i': i }} />)}</span>
  <span className="tvl-mv">{val == null ? '—' : val}</span></span>;
// 📏 each call's own 1-hour record (backend _call_track → /fuses/call-proof), one shared read for every row
const CALL_KEY = { 'SEND IT': 'send', WATCH: 'watch', COLD: 'cold', 'RUG BAIT': 'bait', 'BOND RUN': 'bond', 'EARLY RUSH': 'rush', DUMPING: 'dump', 'SLOW CURVE': 'slow', 'BUY THE DIP': 'dip', 'FALLING KNIFE': 'knife', 'DEAD DIP': 'deaddip' };
const KIND_TIP = { trench: 'New-coin read: 🔥 heat (is it sending) vs ☠ rug risk.', curve: 'Curve read: 🎢 how far along its launch curve vs ⚡ pace (curve speed, 5-min volume, buyers).', dip: 'Dip read: 🧲 bounce (turning up, buyers back, holders arriving) vs 🔪 knife (still falling, sellers, holders leaving).' };
function useCallProof() {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; sharedJson('/api/reputation/fuses/call-proof', { maxAge: 120000 }).then(x => on && setD(x)).catch(() => {}); return () => { on = false; }; }, []);
  return d;
}
export const callRecord = (p, auto) => (!p || !p.n ? 'No calls settled yet — every call is noted and checked an hour later.'
  : `This call's record: ${p.medPct >= 0 ? '+' : ''}${p.medPct}% typical an hour later · ${p.wonPct}% up · ${p.n} settled.${auto ? ' The engine is taking these.' : ''}`);
export function TrenchVital({ r, mini = false }) {
  const cp = useCallProof();
  const t = r?.tv; if (!t) return null;
  const [ic, word, tone] = t.call || ['👀', 'WATCH', 'warn'];
  const meters = t.meters || [['🔥 HEAT', t.heat], ['☠ RUG', t.rug]];
  return <div className={`tvl tvl-${tone} tvl-k-${t.kind || 'trench'} ${mini ? 'is-mini' : ''}`} data-testid={`tvl-${r.symbol}`}>
    <span className={`tvl-call ${tone === 'good' ? 'is-send' : ''}`} data-tip={`${KIND_TIP[t.kind || 'trench']} ${callRecord(cp?.proof?.[CALL_KEY[word]], word === 'SEND IT' && cp?.auto)} A read for a small ticket, never a promise.`}>{ic} {word}</span>
    <span className="tvl-meters">{meters.map(([label, val], i) => <Meter key={label} k={i === 0 ? 'heat' : 'rug'} label={label} val={val} />)}</span>
    {!mini && t.tags?.length > 0 && <span className="tvl-tags">{t.tags.map(([i2, txt, tn]) => <span key={txt} className={`tvl-tag ${tn}`}>{i2} {txt}</span>)}
      {r.vital && <span className={`tvl-tag tvl-grade cvl-${r.vital.tone}`} data-tip={`Vital ${r.vital.score}/100 — ${r.vital.word}`}>🫀 {r.vital.grade}</span>}</span>}
  </div>;
}

export function CoinVital({ r, live = false }) {
  const v = r?.vital;
  if (r?.tv) return <TrenchVital r={r} />;   // a brand-new coin: the degen read decides more than spread / dev / crew
  if (!v) return <RowVitals r={r} live={live} />;
  const crew = v.crew || r.crew;
  return <div className={`cvl cvl-${v.tone}`} data-testid={`cvl-${r.symbol}`}>
    <span className="cvl-grade" data-tip={`Vital ${v.score}/100 — ${v.word}. Holders, dev, crew and organic flow, from Jupiter's audit + our own holder scan. A reading, never a promise.`}>
      <span className="cvl-g">{v.grade}</span><span className="cvl-s">{v.score}</span></span>
    <span className="cvl-bars" aria-label="Vital bars">{BARS.map(([k, ic, tip]) => { const x = Number(v.bars?.[k]); const val = Number.isFinite(x) ? x : 0.5;
      return <span key={k} className={`cvl-bar ${val >= 0.65 ? 'good' : val < 0.35 ? 'bad' : ''}`} data-tip={`${tip}: ${Math.round(val * 100)}%`}><span className="cvl-track"><span className="cvl-fill" style={{ transform: `scaleY(${Math.max(0.06, val)})` }} /></span><span className="cvl-ic">{ic}</span></span>; })}</span>
    <span className="cvl-body">
      <span className="cvl-top"><span className="cvl-word">{v.word}</span>{crew && crew.kind !== 'unknown' && <span className={`cvl-crew is-${crew.kind}`} data-tip={crew.why}>{crew.icon} {crew.label}</span>}</span>
      {v.flags?.length > 0 && <span className="cvl-flags">{v.flags.map(([ic, t, tone]) => <span key={t} className={`cvl-flag ${tone}`}>{ic} {t}</span>)}</span>}
      <span className="cvl-stats">{statLine(r).join(' · ')}</span>
    </span>
  </div>;
}

export default CoinVital;
