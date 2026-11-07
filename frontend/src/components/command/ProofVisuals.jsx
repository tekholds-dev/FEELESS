import React, { useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import '../../styles/proofVisuals.css';

// 🎬 One drawn demo per proof (owner 2026-11-07: "a unique demo of the best these agents can do... visual over bars and text"). Every number and word comes from real data: a real trade, live perps, live scores, today's trends. If it has none, it says so.
const parseGame = s => { const m = String(s).match(/^(\w+) (\w+) (\d+) at (\w+) (\d+), (.+)$/); return m ? { league: m[1], away: m[2], as: +m[3], home: m[4], hs: +m[5], when: m[6] } : null; };
const parseFund = s => { const m = String(s).match(/^(\w+) funding (-?[\d.]+)%\/h \((-?\d+)%\/yr pace\), open interest \$([\d.]+)([KMB]?)/); return m ? { sym: m[1], rate: +m[2], yr: +m[3], oi: +m[4] * ({ K: 1e3, M: 1e6, B: 1e9 }[m[5]] || 1) } : null; };
const parseLev = s => { const m = String(s).match(/^(\w+) mark \$([\d,.]+): 3x long \$([\d,.]+) \/ short \$([\d,.]+), 10x long \$([\d,.]+) \/ short \$([\d,.]+)/); const n = v => +String(v).replace(/,/g, ''); return m ? { sym: m[1], mark: n(m[2]), l3: n(m[3]), s3: n(m[4]), l10: n(m[5]), s10: n(m[6]) } : null; };
const compact = n => (n >= 1e9 ? `$${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${Math.round(n / 1e3)}K`);
const Empty = ({ what }) => <p className="pvz-empty" data-testid="pvz-empty">{what}</p>;

// ⛏ PoW: the real trade as a flight: stop below, target above, the line it really took, and the sites it really read as a film strip.
export function TradeFlight({ t, catId }) {
  if (!t?.line?.length) return <Empty what="No real PoW yet. Its first trade flies here." />;
  const W = 640; const H = 250; const up = (t.tp || 10) / 100; const dn = (t.sl || 6) / 100; const e = t.entry || t.line[0]; const top = Math.max(e * (1 + up), ...t.line); const low = Math.min(e * (1 - dn), ...t.line); const y = v => 18 + (H - 36) * (1 - (v - low) / Math.max(top - low, 1e-12)); const x = i => 16 + (W - 32) * (i / Math.max(1, t.line.length - 1)); const path = t.line.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' '); const won = t.pnl > 0; const q = agentAuthQuery();
  return <div className={`pvz pvz-flight${won ? ' is-won' : ' is-lost'}`} data-testid="pvz-pow"><svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`$${t.sym}: entry to exit, ${t.pnl}%`}><defs><linearGradient id="pvzFly" x1="0" x2="1"><stop offset="0" stopColor="#e7c36a" /><stop offset="1" stopColor={won ? '#15d16a' : '#ff8fa3'} /></linearGradient></defs>
    <line className="pvz-tp" x1="0" x2={W} y1={y(e * (1 + up))} y2={y(e * (1 + up))} /><text x="10" y={y(e * (1 + up)) - 6}>TARGET +{t.tp}%</text><line className="pvz-sl" x1="0" x2={W} y1={y(e * (1 - dn))} y2={y(e * (1 - dn))} /><text x="10" y={y(e * (1 - dn)) + 14}>STOP -{t.sl}%</text><line className="pvz-en" x1="0" x2={W} y1={y(e)} y2={y(e)} />
    <path className="pvz-path" d={path} pathLength="1" stroke="url(#pvzFly)" /><circle className="pvz-end" cx={x(t.line.length - 1)} cy={y(t.line[t.line.length - 1])} r="7" /></svg>
    <div className="pvz-big"><b className="m-num">${t.sym}</b><strong className="m-num">{t.pnl > 0 ? '+' : ''}{t.pnl}%</strong></div>
    {t.files?.length ? <ul className="pvz-film" aria-label="Sites it read before buying">{t.files.slice(0, 6).map((f, i) => <li key={f.file} style={{ '--i': i }} data-tip={`It read ${f.site}`}><img src={apiUrl(`/api/cats/${catId}/powshot/${t.id}/${f.file}?${q}`)} alt={f.site} loading="lazy" onError={e => { e.currentTarget.parentElement.style.display = 'none'; }} /></li>)}</ul> : null}</div>;
}
// 📉 PoP: every market a bubble, size is its open interest, colour is who pays. Under it, the liquidation ladder worked out live.
export function FundingSea({ kits }) {
  const rows = useMemo(() => kits.flatMap(k => k.fresh || []).map(parseFund).filter(Boolean).slice(0, 9), [kits]); const lev = useMemo(() => kits.flatMap(k => k.fresh || []).map(parseLev).filter(Boolean)[0], [kits]);
  if (!rows.length) return <Empty what="Live funding has not been read yet. It refreshes every 15 minutes." />;
  const most = Math.max(...rows.map(r => r.oi)); const hot = Math.max(...rows.map(r => Math.abs(r.yr)), 1); const span = lev ? lev.s3 - lev.l3 : 1; const at = v => (lev ? ((v - lev.l3) / span) * 100 : 0);
  return <div className="pvz pvz-sea" data-testid="pvz-pop"><div className="pvz-bubbles">{rows.map((r, i) => { const size = 62 + 96 * Math.sqrt(r.oi / most); const heat = Math.abs(r.yr) / hot; return <span key={r.sym} className={r.rate < 0 ? 'is-short' : 'is-long'} style={{ '--s': `${size}px`, '--h': heat, '--i': i }} data-tip={`${r.sym}: ${r.rate}%/h, ${r.yr}%/yr pace, ${compact(r.oi)} open. ${r.rate < 0 ? 'Shorts pay longs' : 'Longs pay shorts'}`}><b>{r.sym}</b><small className="m-num">{r.yr}%/yr</small></span>; })}</div>
    {lev ? <div className="pvz-ladder" data-tip="Where a position dies, from today's mark" role="img" aria-label={`${lev.sym} mark ${lev.mark}, 10x liquidates at ${lev.l10} and ${lev.s10}`}><i className="is-mark" style={{ left: `${at(lev.mark)}%` }}><b className="m-num">{lev.sym} ${lev.mark.toLocaleString()}</b></i>{[['3x', lev.l3], ['10x', lev.l10], ['10x', lev.s10], ['3x', lev.s3]].map(([l, v], n) => <i key={n} className="is-liq" style={{ left: `${at(v)}%` }}><small className="m-num">{l}</small></i>)}</div> : null}</div>;
}
// 🎲 PoB: tonight's real games on a stadium board. Finals show their score, the rest their start time.
export function ScoreBoard({ kits }) {
  const games = useMemo(() => kits.flatMap(k => k.fresh || []).map(parseGame).filter(Boolean).slice(0, 8), [kits]);
  if (!games.length) return <Empty what="No games have been read yet. ESPN refreshes every 15 minutes." />;
  return <div className="pvz pvz-board" data-testid="pvz-pob">{games.map((g, i) => { const done = /final/i.test(g.when); const live = g.as + g.hs > 0 && !done; return <article key={`${g.away}${g.home}${g.when}`} className={`${done ? 'is-final' : live ? 'is-live' : ''}`} style={{ '--i': i }} data-tip={`${g.league}: ${g.away} at ${g.home}, ${g.when}`}><em>{g.league}</em><div><b>{g.away}</b><strong className="m-num">{done || live ? g.as : ''}</strong></div><i aria-hidden="true">@</i><div><b>{g.home}</b><strong className="m-num">{done || live ? g.hs : ''}</strong></div><small className="m-num">{done ? 'FINAL' : g.when.replace(/^\d+\/\d+ - /, '')}</small></article>; })}</div>;
}
// 📣 PoC: today's real trends cut into a short, on a phone, with the timeline running under it. Each beat is a real headline.
export function ContentCut({ kits }) {
  const beats = useMemo(() => kits.filter(k => k.id === 'fl-trend').flatMap(k => k.fresh || []).map(x => String(x).replace(/^[^:]{0,30}:\s*/, '')).filter(Boolean).slice(0, 5), [kits]); const [at, setAt] = useState(0);
  useEffect(() => { if (beats.length < 2 || document.body.classList.contains('fx-lite') || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined; const t = setInterval(() => { if (!document.hidden) setAt(n => (n + 1) % beats.length); }, 2600); return () => clearInterval(t); }, [beats.length]);
  if (!beats.length) return <Empty what="Today's trends have not been read yet. They refresh every 15 minutes." />;
  return <div className="pvz pvz-cut" data-testid="pvz-poc"><div className="pvz-phone" aria-live="off"><div className="pvz-reel" key={at} style={{ '--hue': (at * 67 + 280) % 360 }}><i aria-hidden="true" /><b>{beats[at].slice(0, 70)}</b><small>Hook · beat {at + 1} of {beats.length}</small></div></div>
    <div className="pvz-time"><small className="m-label">TODAY'S TRENDS, CUT INTO A SHORT</small><div className="pvz-track" role="img" aria-label={`${beats.length} shots from today's trends`}>{beats.map((b, i) => <button key={b} type="button" className={i === at ? 'is-on' : ''} style={{ flex: 1 + (b.length % 4), '--hue': (i * 67 + 280) % 360 }} onClick={() => setAt(i)} data-tip={b} aria-label={`Shot ${i + 1}: ${b.slice(0, 40)}`} data-testid={`pvz-shot-${i}`} />)}</div><div className="pvz-track is-sound" aria-hidden="true">{Array.from({ length: 40 }, (_, i) => <s key={i} style={{ '--v': 0.2 + Math.abs(Math.sin(i * 1.7)) * 0.8 }} />)}</div></div></div>;
}
// 🧬 A proof's score as its own seal: each thing it was scored on is a spoke, and what is not known stays empty. Replaces rows of bars.
export function ProofSeal({ parts, rank, score, tone }) {
  const rows = (parts || []).slice(0, 8); const n = Math.max(3, rows.length); const pt = (i, r) => { const a = -Math.PI / 2 + (i / n) * Math.PI * 2; return [60 + Math.cos(a) * r, 60 + Math.sin(a) * r]; };
  const shape = rows.map((p, i) => pt(i, 8 + 42 * (Number(p.value) || 0)).map(v => v.toFixed(1)).join(',')).join(' ');
  return <span className={`pvz-seal is-${tone || 'open'}`} data-testid="pvz-seal"><svg viewBox="0 0 120 120" role="img" aria-label={`Rank ${rank}. ${rows.map(p => `${p.label} ${p.value == null ? 'not known' : Math.round(p.value * 100)}`).join(', ')}`}>{[20, 35, 50].map(r => <circle key={r} cx="60" cy="60" r={r} />)}{rows.map((p, i) => { const [x, y] = pt(i, 50); return <line key={p.label} x1="60" y1="60" x2={x} y2={y} className={p.value == null ? 'is-unknown' : ''}><title>{`${p.label}: ${p.value == null ? 'not known, scores nothing' : Math.round(p.value * 100)}`}</title></line>; })}<polygon points={shape} />{rows.map((p, i) => { const [x, y] = pt(i, 8 + 42 * (Number(p.value) || 0)); return p.value == null ? null : <circle key={p.label} className="pvz-dot" cx={x} cy={y} r="2.6"><title>{`${p.label}: ${Math.round(p.value * 100)}`}</title></circle>; })}</svg><b>{rank}</b>{score != null ? <small className="m-num">{Math.round(score)}</small> : null}</span>;
}
