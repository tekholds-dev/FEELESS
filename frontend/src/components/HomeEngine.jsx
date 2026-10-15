// 🤖 AGENT RELAY (Home; owner, 2026-10-15: "no radar or scans — a cool realtime animation of the background vital work we do that other big
// sites don't"). What nobody else shows: ten AI agents running a REAL-money card, in public. The ten desks are one lit chain; every real
// decision the card made (the public proof feed: confirmed swaps with the engine's own reason + tx) REPLAYS across it — the coin rides the
// chain from Tally to the desk that decided (Courier for a buy, Reaper for a sale), that desk flares, and the verdict stamps in with its
// real reason and result. One decision every 5s, newest first; tap a coin → its drawer, the tx → Solscan. A missing number reads "—".
import React, { useEffect, useMemo, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import { openCoin } from './CoinDrawer';
import '../styles/homeEngine.css';

const POLL = 30000;
const STEP_MS = 5000;
export const DESKS = [['tally', '📊', 'Tally', 'reads the market'], ['sherlock', '🔍', 'Sherlock', 'why it moves'], ['weather', '🌦', 'Weather', 'the regime'],
  ['trigger', '⏱', 'Trigger', 'entry timing'], ['devil', '😈', 'Devil', 'argues against'], ['warden', '🛡', 'Warden', 'sizes it'], ['courier', '📮', 'Courier', 'signs + sends'],
  ['reaper', '☠', 'Reaper', 'manages the exit'], ['archivist', '🗄', 'Archivist', 'files the record'], ['judge', '👨‍⚖️', 'Judge', 'grades who was right']];

// pure: one public proof row → the relay step it plays (which desk decided, the stamp, the reason in plain words)
export function relayOf(f) {
  if (!f || !f.symbol) return null;
  const sell = f.side === 'sell';
  const why = String(f.why || '');
  const rule = (why.match(/Reaper\s+R\d+\w*\s+([^:]+)/) || [])[1] || null;
  return { id: f.sig || `${f.symbol}-${f.at}`, sym: String(f.symbol).slice(0, 12), mint: f.mint, pair: f.pair, sig: f.sig, at: Number(f.at) || 0,
    desk: sell ? 'reaper' : 'courier', side: sell ? 'sell' : 'buy', pct: f.pct == null ? null : Number(f.pct), usd: Number(f.usd) || 0,
    stamp: sell ? (f.pct == null ? 'SOLD' : `SOLD ${Number(f.pct) > 0 ? '+' : ''}${Number(f.pct).toFixed(1)}%`) : `BOUGHT $${(Number(f.usd) || 0).toFixed(2)}`,
    why: sell ? (rule ? `Reaper: ${rule.trim()}` : 'Reaper closed it') : 'Trigger cleared it · Devil let it through · Warden sized it · Courier signed it' };
}
export const relays = (proof, n = 12) => (proof?.feed || []).map(relayOf).filter(Boolean).slice(0, n);
// pure: the scoreboard of the shown decisions (real results only)
export function board(steps) {
  const sells = (steps || []).filter(s => s.side === 'sell' && s.pct != null);
  const won = sells.filter(s => s.pct > 0).length;
  return { decisions: (steps || []).length, sells: sells.length, won, rate: sells.length ? Math.round((won / sells.length) * 100) : null };
}
const ago = at => { const s = Math.max(0, Math.round(Date.now() / 1000 - at)); return s < 60 ? `${s}s ago` : s < 3600 ? `${Math.round(s / 60)}m ago` : `${Math.round(s / 3600)}h ago`; };

export function HomeEngine({ onOpen }) {
  const [d, setD] = useState(null); const [i, setI] = useState(0); const [hold, setHold] = useState(false);
  useEffect(() => { let on = true;
    const load = first => { if (!first && typeof document !== 'undefined' && document.hidden) return;
      Promise.all(['fuses/proof', 'fuses/prime'].map(u => sharedJson(`/api/reputation/${u}`, { maxAge: POLL - 2000 }).catch(() => null)))
        .then(([proof, prime]) => { if (on && (proof || prime)) setD(p => ({ proof: proof || p?.proof, prime: prime || p?.prime })); }); };
    load(true); const t = setInterval(load, POLL); return () => { on = false; clearInterval(t); }; }, []);
  const steps = useMemo(() => relays(d?.proof), [d?.proof]);
  useEffect(() => { if (hold || steps.length < 2) return undefined; const t = setInterval(() => setI(x => x + 1), STEP_MS); return () => clearInterval(t); }, [hold, steps.length]);
  if (!d) return null;
  const cur = steps.length ? steps[i % steps.length] : null; const sc = board(steps);
  const deskAt = cur ? DESKS.findIndex(x => x[0] === cur.desk) : -1;
  const real = (d.prime?.cards || []).find(c => c?.real);
  const go = (e, url) => { if (onOpen) { e.preventDefault(); onOpen(url); } };
  return <section className="arl" data-testid="home-engine" onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)}>
    <header className="arl-top"><span className="arl-title"><b>AGENT RELAY<i className="arl-live" aria-hidden="true">● LIVE</i></b>
      <small>10 AI agents run a real-money card — every decision replayed here, with its reason and its tx</small></span>
      <span className="arl-score" data-testid="arl-score"><span><b>{sc.decisions}</b> real decisions</span><span><b>{sc.rate == null ? '—' : `${sc.rate}%`}</b> exits won</span>
        <span><b>{real?.valueUsd == null ? '—' : `$${Number(real.valueUsd).toFixed(2)}`}</b> in the card now</span></span></header>
    <div className="arl-chain" data-testid="arl-chain" style={{ '--n': DESKS.length }}>
      <i className="arl-wire" aria-hidden="true"><u /></i>
      {cur ? <i key={cur.id + i} className={`arl-pkt is-${cur.side}`} aria-hidden="true" style={{ '--to': deskAt / (DESKS.length - 1) }}><b>${cur.sym}</b></i> : null}
      {DESKS.map(([k, ico, name, job], j) => <span key={k} className={`arl-desk${j === deskAt ? ' is-on' : ''}${j < deskAt ? ' is-passed' : ''}`} data-testid={`arl-${k}`} data-tip={`${name}: ${job}`}>
        <i className="arl-node" aria-hidden="true">{ico}</i><b>{name}</b><small>{job}</small></span>)}
    </div>
    {cur ? <div className={`arl-call is-${cur.side} ${cur.pct != null && cur.pct < 0 ? 'is-loss' : ''}`} key={cur.id + 'c' + i} data-testid="arl-call">
      <button type="button" className="arl-coin" onClick={() => openCoin({ mint: cur.mint, symbol: cur.sym, pairAddress: cur.pair })}>${cur.sym}</button>
      <span className="arl-stamp">{cur.stamp}</span><span className="arl-why">{cur.why}</span>
      <small>{ago(cur.at)}{cur.sig ? <> · <a href={`https://solscan.io/tx/${cur.sig}`} target="_blank" rel="noreferrer">tx ↗</a></> : null}</small>
    </div> : <div className="arl-call is-wait"><small>no real decisions in the last 24h — the agents are waiting for a coin worth it</small></div>}
    <ol className="arl-log" aria-label="Latest real decisions">{steps.slice(0, 8).map((s, j) => <li key={s.id} className={`is-${s.side}${s.pct != null && s.pct < 0 ? ' is-loss' : ''}${j === i % Math.max(1, steps.length) ? ' is-on' : ''}`}>
      <button type="button" onClick={() => setI(j)}><b>{s.side === 'sell' ? '☠' : '📮'} ${s.sym}</b><span>{s.stamp}</span></button></li>)}</ol>
    <a className="arl-go" href="/terminal/fuse" onClick={e => go(e, '/terminal/fuse')}>See the cards they run →</a>
  </section>;
}
