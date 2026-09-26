import React, { useCallback, useEffect, useState } from 'react';
import { Flame, Crown, Megaphone, Zap } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { AnimatedNumber } from './AnimatedNumber';
import { formatUSD } from '../../lib/dexscreener';

const fmtX = v => (v == null ? '—' : `${v >= 100 ? v.toFixed(0) : v.toFixed(2)}×`);
const ago = s => { const d = Date.now() / 1000 - s; return d < 60 ? `${Math.round(d)}s` : d < 3600 ? `${Math.round(d / 60)}m` : d < 86400 ? `${Math.round(d / 3600)}h` : `${Math.round(d / 86400)}d`; };

function usePoll(path, ms) {
  const [data, setData] = useState(null);
  const load = useCallback(() => fetch(apiUrl(path)).then(r => (r.ok ? r.json() : null)).then(d => d && setData(d)).catch(() => {}), [path]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, ms); return () => clearInterval(t); }, [load, ms]);
  return data;
}

export function TrenchHero({ ecosystemName }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const board = usePoll('/api/reputation/calls/leaderboard?days=1', 30000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600);
  const callers = new Set(lastHour.map(c => c.caller)).size;
  const best = calls.filter(c => Date.now() / 1000 - c.at < 86400).reduce((b, c) => (!b || (c.peakX || 0) > (b.peakX || 0) ? c : b), null);
  const heat = Math.min(100, lastHour.length * 8 + callers * 10);
  return <section className="trench-hero" data-testid="trench-hero">
    <div className="trench-hero-copy">
      <span className="eyebrow">{ecosystemName.toUpperCase()} · LIVE FLOOR</span>
      <h1 className="trenches-font trench-title">The Trenches</h1>
      <p>Every coin posted here is logged as a <b>call</b> — priced by the server the second it lands and tracked forever. Talk is cheap. The ledger isn't.</p>
    </div>
    <div className="trench-heat">
      <div className="heat-gauge" style={{ '--heat': `${heat}%` }}><i /><span><AnimatedNumber value={heat} format={v => Math.round(v)} /><small>HEAT</small></span></div>
      <div className="trench-stats">
        <div><small>CALLS / HR</small><b><AnimatedNumber value={lastHour.length} format={v => Math.round(v)} /></b></div>
        <div><small>ACTIVE CALLERS</small><b><AnimatedNumber value={callers} format={v => Math.round(v)} /></b></div>
        <div><small>BEST CALL 24H</small><b className="positive">{best ? `${best.symbol} ${fmtX(best.peakX)}` : '—'}</b></div>
        <div><small>TOP CALLER TODAY</small><b>{board?.rows?.[0]?.caller || '—'}</b></div>
      </div>
    </div>
  </section>;
}

export function HotCalls({ onPick }) {
  const hot = usePoll('/api/reputation/calls/hot?minutes=180', 15000);
  const rows = hot?.rows || [];
  return <section className="trench-tool" data-testid="hot-calls"><div className="trench-tool-head"><Flame size={14} /><h3 className="trenches-font">Hot CAs</h3><small>most-called · 3h</small></div>
    {!rows.length && <p className="trench-empty">No calls in the last 3 hours. Paste a CA in chat to start the ledger.</p>}
    {rows.map(r => <button type="button" key={r.pairAddress} className="hot-row" onClick={() => onPick?.(r)}>
      {r.imageUrl ? <img src={r.imageUrl} alt="" /> : <i>{(r.symbol || '?').slice(0, 2)}</i>}
      <b>{r.symbol}</b><small>{r.callers} caller{r.callers === 1 ? '' : 's'} · {r.calls} call{r.calls === 1 ? '' : 's'}</small>
      <span className={(r.x || 1) >= 1 ? 'positive' : 'negative'}><AnimatedNumber value={r.x || 1} format={fmtX} /></span>
    </button>)}
  </section>;
}

export function LiveCalls({ onPick }) {
  const data = usePoll('/api/reputation/calls/recent?limit=25', 10000);
  const calls = data?.calls || [];
  return <section className="trench-tool" data-testid="live-calls"><div className="trench-tool-head"><Megaphone size={14} /><h3 className="trenches-font">Live calls</h3><small>× since called</small></div>
    {!calls.length && <p className="trench-empty">The ledger is empty. First caller to post a CA sets the record.</p>}
    <div className="live-call-list">{calls.map(c => <button type="button" key={c.id} className="live-call" onClick={() => onPick?.(c)}>
      <span className="caller">{c.caller}</span><b>{c.symbol}</b>
      <small>@ {formatUSD(c.mcAtCall)} MC · {ago(c.at)} ago</small>
      <span className={`call-x ${(c.x || 1) >= 1 ? 'up' : 'down'}`}><AnimatedNumber value={c.x || 1} format={fmtX} /><em>peak {fmtX(c.peakX)}</em></span>
    </button>)}</div>
  </section>;
}

export function CallerBoard() {
  const [days, setDays] = useState(7);
  const data = usePoll(`/api/reputation/calls/leaderboard?days=${days}`, 30000);
  const rows = data?.rows || [];
  return <section className="trench-tool" data-testid="caller-board"><div className="trench-tool-head"><Crown size={14} /><h3 className="trenches-font">Caller board</h3>
    <div className="caller-days">{[1, 7, 30].map(d => <button type="button" key={d} className={days === d ? 'active' : ''} onClick={() => setDays(d)}>{d}d</button>)}</div></div>
    {!rows.length && <p className="trench-empty">No ranked callers yet for this window.</p>}
    {rows.slice(0, 10).map((r, i) => <div key={r.caller} className="caller-row">
      <span className="rank">{i + 1}</span><b>{r.caller}</b>
      <span title="calls that reached 2× or more"><small>HIT</small>{Math.round(r.hitRate * 100)}%</span>
      <span><small>AVG PEAK</small>{fmtX(r.avgPeakX)}</span>
      <span><small>CALLS</small>{r.calls}</span>
      {r.rugs > 0 && <span className="negative"><small>DUDS</small>{r.rugs}</span>}
    </div>)}
    <p className="trench-foot"><Zap size={11} /> Hit = a call that reached 2× from the server-recorded price. Permanent and unfakeable — nobody can edit a call after it lands.</p>
  </section>;
}

const FEATURES = [
  ['📣', 'Every call is on the record', 'Paste a CA in chat and it becomes a call — priced by the server the second it lands. No edits, no deletes, no fake entries.'],
  ['🎯', 'Callers earn a track record', 'Hit rate, average peak ×, duds. The Caller Board shows who actually finds winners — and who just talks.'],
  ['🧪', 'Every coin gets an Edge Score', 'Order flow, liquidity depth, creator reputation, snipers and bundles — one grade, every reason shown.'],
  ['⚡', 'Trade without leaving', 'Quick-buy in SOL or USD right next to the chart. Anything into $FEE is always fee-free.'],
  ['🐂', 'Bulls · Trenches · Bears', 'Every coin has three rooms. Pick your side, react, and watch your calls play out live.'],
  ['🐱', 'Fee is watching too', 'Toggle Fee\'s trades onto any chart and see exactly where the Leader cat bought and sold.'],
];

// Front page for the Trenches: what it is, live proof it's alive, and one button onto the floor.
export function TrenchLanding({ ecosystemName, onEnter }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const board = usePoll('/api/reputation/calls/leaderboard?days=7', 30000);
  const hot = usePoll('/api/reputation/calls/hot?minutes=1440', 30000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600).length;
  const callers = new Set(calls.filter(c => Date.now() / 1000 - c.at < 86400).map(c => c.caller)).size;
  const top = board?.rows?.[0];
  const hottest = hot?.rows?.[0];
  return <section className="trench-landing" data-testid="trench-landing">
    <div className="trench-landing-hero">
      <span className="eyebrow">{ecosystemName.toUpperCase()} · COMMUNITY FLOOR</span>
      <h1 className="trenches-font trench-landing-title">The Trenches</h1>
      <p>Where calls get made and receipts get kept. Chat, chart, trade and track who's actually right — all on one floor.</p>
      <div className="trench-landing-live">
        <div><small>CALLS LAST HOUR</small><b><AnimatedNumber value={lastHour} format={v => String(Math.round(v))} /></b></div>
        <div><small>CALLERS TODAY</small><b><AnimatedNumber value={callers} format={v => String(Math.round(v))} /></b></div>
        <div><small>TOP CALLER · 7D</small><b>{top ? `${top.caller} · ${Math.round(top.hitRate * 100)}%` : '—'}</b></div>
        <div><small>HOTTEST CA · 24H</small><b>{hottest ? `${hottest.symbol} ${fmtX(hottest.x)}` : '—'}</b></div>
      </div>
      <button type="button" className="lets-trench trenches-font" onClick={onEnter} data-testid="lets-trench">Let's Trench →</button>
    </div>
    <div className="trench-features">{FEATURES.map(([icon, title, text]) => <article key={title}><span>{icon}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
  </section>;
}

export function TrenchBar({ onAbout }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600);
  const best = calls.filter(c => Date.now() / 1000 - c.at < 86400).reduce((b, c) => (!b || (c.peakX || 0) > (b.peakX || 0) ? c : b), null);
  return <div className="trench-bar" data-testid="trench-bar">
    <button type="button" onClick={onAbout} className="trench-bar-about">← About</button>
    <b className="trenches-font">The Trenches</b>
    <span><small>CALLS/HR</small><AnimatedNumber value={lastHour.length} format={v => String(Math.round(v))} /></span>
    <span><small>CALLERS</small><AnimatedNumber value={new Set(lastHour.map(c => c.caller)).size} format={v => String(Math.round(v))} /></span>
    <span><small>BEST 24H</small>{best ? `${best.symbol} ${fmtX(best.peakX)}` : '—'}</span>
  </div>;
}
