import React from 'react';
import { RowVitals } from './RowVitals';
import '../styles/coinVital.css';

// 🫀 THE VITAL (replaces the long chip row in pick lists; owner: "the long horizontal vitals aren't vital enough, try something else").
// One verdict you read in a second: a grade ring (A–F + score), four bars — 🧩 holders spread · 👤 dev share · 👥 crew record · 🌱 organic
// flow — and the THREE facts that decide it (bad first), plus a single stats line. Built from backend jup_audit.verdict (`r.vital`) on
// Jupiter's audit + our own scan; a coin not read yet falls back to the old chip line. A reading, never a promise.
const big = v => { const n = Number(v); if (!(n > 0)) return null; return n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : `$${Math.round(n)}`; };
const age = h => (h == null || !Number.isFinite(Number(h)) ? null : h < 1 ? `${Math.max(1, Math.round(h * 60))}m old` : h < 48 ? `${Number(h).toFixed(h < 10 ? 1 : 0)}h old` : `${Math.round(h / 24)}d old`);
export const BARS = [['holders', '🧩', 'Holders spread (top-10 share, bundles, insiders)'], ['dev', '👤', 'Dev share (lower is safer)'],
  ['crew', '👥', "Crew — the dev's launch record: how many of their coins graduated"], ['flow', '🌱', 'Organic flow — share of volume from real traders, not bots']];

export function statLine(r) {
  return [age(r.ageH), big(r.mcap) && `${big(r.mcap)} cap`, big(r.vol1h) && `${big(r.vol1h)}/h`, r.buyShare != null && `${Math.round(r.buyShare)}% buys`,
    Number(r.holders) > 0 && `${Number(r.holders).toLocaleString()} holders`].filter(Boolean);
}

export function CoinVital({ r, live = false }) {
  const v = r?.vital;
  if (!v) return <RowVitals r={r} live={live} />;
  const crew = v.crew || r.crew;
  return <div className={`cv cv-${v.tone}`} data-testid={`cv-${r.symbol}`}>
    <span className="cv-grade" data-tip={`Vital ${v.score}/100 — ${v.word}. Holders, dev, crew and organic flow, from Jupiter's audit + our own holder scan. A reading, never a promise.`}>
      <b>{v.grade}</b><small>{v.score}</small></span>
    <span className="cv-bars" aria-label="Vital bars">{BARS.map(([k, ic, tip]) => { const x = Number(v.bars?.[k]); const val = Number.isFinite(x) ? x : 0.5;
      return <span key={k} className={`cv-bar ${val >= 0.65 ? 'good' : val < 0.35 ? 'bad' : ''}`} data-tip={`${tip}: ${Math.round(val * 100)}%`}><i><em style={{ transform: `scaleY(${Math.max(0.06, val)})` }} /></i><small>{ic}</small></span>; })}</span>
    <span className="cv-body">
      <span className="cv-top"><b className="cv-word">{v.word}</b>{crew && crew.kind !== 'unknown' && <i className={`cv-crew is-${crew.kind}`} data-tip={crew.why}>{crew.icon} {crew.label}</i>}</span>
      {v.flags?.length > 0 && <span className="cv-flags">{v.flags.map(([ic, t, tone]) => <i key={t} className={tone}>{ic} {t}</i>)}</span>}
      <small className="cv-stats">{statLine(r).join(' · ')}</small>
    </span>
  </div>;
}

export default CoinVital;
