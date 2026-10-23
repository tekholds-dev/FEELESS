// 🐱 FEE, LIVE (owner, 2026-10-18: "see how she thinks, double charts in her HQ, live realtime activity, learnings explicitly from G4 and OSSY"):
// two charts side by side (her open trades first, then the coins she would take next), each with HOW she read it (the setup, germ, higher /
// lower lows, the models' word), her moves as a live tape, and what she took from OSSY / G4. Drawn from the /admin/feecat payload only.
import React, { useMemo, useState } from 'react';
import { useLivePrices } from '../../lib/livePrices';
import { chartCalls } from './AgentCockpit';
import { avatarOf } from '../../lib/aiAvatars';
import { tapeRow } from '../../lib/feeTape';

const PriceChart = React.lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
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

function Pane({ list, idx, setIdx, pins }) {
  const t = list[idx];
  const live = useLivePrices(t?.pair ? [t.pair] : []);
  const calls = useMemo(() => deskPins(pins?.[t?.mint], t?.mint), [pins, t?.mint]);
  if (!t) return <div className="fcl-pane is-empty"><p>no coin to chart yet — she charts her open trades first, then her next picks</p></div>;
  const lp = live.get(t.pair);   /* 📍 pins sit at a market cap — the chart needs the live cap or they land off the scale (they never showed) */
  const pair = { chainId: 'solana', pairAddress: t.pair, baseToken: { address: t.mint, symbol: t.symbol }, priceUsd: lp?.price || undefined, marketCap: lp?.mc || undefined };
  return <div className={`fcl-pane is-${t.kind}`} data-testid="fcl-pane">
    <header><select className="m-input" value={idx} onChange={e => setIdx(Number(e.target.value))} aria-label="Coin on this chart">
      {list.map((x, i) => <option key={x.pair} value={i}>{x.kind === 'open' ? '📂' : '⏭'} ${x.symbol}{x.pct != null ? ` ${x.pct >= 0 ? '+' : ''}${x.pct.toFixed(1)}%` : ''}</option>)}</select>
      <b className={t.kind === 'open' ? (t.pct >= 0 ? 'm-pos' : 'm-neg') : ''}>{t.kind === 'open' ? `HOLDING${t.pct != null ? ` ${t.pct >= 0 ? '+' : ''}${t.pct.toFixed(1)}%` : ''}` : 'NEXT UP'}</b></header>
    <div className="fcl-chart"><React.Suspense fallback={<p className="fcl-wait">loading chart…</p>}>
      <PriceChart key={t.pair} pair={pair} interval="1m" metric="marketCap" showVolume={false} userEntry={t.entry || null} wallets={false} callouts={calls} />
    </React.Suspense></div>
    <p className="fcl-read" data-testid="fcl-read">{readWords(t).map(w => <span key={w}>{w}</span>)}{!readWords(t).length ? <span>no chart read yet — her own lanes decided</span> : null}</p>
    {t.why ? <small className="fcl-why" data-tip={String(t.why)}>{/FeeCat AI|NEXA/i.test(t.why) ? '🔮 FeeCat AI call · ' : ''}{String(t.why).split(/[;·]/)[0].replace(/🔮 FeeCat AI|🪟 ?NEXA/g, '').trim().slice(0, 60)}</small> : null}
  </div>;
}

export function FeeCharts({ d }) {
  const list = useMemo(() => chartTargets(d?.cat?.positions, d?.scan?.top), [d]);
  const [a, setA] = useState(0); const [b, setB] = useState(1);
  return <article className="fch-card fch-wide fcl" data-testid="fcl-charts"><h4>📈 HOW SHE SEES IT<small>{list.length} coins · 🐱 her calls · 🤖 the agents · 🔁 OSSY / G4 on each chart</small></h4>
    <div className="fcl-two"><Pane list={list} idx={Math.min(a, Math.max(0, list.length - 1))} setIdx={setA} pins={d?.pins} /><Pane list={list} idx={Math.min(b, list.length - 1)} setIdx={setB} pins={d?.pins} /></div>
  </article>;
}

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
