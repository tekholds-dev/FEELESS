import React from 'react';
import { useCoinRead } from './ChartVitals';
import { SocialIcons } from '../QuickPulse';
import '../../styles/chartPulse.css';

const TONE = { good: 'is-good', warn: 'is-warn', bad: 'is-bad' };

// 🫀 THE FEELESS VITAL on every chart (owner, 2026-10-11: "add one unique vital to all charts"): the coin's vital grade ring (A–F + score),
// the read that fits it (🔥 SEND IT · 🧊 COLD · 🧲 BUY THE DIP …) and a heartbeat that beats on every REAL trade the chart receives (`beat` =
// the live price — a new value = a trade). One shared, activity-paced read per coin (`useCoinRead`); nothing is invented — no read = no badge.
// 🔗 the coin's own links on every chart (owner, 2026-10-16: "socials on charts") — the read's facts first (Jupiter / Pump), the board row after
export const socOf = (mint, r) => { const f = r?.facts || {}; const w = r?.row || {}; return { mint, site: f.site || w.site, x: f.x || w.x, tg: f.tg || w.tg }; };

export function ChartPulse({ mint, beat }) {
  const r = useCoinRead(mint, beat);
  const v = r?.vital; const call = r?.tv?.call;
  if (!mint || !v) return null;
  const tip = [`FEELESS vital ${v.grade} · ${v.score}/100 — ${v.word}`, ...(v.flags || []).map(f => `${f[0]} ${f[1]}`), call ? `read: ${call[0]} ${call[1]}` : null].filter(Boolean).join(' · ');
  return <div className={`cpl ${TONE[v.tone] || ''}`} data-testid="chart-pulse" data-tip={tip}>
    <span className="cpl-ring" style={{ '--cpl-k': Math.max(0, Math.min(100, Number(v.score) || 0)) / 100 }}><b>{v.grade}</b></span>
    <span className="cpl-txt"><small>🫀 FEELESS VITAL</small><em>{v.score}<u>/100</u>{call ? <i className={TONE[call[2]] || ''}>{call[0]} {call[1]}</i> : null}</em></span>
    <span className="cpl-soc"><SocialIcons r={socOf(mint, r)} /></span>
    <i className="cpl-beat" key={String(beat)} aria-hidden />
  </div>;
}
