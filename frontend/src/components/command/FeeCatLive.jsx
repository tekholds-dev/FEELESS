// 🐱 FEE, LIVE (owner, 2026-10-18: "see how she thinks, double charts in her HQ, live realtime activity, learnings explicitly from G4 and OSSY"):
// two charts side by side (her open trades first, then the coins she would take next), each with HOW she read it (the setup, germ, higher /
// lower lows, the models' word), her moves as a live tape, and what she took from OSSY / G4. Drawn from the /admin/feecat payload only.
import React from 'react';
import { chartCalls } from './AgentCockpit';
import { avatarOf } from '../../lib/aiAvatars';
import { tapeRow } from '../../lib/feeTape';

const n = v => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const agoS = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - (n(t) > 1e12 ? n(t) / 1000 : n(t) || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
export const SETUP_WORD = { hhhl: '📈 HH/HL pullback', germ: '🦠 on its germ floor', fvg: '🪜 on its FVG support', breakout: '🚀 held breakout' };

// pure: what the two chart panes can show — her open trades first (with entry), then the coins she would take next
export function chartTargets(positions, top) {
  const out = []; const seen = new Set();
  (positions || []).forEach(p => { if (p.pairAddress && !seen.has(p.pairAddress)) { seen.add(p.pairAddress); out.push({ kind: 'open', pair: p.pairAddress, mint: p.mint, symbol: p.symbol, entry: n(p.entryPriceUsd), pct: n(p.currentChange), setups: p.setups || [], read: p.read, duo: p.duoAtEntry, why: p.reason }); } });
  (top || []).forEach(t => { if (t.pairAddress && !seen.has(t.pairAddress)) { seen.add(t.pairAddress); out.push({ kind: 'next', pair: t.pairAddress, mint: t.mint, symbol: t.symbol, setups: t.setups || [], read: t.read, duo: t.duo, why: t.reason }); } });
  return out;
}

// pure: HQ-only pins on her chart — the agents' verdict on the coin + OSSY / G4 / Reaper lines on it (users see only Fee's own calls)
export function deskPins(p, mint) {
  if (!p) return [];
  const a = p.agents; const out = chartCalls(p.duo, mint, a?.cap);
  if (a && Number(a.cap) > 0) out.unshift({ id: `ag-${mint}`, at: a.at, cap: Number(a.cap), who: 'Agents', kind: 'agent', action: a.status, text: `${a.status} · rank ${a.rank} — ${a.why}`, img: avatarOf('trigger') });
  return out;
}

// pure: her read of one coin in plain words (setup · germ · structure · the models)
export function readWords(t) {
  const r = t?.read || {}; const out = (t?.setups || []).map(k => SETUP_WORD[k]).filter(Boolean);
  if (r.germ != null) out.push(`germ ${r.germ > 0 ? '+' : ''}${r.germ}%`);
  if (r.hl || r.ll) out.push(`${r.hl} higher · ${r.ll} lower lows`);
  if (r.distHigh != null) out.push(`${r.distHigh}% under its high`);
  if (t?.duo) out.push(`🤝 ${t.duo.who} said ${t.duo.action}`);
  return out;
}

// (the two-chart 'HOW SHE SEES IT' panel is gone — her desk's two live windows (AgentLive) are her charts now, owner 2026-10-30)

// ⚡ One event → a row of chips (lib/feeTape.js — the public FeeCat page reads the same rows)
export { tapeRow };

function TapeChips({ r }) {
  return <span className="fcl-chips" data-tip={r.full}>
    {r.coin ? <i className="fcl-coin">${r.coin}</i> : null}
    {r.sol != null ? <i>{r.sol} SOL</i> : null}
    {r.move != null ? <i className={r.move >= 0 ? 'is-up' : 'is-dn'}>{r.move > 0 ? '+' : ''}{r.move}%</i> : null}
    {r.pnl != null ? <i className={`fcl-pnl ${r.pnl >= 0 ? 'is-up' : 'is-dn'}`}>{r.pnl >= 0 ? '+' : ''}{(+r.pnl).toFixed(4)} SOL</i> : null}
    {r.ai ? <i className="fcl-ai">🔮 FeeCat AI</i> : null}
    {r.tag ? <i className="fcl-tag">{r.tag}</i> : null}
  </span>;
}

export function FeeTape({ events }) {
  const ev = events || [];
  return <article className="fch-card fch-wide fcl-tape" data-testid="fcl-tape"><h4>⚡ LIVE ACTIVITY<small>{ev.length ? `newest ${agoS(ev[0].ts)} ago` : 'quiet'}</small></h4>
    {ev.length ? <ol>{ev.map((e, i) => <li key={e.id || i} className={`is-${String(e.type || '').toLowerCase()} ${i === 0 ? 'is-new' : ''}`}>
      <b>{e.type}</b><TapeChips r={tapeRow(e)} /><small>{agoS(e.ts)}</small></li>)}</ol> : <p className="fch-nil">no moves yet on this paper trail</p>}
  </article>;
}

export function DuoLearn({ learn }) {
  const rec = learn?.record || {}; const les = learn?.lessons || [];
  return <article className="fch-card" data-testid="fcl-learn"><h4>🎓 LEARNED FROM OSSY · G4<small>{learn?.at ? `${agoS(learn.at)} ago` : 'waiting on the first read'}</small></h4>
    <p className="fcl-rec">{['OSSY', 'G4'].map(k => { const r = rec[k] || {}; return <span key={k}><b>{k}</b><small>{r.n ? `${r.n} real trades · ${Math.round(n(r.won) || 0)}% won · avg ${n(r.med) >= 0 ? '+' : ''}${(n(r.med) || 0).toFixed(1)}%${n(r.usd) != null ? ` · ${n(r.usd) >= 0 ? '+' : '−'}$${Math.abs(n(r.usd)).toFixed(2)}` : ''}` : 'no closed trades yet'}</small></span>; })}</p>
    {les.length ? <ul className="fcl-les">{les.map((l, i) => <li key={`${l.who}-${l.at}-${i}`}><b>{l.who} · ${l.symbol}{n(l.pct) != null ? ` ${n(l.pct) >= 0 ? '+' : ''}${n(l.pct).toFixed(1)}%` : ''}</b><span>{l.lesson}</span></li>)}</ul>
      : <p className="fch-nil">each final review OSSY / G4 write lands here and in her activity as a 🎓 LEARN line</p>}
    <small className="fch-note">she copies their method — HH/HL pullbacks, the germ floor, held breakouts, never the gun line — and skips a coin either one just said SELL on</small>
  </article>;
}
