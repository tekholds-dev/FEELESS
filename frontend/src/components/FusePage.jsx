import React, { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { TraderChip } from './TraderChip';
import { toast } from 'sonner';
import { ShareGifButton } from './ShareGif';
import { RiskDial, DialBoard } from './RiskDial';
import { StrategyPicks } from './StrategyPicks';
import { ArenaPrime, HqRealCards, WeatherStrip, TrenchScan } from './ArenaPrime';
import { ArenaContenders } from './ArenaContenders';
import { FuseLanding } from './FuseLanding';
import { PitReel } from './PitReel';
import { RaceLine, CoinTicker, DuelBoard } from './PitLive';
import { FuseGuide } from './FuseGuide';
import { CardEarnings } from './CardEarnings';
import { PaperAudit, TrailSummary, CoinTable, CycleBuilder, usd as fmt$ } from './FuseMoney';
import { CardRounds } from './CardRounds';
import { openCoin } from './CoinDrawer';
import { RISK_DIALS } from '../lib/riskDial';
import { apiUrl } from '../lib/api';
import { useAdmin } from '../lib/adminCall';
import { useWallet } from '../hooks/useWallet';
import { readChatSession } from '../lib/chatSession';
import { unfuseOrders, rebalanceOrders, topupOrders, SOL_MINT } from '../lib/fuseGo';
import { FuseLab } from './FuseLab';
import { FuseSide } from './FuseSide';
import { FuseGo } from './FuseGo';
import { RunnersPanel, Countdown } from './RunnersPanel';
import { FuseCard, LiveFuseCard } from './FuseCard';
import { openWarRoom } from './WarRoomHost';
import { useLivePrices } from '../lib/livePrices';
import { liveBook, liveStagePct } from '../lib/fuseLive';
import '../styles/runners.css';
import '../styles/fusePage.css';
import '../styles/cardWindow.css';

// Fuse 🧬 — the whole Fuse product in one tab: Lab (build + featured) · Runners (pick ≤3 fresh coins) · Arena (proof)
// · My cards (live cards + every action). Runner picks and "Load" carry across tabs. Every money action is a normal
// wallet-signed FuseGo approval; the server re-checks every signature before anything counts.
// 🧬 A real 3D double helix (CSS 3D, transform-only): 10 base-pair rungs, each turning on its own phase so the strands spiral.
export function DnaHelix({ rungs = 10 }) {
  return <span className="dna3d" aria-hidden="true" data-testid="dna3d">{Array.from({ length: rungs }, (_, i) => <i key={i} style={{ '--i': i }}><b /><b /></i>)}</span>;
}

// One fun line per tab, so a first-timer knows what each one is for in 5 seconds.
export const TAB_TIPS = {
  home: '⚡ What a Fuse is, on one screen: a live card, its book on the back, and the four steps to make your own.',
  lab: '🧪 The kitchen: pick pools + runners, set your TP / SL and auto-profit, see every fee, then one tap fuses it all.',
  runners: '🏃 The scouting report: only coins that pass every gate show up — 🔔 bond runs light up box by box. Grab up to 3.',
  arena: '⚔ The battlefield: the hottest cards burn brightest, fight head-to-head every hour, and climb the weekly season. Beat FeeCat.',
  cards: '🃏 Your deck: live P&L on every card (fees never mixed in), one-tap take-profit, compound, swap and withdraw.',
};

// Page-wide battlefield FX: a synthwave grid floor rolling under the page, lightning strikes across the sky and rising
// sparks. Transform/opacity only, one layer, dies under fx-lite / reduced motion.
export function FuseFx() {
  return <div className="fz-fx" aria-hidden="true"><div className="fz-grid" />{[0, 1, 2].map(i => <i key={i} className="fz-strike" style={{ '--i': i }} />)}
    {Array.from({ length: 14 }, (_, i) => <b key={i} className="fz-spark" style={{ '--i': i }} />)}</div>;
}

export const FUSE_TABS = [['home', '⚡ Fuse'], ['lab', '🧪 Lab'], ['runners', '🏃 Runners'], ['arena', '🏟 Arena'], ['cards', '🃏 My cards']];   // every ?tab= that routes
// What the header shows: FOUR tabs, each with what it is for. Runners is step 1 of Build (same picks), not its own tab.
export const TOP_TABS = [['home', '⚡ Start', 'what a Fuse is'], ['lab', '🧪 Build', 'pick coins · make a card'], ['arena', '🏟 Arena', 'cards fighting live'], ['cards', '🃏 My cards', 'yours, live']];
const topOf = t => (t === 'runners' ? 'lab' : t);
const m$ = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0) >= 1e3 ? `${(Math.abs(v) / 1e3).toFixed(1)}K` : Math.abs(v || 0).toFixed(2)}`;
const pc = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;
// Watching row: graduated coins are never runners (pre-bond engine) → hidden; the rest say WHAT failed, in plain words.
const FAIL_WHY = { 'Top 10 under 25%': 'top 10 hold too much', 'Holder scan done': 'holder scan pending', 'Creator not flagged (Bot shield / blocklist)': 'creator flagged',
  'Creator not a rugger (suspect = coin must prove itself)': 'creator rep risky', 'Market cap ≥ $12K': 'mcap too small', '1h volume ≥ $10K': 'volume too thin' };
const failWhy = g => FAIL_WHY[g] || (g ? `not: ${g.toLowerCase()}` : 'a gate');
const MAX_RUNNERS = 3;
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });
const readTab = () => { const t = new URLSearchParams(window.location.search).get('tab'); return FUSE_TABS.some(([k]) => k === t) ? t : 'home'; };   // no ?tab = the landing stage

export function useFuseLimits(addr) {
  const [lim, setLim] = useState(null);
  useEffect(() => { if (!addr) { setLim(null); return undefined; } let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/fuses/limits/${addr}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setLim(x)).catch(() => {});
    load(); window.addEventListener('feeless:fuse-pnl', load); return () => { alive = false; window.removeEventListener('feeless:fuse-pnl', load); }; }, [addr]);
  return lim;
}

export function FusePage() {
  const [tab, setTab] = useState(readTab);
  const [runnerPicks, setRunnerPicks] = useState([]);
  const [incoming, setIncoming] = useState(null);
  const { wallet } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const limits = useFuseLimits(addr);
  const go = t => { setTab(t); const u = new URL(window.location.href); u.searchParams.set('tab', t); window.history.replaceState(null, '', u); };
  return <section className="fuse-page" data-testid="fuse-page"><FuseFx />
    <header className="fp-head"><h1 className="fp-title"><span className="fp-zap" data-text="Fuse">Fuse<i className="fp-bolt" aria-hidden="true" /><i className="fp-bolt b2" aria-hidden="true" /></span> <DnaHelix /></h1><p className="m-dim">Fuse pools + fresh runners into one card. You sign every move; we show every fee.</p>
      <div className="m-seg fp-tabs" role="tablist" aria-label="Fuse">{TOP_TABS.map(([k, l, sub]) => <button key={k} type="button" role="tab" aria-selected={topOf(tab) === k} className={topOf(tab) === k ? 'active' : ''} data-testid={`fuse-tab-${k}`} onClick={() => go(k)}>
        <b>{l}{k === 'lab' && runnerPicks.length ? ` · ${runnerPicks.length}` : ''}</b><small>{sub}</small></button>)}</div></header>
    <p className="fp-tabtip" key={`tip-${tab}`} data-testid="fp-tabtip">{TAB_TIPS[tab]} <FuseGuide label="📖 What everything means" /></p>
    {topOf(tab) === 'lab' && <div className="m-seg fp-steps" role="tablist" aria-label="Build steps">
      <button type="button" role="tab" aria-selected={tab === 'runners'} className={tab === 'runners' ? 'active' : ''} onClick={() => go('runners')} data-testid="fuse-tab-runners"><b>1</b> 🏃 Pick runners <em>{runnerPicks.length}/{MAX_RUNNERS}</em></button>
      <button type="button" role="tab" aria-selected={tab === 'lab'} className={tab === 'lab' ? 'active' : ''} onClick={() => go('lab')} data-testid="fuse-step-lab"><b>2</b> 🧪 Build the card</button></div>}
    <div className="fp-body" key={tab}>
      {tab === 'home' && <FuseLanding onGo={go} />}
      {tab === 'lab' && <div className="fz-split-view fp-lab"><FuseLab runnerPicks={runnerPicks} onRunnerPicks={setRunnerPicks} incoming={incoming} limits={limits} />
        <aside className="fp-right"><FeaturedFuses onLoad={f => setIncoming({ legs: f.legs, sol: 0, n: Date.now() })} /><FuseSide /></aside></div>}
      {tab === 'runners' && <><RunnerPicker picks={runnerPicks} onPicks={setRunnerPicks} onDone={() => go('lab')} /><details className="hrt-fold fp-trench" data-testid="fp-trench"><summary>🗑 Trench metas <small>five ways to hunt fresh launches — tap one to see what it finds right now</small></summary><TrenchScan /></details></>}
      {tab === 'arena' && <ArenaBoard onPicks={list => { setRunnerPicks(list); go('lab'); }} onLoad={(legs, from) => { const run = legs.filter(l => l.runner); if (run.length) setRunnerPicks(run.slice(0, MAX_RUNNERS).map(l => ({ mint: l.baseAddress, symbol: l.symbol, logo: l.logo, pairAddress: l.pairAddress, lane: l.lane || 'runner' })));
        setIncoming({ legs: legs.filter(l => !l.runner).sort((x, y) => (y.weight || 0) - (x.weight || 0)), sol: 0, n: Date.now(), ...(from || {}) }); go('lab'); }} />}
      {tab === 'cards' && <MyCards addr={addr} />}
    </div>
  </section>;
}

// ---- Lab › Featured (HQ marks Fuses "Featured in Fuse Lab") ----------------------------------------------------
export function FeaturedFuses({ onLoad }) {
  const [list, setList] = useState(null);
  useEffect(() => { let alive = true; fetch(apiUrl('/api/reputation/fuses')).then(r => (r.ok ? r.json() : null)).then(d => alive && setList((d?.fuses || []).filter(f => f.featured))).catch(() => alive && setList([])); return () => { alive = false; }; }, []);
  if (!list?.length) return null;
  return <section className="m-card fp-featured" data-testid="fuse-featured"><span className="m-label">⭐ FEATURED FUSES</span>
    {list.map(f => <div key={f.id} className="fp-feat"><span className="fz-emoji">{f.emoji}</span><div><b>{f.name}</b><small>{f.legs.map(l => l.symbol).join(' · ')} · grade {f.score?.grade} · index {Number(f.index || 100).toFixed(1)}</small></div>
      <button type="button" className="m-btn" onClick={() => onLoad(f)} data-testid={`feat-load-${f.id}`}>Load</button></div>)}</section>;
}

// ---- Runners (users): live discovery — gated runners every source likes, pick ≤3 ----------------------------------------
export function togglePick(picks, r, max = MAX_RUNNERS) {
  if (picks.some(p => p.mint === r.mint)) return picks.filter(p => p.mint !== r.mint);
  return picks.length >= max ? picks : [...picks, r];
}
const SRC_ICON = { bond: '🔔', watch: '👀', grad: '🎓', arena: '🏟', lit: '🔥', pump: '🚀', snipers: '🎯', creator: '📣', dip: '📉', paid: '💳' };
export const filterBySource = (rows, src) => (src === 'all' ? rows : rows.filter(r => r.sources.some(s => s.kind === src)));

export function RunnerPicker({ picks, onPicks, onDone }) {
  const [d, setD] = useState(null); const [src, setSrc] = useState('all');
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/runners/discover')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 20000); return () => { alive = false; clearInterval(t); }; }, []);
  const live = useLivePrices((d?.runners || []).map(x => x.pairAddress));
  if (!d) return <div className="fp-disc is-loading" data-testid="runner-picker"><div className="fp-scan" /><span className="m-dim">Scanning launchpads, the arena, the radar and the callers…</span></div>;
  const rows = filterBySource(d.runners || [], src);
  const watch = (d.watching || []).filter(w => !(w.gates || []).includes('Pre-bond (still on the curve)'));
  return <section className="fp-disc" data-testid="runner-picker">
    <header className="fp-disc-head m-card m-live"><div><span className="m-label">🏃 RUNNER DISCOVERY · LIVE</span><h2>Good runners, found for you.</h2>
      <p className="m-dim">Every coin here passed every gate right now ({d.gates.slice(0, 3).join(' · ')}…). The more sources that like it, the higher it sits.</p></div>
      <div className="rn-clock"><small>NEXT ROUND</small><Countdown at={d.nextRoundAt} /></div></header>
    <div className="m-seg fp-src" role="tablist" aria-label="Source">{[['all', '✨ All', (d.runners || []).length], ...Object.entries(d.sources).map(([k, l]) => [k, l, d.counts[k] || 0]).filter(([k, , n]) => n > 0 || k === src)].map(([k, l, n]) =>
      <button key={k} type="button" role="tab" aria-selected={src === k} className={src === k ? 'active' : ''} onClick={() => setSrc(k)} data-testid={`src-${k}`}>{l} <em>{n}</em></button>)}</div>
    {(d.swaps || []).length > 0 && <div className="fp-swaps" aria-label="Auto-swaps">{d.swaps.slice().reverse().map(s => <span key={s.at} className="fp-swap">🔁 ${s.out.symbol} → ${s.in.symbol} <small>{s.why[0]}</small></span>)}</div>}
    {!rows.length && <p className="m-dim fp-none">Nothing from this source passes every gate right now — that's the gates working. Next scan in seconds.</p>}
    {rows.length < 6 && watch.length > 0 && <div className="fp-watch" data-testid="fp-watching"><span className="m-label">👀 WATCHING · PRE-BOND, FAILS A GATE (NOT ADDABLE YET)</span>
      <div className="fp-watch-row">{watch.map((w, i) => <span key={w.mint} className="fp-wchip" style={{ '--i': i }} data-tip={`Fails: ${(w.gates || []).join(' · ')}`}>
        <span className="fp-ava sm">{w.logo ? <img src={w.logo} alt="" loading="lazy" /> : '👀'}</span><b>${w.symbol}</b><small>✕ {failWhy((w.gates || [])[0])}</small></span>)}</div></div>}
    <div className="fp-rgrid">{rows.map((r, i) => { const on = picks.some(p => p.mint === r.mint); const full = !on && (picks.length >= MAX_RUNNERS || r.rechecking); const hot = r.sources.length >= 2;
      return <article key={r.mint} className={`fp-runner ${on ? 'is-on' : ''} ${hot ? 'is-hot' : ''} ${r.rechecking ? 'is-recheck' : ''}`} style={{ '--i': Math.min(i, 14) }} data-testid={`runner-${r.mint}`}>
        {hot && <span className="fp-hotband">{r.sources.length} sources</span>}
        <div className="fp-rtop"><span className="fp-ava">{r.logo ? <img src={r.logo} alt="" loading="lazy" /> : '🏃'}</span><div><b>${r.symbol}</b><small>{r.lane || 'runner'} lane · score {Math.round(r.score || 0)}</small></div>
          {(() => { const lv = live.get(r.pairAddress); const mv = lv ? lv.m5 : r.chg1h; return <span className={`m-num fp-move fl-tick ${(mv || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={`${(mv || 0).toFixed(1)}`} data-tip={lv ? `Live · 5m · $${lv.price}` : 'Last hour'}>{pc(mv)}<small>{lv ? '5m' : '1h'}</small></span>; })()}</div>
        <i className="fp-score"><i style={{ transform: `scaleX(${Math.min(1, (r.score || 0) / 100)})` }} /></i>
        {(r.bond || []).length > 0 && <BondMeter checks={r.bond} />}
        <div className="fp-srcs">{r.sources.map(s => <span key={s.kind} className={`fp-chip src-${s.kind}`} data-tip={s.detail}>{SRC_ICON[s.kind]} {s.label.replace(/^\S+\s/, '')}</span>)}</div>
        <div className="m-row fp-rstats"><span>MC {m$(r.mcap)}</span><span>{Math.round(r.buyShare || 0)}% buys</span><span>{m$(r.vol1h)} 1h vol</span></div>
        <button type="button" className={`m-btn wide ${on ? 'primary' : ''}`} disabled={full} onClick={() => onPicks(togglePick(picks, r))} data-testid={`runner-add-${r.mint}`} data-tip={r.rechecking ? 'Passed every gate minutes ago — its holder scan is refreshing. Addable again once it passes.' : undefined}>{on ? '✓ On your card' : r.rechecking ? '🕘 Rechecking…' : full ? 'Card full (3)' : '+ Add to card'}</button>
      </article>; })}</div>
    {picks.length > 0 && picks.length < MAX_RUNNERS && <div className="fp-dock" data-testid="fp-dock"><span>{picks.map(p => `$${p.symbol}`).join(' · ')} <small className="m-dim">· {MAX_RUNNERS - picks.length} more fills the card</small></span><button type="button" className="m-btn primary m-go" onClick={onDone} data-testid="runners-to-lab">Build card with {picks.length} →</button></div>}
    {picks.length >= MAX_RUNNERS && <RunnerCardFull picks={picks} onDone={onDone} />}
  </section>;
}

// A full runner card looks exactly like a prebuilt card (FuseCard: tilt, ⟲ money-math back), then goes to the Lab to fuse in.
// A runner's replay window is never "since launch": a coin under 1h old shows its last 5 minutes, older ones their last hour.
// (A 20-minute-old coin's 1h change IS its launch pump — one card back read "+120,669% · $5 → $1,514".)
export const runnerReplay = p => { const young = p.ageH != null && p.ageH < 1; const move = Number(young ? p.chg5m : p.chg1h) || 0; return { change24h: move, replayPct: move, replayH: young ? 5 / 60 : 1 }; };
export const runnerLegs = picks => picks.map(p => ({ chainId: 'solana', pairAddress: p.pairAddress || p.mint, symbol: p.symbol, baseAddress: p.mint, logo: p.logo,
  weight: Math.round(10000 / picks.length) / 100, liquidityUsd: p.liq || 0, ...runnerReplay(p) }));
export function RunnerCardFull({ picks, onDone }) {
  const legs = runnerLegs(picks); const score = Math.round(picks.reduce((a, p) => a + (p.score || 0), 0) / picks.length);
  return <div className="fp-full m-card m-live" data-testid="runner-card-full">
    <FuseCard c={{ pools: legs.map(l => l.pairAddress), fitness: score, bornGen: 0, parts: { grade: score >= 70 ? 'A' : score >= 50 ? 'B' : 'C', aprScore: 0, momentum24h: 0, calm: '—', feeDragPct: 0, impactLegs: 0 }, legs }} style="degen" rank={0} budget={5} aura="sparkle" />
    <div className="fp-full-side"><span className="m-label">🃏 YOUR RUNNER CARD · FULL</span><h3>{picks.map(p => `$${p.symbol}`).join(' · ')}</h3>
      <p className="m-dim">Equal weight, gated right now, each with its lane's exit plan. Drag to tilt · ⟲ for the money math. Fuse it in from the Lab with one approval — bundle pricing per coin.</p>
      <button type="button" className="m-btn primary m-go" onClick={onDone} data-testid="runners-to-lab">Fuse this card in the Lab →</button></div></div>;
}

const EcosystemChat = lazy(() => import('./EcosystemChat'));

// Compound streak badge: ♻ Compounder ≥1 · ❄ Snowball ≥3 · 💎 Diamond loop ≥5 compounds, only while the card still wins.
export function CompoundBadge({ s }) {
  if (!s?.tier) return null;
  return <span className={`streak-badge st-${s.tier}`} data-tip={`Rolled its gains back in ${s.compounds}× and still up — +${s.bonus} activity on the Arena`} data-testid={`compound-${s.tier}`}><i aria-hidden="true" />{s.label} ×{s.compounds}</span>;
}

// 💬 Card chat: every Arena card has its own thread (the normal chat, room fuse-card-<id>) — holders, copiers, watchers.
export function CardChat({ c, onClose }) {
  return <section className="m-card ar-chat" data-testid={`card-chat-${c.id}`}><header className="m-row"><span className="m-label">💬 {c.emoji} {c.name}</span><small className="m-dim">card chat · {c.kind === 'user' ? c.owner : c.kind}</small>
    <button type="button" className="m-btn fl-clear" onClick={onClose} aria-label="Close card chat">×</button></header>
    <Suspense fallback={<div className="fl-row is-ghost" />}><EcosystemChat compact room={c.chat} ecosystem={{ id: c.chat, name: c.name }} /></Suspense></section>;
}

// ▶ Card replay: each coin's last 24h (15m closes from the candles service) as % lines + the card's average (bold), with the
// card's moments (opened, buys, take-profits, swaps, compounds) as markers. The lines draw in left→right (a scaleX reveal —
// transform only); "Replay" restarts it.
export function replayPaths(d, w = 600, h = 160) {
  const span = Math.max(1, d.to - d.from); const x = t => ((t - d.from) / span) * w;
  const lines = (d.legs || []).filter(l => (l.series || []).length > 1).map(l => {
    const base = l.entry > 0 ? l.entry : l.series[0][1];
    return { symbol: l.symbol, pts: l.series.map(([t, c]) => [t, (c / base - 1) * 100]) };
  });
  const times = [...new Set(lines.flatMap(l => l.pts.map(p => p[0])))].sort((a, b) => a - b);
  const avg = times.map(t => { const vals = lines.map(l => { const p = l.pts.filter(q => q[0] <= t).pop(); return p ? p[1] : null; }).filter(v => v != null); return [t, vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0]; });
  const top = Math.max(5, ...lines.flatMap(l => l.pts.map(p => Math.abs(p[1]))), ...avg.map(p => Math.abs(p[1])));
  const y = v => h / 2 - (v / top) * (h / 2 - 6);
  const path = pts => pts.map(([t, v], i) => `${i ? 'L' : 'M'}${x(t).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
  return { lines: lines.map(l => ({ symbol: l.symbol, d: path(l.pts), last: l.pts[l.pts.length - 1][1] })), avg: avg.length > 1 ? path(avg) : '', last: avg.length ? avg[avg.length - 1][1] : 0,
    marks: (d.markers || []).map(m => ({ ...m, x: x(m.at) })), zero: y(0), top };
}

export function CardReplay({ c, onClose }) {
  const [d, setD] = useState(null); const [run, setRun] = useState(0);
  useEffect(() => { let alive = true; fetch(apiUrl(`/api/reputation/fuses/replay/${c.kind}/${encodeURIComponent(c.id)}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x || { legs: [] })).catch(() => alive && setD({ legs: [] })); return () => { alive = false; }; }, [c.kind, c.id]);
  const g = d && d.legs?.length ? replayPaths(d) : null;
  return <section className="m-card rp" data-testid={`replay-${c.id}`}><header className="m-row"><span className="m-label">▶ REPLAY · LAST 24H</span><small className="m-dim">{c.emoji} {c.name}</small>
    <button type="button" className="m-btn" onClick={() => setRun(n => n + 1)} disabled={!g}>↻ Replay</button><button type="button" className="m-btn fl-clear" onClick={onClose} aria-label="Close replay">×</button></header>
    {!d ? <div className="fs-ghost" /> : !g || !g.lines.length ? <p className="m-dim">No price history for these coins yet.</p> : <>
      <svg className="rp-chart" viewBox="0 0 600 160" preserveAspectRatio="none" key={run} role="img" aria-label={`Card replay: ${pc(g.last)} over 24h`}>
        <defs><clipPath id={`rp-clip-${c.id}`}><rect className="rp-reveal" x="0" y="0" width="600" height="160" /></clipPath></defs>
        <line x1="0" x2="600" y1={g.zero} y2={g.zero} className="rp-zero" />
        <g clipPath={`url(#rp-clip-${c.id})`}>{g.lines.map((l, i) => <path key={l.symbol + i} d={l.d} className={`rp-line c${i % 6}`} />)}{g.avg && <path d={g.avg} className={`rp-avg ${g.last >= 0 ? 'up' : 'down'}`} />}</g>
        {g.marks.map((m, i) => <g key={i} className={`rp-mark k-${m.kind}`} style={{ '--i': i }}><line x1={m.x} x2={m.x} y1="4" y2="156" /><circle cx={m.x} cy="8" r="4"><title>{m.label}</title></circle></g>)}
      </svg>
      <div className="rp-legend">{g.lines.map((l, i) => <span key={l.symbol + i} className={`c${i % 6}`}><i />{l.symbol} <b className={l.last >= 0 ? 'm-pos' : 'm-neg'}>{pc(l.last)}</b></span>)}
        <span className="rp-card"><i />card <b className={g.last >= 0 ? 'm-pos' : 'm-neg'}>{pc(g.last)}</b></span></div>
      {g.marks.length > 0 && <div className="rp-moments">{g.marks.map((m, i) => <small key={i} className={`k-${m.kind}`}>● {m.label}</small>)}</div>}</>}
  </section>;
}

// 🔔 Bond run meter: the 6 boxes a pre-bond coin must tick (HQ tunes them) — they light up one by one as it charges.
export function BondMeter({ checks }) {
  const n = checks.filter(c => c.ok).length; const full = n === checks.length;
  return <div className={`bond-meter ${full ? 'is-full' : ''}`} data-testid="bond-meter" data-tip={checks.map(c => `${c.ok ? '✓' : '·'} ${c.label}`).join('\n')}>
    <small>{full ? '🔔 BOND RUN' : `bond ${n}/${checks.length}`}</small>{checks.map((c, i) => <i key={c.id} className={c.ok ? 'on' : ''} style={{ '--i': i }} />)}</div>;
}

// ---- Arena: the stage. HQ mega cards + runner cards that lit after their rounds, each wrapped in effects driven by
// its real activity (server fuse_hq.activity → hard-coded tier: calm / warm / hot / blazing). Then the Runners show
// (RunnersPanel: proof ring, countdown, lanes, round card, live board, last rounds) and the strategies board.
export const TIER_FX = { calm: { aura: 'aurora', embers: 3 }, warm: { aura: 'sparkle', embers: 6 }, hot: { aura: 'fire', embers: 10 }, blazing: { aura: 'lightning', embers: 16 } };
export const stageTier = cards => (cards || []).reduce((top, c) => (['calm', 'warm', 'hot', 'blazing'].indexOf(c.activity?.tier) > ['calm', 'warm', 'hot', 'blazing'].indexOf(top) ? c.activity.tier : top), 'calm');

// 🏟 Arena zones: [key, name, what happens there]. One zone on screen at a time; `?zone=` deep-links it (old links land on the first).
export const ARENA_ZONES = [
  ['prime', '👑 Prime League', "FEELESS's own tier cards, fully automatic — one runs on real money"],
  ['pit', '⚔ The Pit', 'Cards fight head to head for the Throne; below it, every card that made the Main Stage'],
  ['gauntlet', '🏁 The Gauntlet', "Coins ranked live for the next card seat, and this week's Crown Race"],
  ['proving', '🧪 Proving Ground', 'Runner rounds, dial proof and strategies — where the engine earns its record'],
];
const ZONE_ALIAS = { crown: 'gauntlet', stage: 'pit' };   // old links still land in the right place
export const arenaZone = search => { const q = new URLSearchParams(search || '').get('zone'); const z = ZONE_ALIAS[q] || q; return z === 'all' || ARENA_ZONES.some(x => x[0] === z) ? z : 'prime'; };

export function ArenaBoard({ onPicks, onLoad }) {
  const [a, setA] = useState(null);
  const [chat, setChat] = useState(null);
  const [replay, setReplay] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/arena')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setA(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => { alive = false; clearInterval(t); }; }, []);
  const mega = a?.mega || [];
  const top = stageTier(mega);
  const [zone, setZoneRaw] = useState(() => arenaZone(typeof window !== 'undefined' ? window.location.search : ''));
  const setZone = z => { setZoneRaw(z); try { const u = new URL(window.location.href); u.searchParams.set('zone', z); window.history.replaceState(null, '', u); } catch { /* no history */ } };
  // Arena = ZONES, one at a time (never one long scroll): 👑 Prime League · 🏁 The Gauntlet · ⚔ The Pit · 🏆 Crown Race · 🏟 Main Stage · 🧪 Proving Ground
  const on = z => zone === z || zone === 'all';
  const counts = { pit: a?.battles?.pairs?.length || 0 };
  const megaCard = (c, i) => <MegaCard key={`${c.kind}-${c.id}`} c={c} i={i} onPicks={onPicks} onLoad={onLoad} chatOpen={chat?.id === c.id} onChat={() => setChat(x => (x?.id === c.id ? null : c))} onReplay={() => setReplay(x => (x?.id === c.id ? null : c))} />;
  return <section className={`fp-arena ar-tier-${top}`} data-testid="fuse-arena"><ArenaGuide />
    <nav className="m-seg az-bar" role="tablist" aria-label="Arena zones">{ARENA_ZONES.map(([k, label, tip]) =>
      <button key={k} type="button" role="tab" aria-selected={zone === k} className={zone === k ? 'active' : ''} data-tip={tip} onClick={() => setZone(k)} data-testid={`az-${k}`}>{label}{counts[k] > 0 && <i className="m-num">{counts[k]}</i>}</button>)}</nav>
    <div key={zone} className="az-pane" data-testid={`az-pane-${zone}`}>
    {on('prime') && <ArenaPrime onLoad={legs => onLoad?.(legs)} />}
    {on('gauntlet') && <><ArenaContenders /><FuseSeason /></>}
    {on('pit') && <div className="ar-sky" aria-hidden="true">{Array.from({ length: TIER_FX[top].embers + 6 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</div>}
    {on('pit') && (a?.battles?.pairs?.length > 0 ? <Battlefield b={a.battles} cards={[...mega, ...(a.bench || []), ...(a.fighters || [])]} onLoad={onLoad} />
      : a && <p className="m-dim ar-none">The Pit is between fights — the next bell pairs the hottest cards.</p>)}
    {on('pit') && <><header className="ar-head m-card m-live"><span className="m-label">🏟 MAIN STAGE · LIVE</span><h2>Cards that made it.</h2>
      <p className="m-dim">FEELESS cards, runner cards that lit after their rounds, and every trader's open card until it's withdrawn — every one fights in The Pit. The more real activity a card has (FEELESS buys, buyers, $ flow, how far it moved) the hotter it burns.</p>
      <div className="ar-legend">{Object.keys(TIER_FX).map(k => <span key={k} className={`ar-chip t-${k}`}>{k}</span>)}</div></header>
    {!a ? <div className="ar-stage">{[0, 1, 2].map(i => <div key={i} className="frail-ghost" />)}</div>
      : !mega.length ? <p className="m-dim ar-none">No card on stage yet — a runner round that lights up lands here, and FEELESS stages its own cards here.</p>
      : <div className="ar-stage" data-testid="arena-stage">{mega.map(megaCard)}</div>}
    {a?.bench?.length > 0 && <section className="ar-bench" data-testid="arena-bench"><header className="m-row"><span className="m-label">🎨 CREATOR'S CUT · ENGINE CARDS</span>
      <small className="m-dim">hand-picked by FEELESS from the engine playground, with their configs · they fight in The Pit like every card that made it</small></header>
      <div className="ar-stage is-bench">{a.bench.map(megaCard)}</div></section>}</>}
    {on('proving') && <>{a?.dials && <DialBoard dials={a.dials} />}
    <RunnersPanel />
    {a && <div className="m-card"><span className="m-label">STRATEGIES · WE RUN $5 FOR 24H</span><p className="m-dim">{a.outlook?.note || (a.outlook?.style ? `${a.outlook.style}: ${pc(a.outlook.avgPct)} avg over ${a.outlook.runs} runs, ${a.outlook.winRate}% won.` : 'Not enough settled runs yet.')}</p>
      <table className="vd-table"><thead><tr><th>Strategy</th><th>Runs</th><th>Avg</th><th>Won</th><th /></tr></thead><tbody>
      {(a.board || []).map(b => <tr key={b.style}><td><b>{b.style}</b>{a.bestStyle === b.style ? ' 👑' : ''}</td><td>{b.runs}</td><td className={(b.avgPct || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(b.avgPct || 0)}</td><td>{Math.round(b.winRate ?? 0)}%</td><td>{b.runs >= a.minSettled && b.avgPct > 0 ? <span className="m-chip ok">proven</span> : <span className="m-chip">needs {a.minSettled}+</span>}</td></tr>)}</tbody></table></div>}</>}
    </div>
    {replay && <CardReplay c={replay} onClose={() => setReplay(null)} />}
    {chat && <CardChat c={chat} onClose={() => setChat(null)} />}
    <small className="m-dim">Effects show activity, never a promise. Our $5 runs use live prices after each round; fresh coins can go to zero in minutes.</small>
  </section>;
}

// 🗺 The Arena in 6 lines — what each part is, how cards win, how you join. Collapsible; remembers if you closed it.
export function ArenaGuide() {
  const [open, setOpen] = useState(() => { try { return localStorage.getItem('feeless:arena-guide') === 'open'; } catch { return false; } });   // closed until asked for: the Arena opens on the action
  const toggle = () => setOpen(o => { try { localStorage.setItem('feeless:arena-guide', o ? 'closed' : 'open'); } catch { /* private mode */ } return !o; });
  return <details className="ar-guide m-card" open={open} onToggle={e => e.target.open !== open && toggle()} data-testid="arena-guide"><summary><span className="m-label">🗺 HOW THE ARENA WORKS</span><small className="m-dim">tap to {open ? 'hide' : 'show'}</small></summary>
    <ol>
      <li><b>⭐ Tier cards</b><span>FEELESS's own cards, fully automatic. 💵 REAL = live money from the Fuse wallet (every swap has its tx) · 📄 PAPER = same engine at true fills, no money.</span></li>
      <li><b>🔔 Rounds</b><span>each round ends with a 10s countdown, then the card deals its next coins. Losers get swapped, winners stay.</span></li>
      <li><b>🏇 Rules that protect</b><span>+150% or a whole round above +80% = held · 3 losing rounds = safer config · 3 wins = locked · −50% = 🛟 rescue cycle.</span></li>
      <li><b>⚔ Battlefield</b><span>two cards fight each round — bigger move wins. 2 losses and you're out; last card standing is crowned 👑.</span></li>
      <li><b>📜 Every number is real</b><span>tap any card for its config + live P&L per coin, or 📜 Audit for its paper book at true fills.</span></li>
      <li><b>⚡ Join in</b><span>⚔ Back a side (free, XP) · 💰 Buy & back · ⚡ Copy any card to your Lab — you approve one buy, you own the coins.</span></li></ol></details>;
}

// Swap streak badge: Survivor (≥1 swap) · Phoenix (≥3) · Immortal (≥5), only while the card still wins.
export function StreakBadge({ s }) {
  if (!s?.tier) return null;
  return <span className={`streak-badge st-${s.tier}`} data-tip={`Swapped out ${s.swaps} weak leg${s.swaps === 1 ? '' : 's'} and still up — +${s.bonus} activity on the Arena`} data-testid={`streak-${s.tier}`}><i aria-hidden="true" />{s.label} ×{s.swaps}</span>;
}

// 🏆 Fuse season (weekly, Monday 00:00 UTC): cards opened this week ranked by real P&L; top 3 crowned with a Fee-Back boost.
export const left = s => { s = Math.max(0, Math.round(s)); const d = Math.floor(s / 86400); const h = Math.floor((s % 86400) / 3600); const m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`; };
const MEDAL = { 1: '🥇', 2: '🥈', 3: '🥉' };
const wk = s => new Date(s * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });

export function FuseSeason() {
  const [s, setS] = useState(null); const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/season')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setS(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); const c = setInterval(() => setNow(Date.now() / 1000), 30000); return () => { alive = false; clearInterval(t); clearInterval(c); }; }, []);
  if (!s) return <div className="m-card fs is-loading" data-testid="fuse-season"><span className="m-label">🏆 FUSE SEASON</span><div className="fs-ghost" /></div>;
  const top = Math.max(1, ...s.board.map(b => Math.abs(b.pnlPct || 0)));
  return <section className="m-card m-live fs" data-testid="fuse-season">
    <header className="fs-head"><div><span className="m-label">🏆 FUSE SEASON · WEEK OF {wk(s.week).toUpperCase()}</span><h3>Best cards opened this week.</h3>
      <small className="m-dim">Real P&L of verified buys · {s.cards} cards · top 3 crowned Monday 00:00 UTC with +{s.boostPct}% Fee-Back on the card</small></div>
      <div className="fs-clock"><small>ENDS IN</small><b className="m-num">{left(s.endsAt - now)}</b></div></header>
    <div className={`fs-cat ${s.feecat?.pct == null ? 'is-idle' : ''}`} data-testid="season-feecat"><span>🐱</span><b>FeeCat this week</b>
      <em className={`m-num ${(s.feecat?.pct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{s.feecat?.pct == null ? 'no trades yet' : pc(s.feecat.pct)}</em>
      <small className="m-dim">her average trade (sim) · beat her with a real card for +{s.feecat?.winPts ?? 8} Fuse score</small></div>
    {(s.moves || []).length > 0 && <div className="fs-race" data-testid="season-race" aria-label="Season race">{s.moves.slice().reverse().slice(0, 8).map(m => <span key={`${m.id}-${m.at}`} className={`fs-move mv-${m.kind}`}>
      {m.kind === 'up' ? '▲' : m.kind === 'down' ? '▼' : '✦'} {m.handle} <b>{m.name || 'card'}</b> {m.from ? `#${m.from} → ` : ''}#{m.to} <em className={(m.pnlPct || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(m.pnlPct)}</em></span>)}</div>}
    {!s.board.length ? <p className="m-dim fs-none">No card opened this week yet — the first one you fuse lands on this board.</p>
      : <ol className="fs-board">{s.board.map((b, i) => <li key={b.id} className={`fs-row r-${b.rank <= 3 ? b.rank : 'n'}`} style={{ '--i': i }} data-testid={`season-${b.id}`}>
        <b className="fs-rank">{MEDAL[b.rank] || `#${b.rank}`}</b>
        <span className="fs-who"><b>{b.name || 'Fuse card'}{b.beatsCat && <em className="fs-beat" data-tip="Up more than FeeCat's average trade this week">🐱 beat</em>}</b><small>{b.handle}{b.closed ? ' · closed' : ''} <TraderChip address={b.wallet} compact /></small></span>
        {b.streak?.tier ? <StreakBadge s={b.streak} /> : <span />}
        <i className="fs-bar"><i className={b.pnlPct >= 0 ? 'up' : 'down'} style={{ transform: `scaleX(${Math.max(0.03, Math.abs(b.pnlPct || 0) / top)})` }} /></i>
        <b className={`m-num ${b.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(b.pnlPct)}</b></li>)}</ol>}
    {s.backers && <div className="fs-backers" data-testid="season-backers"><small className="m-label">⚔ TOP BACKERS · THIS WEEK</small>
      <em className="m-dim">{s.backers.poolUsd > 0 ? `top 3 split $${s.backers.poolUsd} (50/30/20) · paid with Fee-Back` : 'backs earn season XP'} · {s.backers.minBacks}+ backs to rank</em>
      {s.backers.board.length ? s.backers.board.map((r, i) => <span key={r.wallet} className="fs-backer" style={{ '--i': i }}><b>{MEDAL[r.rank] || `#${r.rank}`}</b> {r.handle} <i className="m-num">{r.wins}/{r.backs} won</i></span>)
        : <span className="m-dim">No ranked backers yet — back a side in the battlefield above.</span>}</div>}
    {s.past?.length > 0 && <div className="fs-past"><small className="m-label">PAST CHAMPIONS</small>{s.past.map(w => <span key={w.week} className="fs-champ" data-tip={w.top.map(t => `${MEDAL[t.rank]} ${t.handle || ''} ${t.name || ''} ${pc(t.pnlPct)}`).join('\n')}>
      <small>{wk(w.week)}</small>{MEDAL[1]} {w.top[0]?.handle || `${(w.top[0]?.wallet || '').slice(0, 4)}…`} <b className="m-pos">{pc(w.top[0]?.pnlPct)}</b></span>)}</div>}
  </section>;
}

// ⚔ Battlefield: stage cards fight in pairs (hot vs hot) — bigger move since the bell wins. Tug-of-war bar = who's ahead.
// ⚡ Smarter power board: standing cards first, then a power score (wins, losses, live move, comebacks, crowd calls)
export const power = board => [...board].map(x => ({ ...x, power: Math.round((x.w * 3 - x.l * 2 + (x.pct || 0) / 10 + (x.comebacks || 0) * 2 + (x.calls || 0) / 2) * 10) / 10 }))
  .sort((a, b) => (a.rank && b.rank ? a.rank - b.rank : 0) || (a.status === 'out') - (b.status === 'out') || b.power - a.power);   // league: the table's order
const tugShare = (a, b) => (a + b > 0 ? Math.max(0.06, Math.min(0.94, a / (a + b))) : 0.5);
// 👑 The Throne: ONE card reigns, wrapped in live voltage until a new bracket winner knocks it off. Its two closest challengers
// circle behind it and trade sides; the past champions line up on the right (🛡 defended or struck through with who took the crown).
export function Throne({ champs, now, onBuy, kingNode, challengers = [], onOpen }) {
  const [king, ...fallen] = champs;
  const [flip, setFlip] = useState(false);
  useEffect(() => { if (challengers.length < 2 || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const t = setInterval(() => setFlip(f => !f), 5200); return () => clearInterval(t); }, [challengers.length]);
  const held = Math.max(0, now - (king.at || now)); const reign = held >= 86400 ? `${Math.floor(held / 86400)}d ${Math.floor((held % 86400) / 3600)}h` : held >= 3600 ? `${Math.floor(held / 3600)}h ${Math.floor((held % 3600) / 60)}m` : `${Math.floor(held / 60)}m`;
  return <div className="th" data-testid="bf-champs">
    <div className="th-stage">
      <span className="th-rays" aria-hidden="true" /><span className="th-cone" aria-hidden="true" />
      {challengers.slice(0, 2).map((c, i) => <div key={c.key} role="button" tabIndex={0} className={`th-ch p-${(i + (flip ? 1 : 0)) % 2}`} onClick={e => { if (!e.target.closest('.fcd-flip')) onOpen?.(c.key); }} onKeyDown={e => e.key === 'Enter' && onOpen?.(c.key)} data-tip={`Challenger: ${c.name} · ${c.badge} — tap for its config`} aria-label={`Challenger ${c.name}`}>
        {c.node ? <span className="th-card">{c.node}</span> : <span className="th-ghost">{c.emoji || '🃏'}</span>}<small className="m-num">{c.name} · {c.badge}</small></div>)}
      <div className="th-king" key={king.at} role={kingNode ? 'button' : undefined} tabIndex={kingNode ? 0 : undefined} onClick={e => { if (!e.target.closest('.fcd-flip, .bf-buychamp')) onOpen?.(king.key); }} onKeyDown={e => e.key === 'Enter' && onOpen?.(king.key)}>
        <span className="th-plinth" aria-hidden="true" /><span className="th-crown" aria-hidden="true">👑</span>
        <span className="th-volt" aria-hidden="true"><i /><i /><i /><i className="th-ring" /></span>
        {kingNode ? <span className="th-card">{kingNode}</span> : <span className="th-ghost">{king.emoji || '👑'}</span>}</div>
    </div>
    <div className="th-side">
      <div className="th-who"><small className="m-label">ON THE THRONE · SEASON #{king.season}</small><b>{king.emoji} {king.name}</b>
        <span className="th-stats"><em className="m-num">{king.w}W</em><em data-tip="Time since it took the crown">reigning {reign}</em></span>
        {king.legs?.length > 0 && onBuy && <button type="button" className="m-btn primary m-go bf-buychamp" onClick={() => onBuy(king)}
          data-tip={king.key?.startsWith('user:') ? "Copy the champion — its owner earns the champion's share (double copy cut) of your FEELESS fee, not extra cost to you" : 'Load the champion into your Lab'} data-testid="buy-champ">👑 Buy the champion</button>}</div>
      {fallen.length > 0 && <ol className="th-fallen" aria-label="Past champions">{fallen.slice(0, 3).map((c, j) => { const next = champs[j]; const kept = next.name === c.name;   // the same card winning again DEFENDED its crown — nobody knocked it off
        return <li key={c.at} style={{ '--i': j }} className={kept ? 'is-kept' : ''} data-tip={kept ? `Bracket #${c.season}: ${c.name} won with ${c.w} wins and kept the crown in #${next.season}` : `Bracket #${c.season} champion with ${c.w} wins — knocked off by ${next.name}`}>
          {kept ? <b>{c.emoji} {c.name}</b> : <s>{c.emoji} {c.name}</s>}<small>#{c.season} · {c.w}W · {kept ? `🛡 defended in #${next.season}` : `knocked off by ${next.emoji} ${next.name}`}</small></li>; })}</ol>}
    </div>
  </div>;
}

// ⏱ Pit lenses: the bell decides the bracket; the others show who is winning the last 5 / 15 / 60 minutes of the same fight.
export const PIT_LENSES = [['bell', '🔔 This bell', 'Move since the bell — this is what decides the fight'], ['5', '5m', 'Who is winning the last 5 minutes'], ['15', '15m', 'Who is winning the last 15 minutes'], ['60', '1h', 'Who is winning the last hour']];
export const lensPairs = (pairs, lens) => (lens === 'bell' ? pairs : (pairs || []).map(p => ({ ...p, a: { ...p.a, now: p.a.frames?.[lens] ?? p.a.now }, b: { ...p.b, now: p.b.frames?.[lens] ?? p.b.now } })));
// 🎙 one live line per fight, straight from the numbers
export function pitCall(p, secs) {
  const d = (p.a.now || 0) - (p.b.now || 0); const lead = d >= 0 ? p.a : p.b; const gap = Math.abs(d);
  if (secs <= 60 && gap < 1) return `FINAL MINUTE — ${p.a.name} and ${p.b.name} are ${gap.toFixed(1)} apart. Anyone's fight.`;
  if (secs <= 60) return `FINAL MINUTE — ${lead.name} needs to hold a ${gap.toFixed(1)}-point lead.`;
  if (gap < 0.3) return `Dead even. ${p.a.name} and ${p.b.name} are trading the lead.`;
  if (gap >= 8) return `${lead.name} is running away with it — up ${gap.toFixed(1)} points.`;
  return `${lead.name} leads by ${gap.toFixed(1)} point${gap.toFixed(1) === '1.0' ? '' : 's'}.`;
}
// 👥 crowd split from backs (free + bought); an even 50 / 50 until anyone backs a side
export const crowdShare = p => { const a = (p.a.backers || 0) + (p.a.paidN || 0); const bb = (p.b.backers || 0) + (p.b.paidN || 0); return a + bb ? Math.round((a / (a + bb)) * 100) : 50; };

export function Battlefield({ b: b0, cards = [], onLoad }) {
  const [lens, setLens] = useState('bell');
  const b = lens === 'bell' ? b0 : { ...b0, pairs: lensPairs(b0.pairs, lens) };
  const [now, setNow] = useState(Date.now() / 1000);
  const { wallet } = useWallet() || {}; const [mine, setMine] = useState(null);
  // ⚔ back a side: free, points only — one pick per battle, a win goes on your backing record
  const back = async key => { const addr = wallet?.address; const s = addr && readChatSession(addr);
    if (!s) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    try { const r = await post('/api/reputation/fuses/battle/back', { address: addr, session: s, key }); setMine(key); toast.success(`⚔ Backed — your record ${r.record.w}–${r.record.l}`); } catch (e) { toast.error(e.message); } };
  // 💰 pay to back = BUY the card (normal one-click Fuse in, you own it) — its own bar, never mixed with free backs
  const buyBack = side => { const c = cards.find(x => `${x.kind}:${x.id}` === side.key); if (!c || !onLoad) { toast.error('That card is not on the board right now.'); return; }
    onLoad(c.legs, { backKey: side.key, backName: side.name }); };
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(t); }, []);
  const br = b.bracket || { board: [], champions: [], season: 1 };
  const [cfgKey, setCfgKey] = useState(null); const [called, setCalled] = useState(null); const [audit, setAudit] = useState(null);
  // 🎬 the show: floating damage numbers when a fighter's live % moves, a shake on a hit, ⚡ LEAD CHANGE when the lead flips, 📣 cheers
  const prevNow = useRef({}); const prevLead = useRef({}); const [fx, setFx] = useState({}); const [cheers, setCheers] = useState({}); const [flip, setFlip] = useState({});
  useEffect(() => { const nfx = {}; const nflip = {};
    (b.pairs || []).forEach((p, i) => { ['a', 'b'].forEach(k => { const x = p[k]; const was = prevNow.current[x.key]; if (was != null && Math.abs((x.now || 0) - was) >= 0.05) nfx[x.key] = { d: (x.now || 0) - was, t: Date.now() }; prevNow.current[x.key] = x.now || 0; });
      const lead = Math.sign((p.a.now || 0) - (p.b.now || 0)); if (prevLead.current[i] != null && lead && prevLead.current[i] && lead !== prevLead.current[i]) nflip[i] = Date.now(); prevLead.current[i] = lead || prevLead.current[i]; });
    if (Object.keys(nfx).length) setFx(f => ({ ...f, ...nfx })); if (Object.keys(nflip).length) setFlip(f => ({ ...f, ...nflip })); }, [b.pairs]);
  const cheer = key => setCheers(c => ({ ...c, [key]: { n: ((c[key] || {}).n || 0) + 1, t: Date.now() } }));
  const cardOf = key => cards.find(x => `${x.kind}:${x.id}` === key);
  // 🔮 call the bracket champion: free, one call per bracket — right = season XP
  const callIt = async key => { const addr = wallet?.address; const s = addr && readChatSession(addr);
    if (!s) { toast.error('Connect your wallet + open chat once to sign in first.'); return; }
    try { await post('/api/reputation/fuses/bracket/pick', { address: addr, session: s, key }); setCalled(key); toast.success('🔮 Called — if it wins the bracket, season XP is yours'); } catch (e) { toast.error(e.message); } };
  const cfgCard = cfgKey && cardOf(cfgKey);
  // the REAL FuseCard for any key on the board (throne + challengers show the actual card, never a placeholder name)
  const nodeOf = (key, mom) => { const c = cardOf(key); return c?.legs?.length ? <FuseCard c={{ pools: c.legs.map(l => l.pairAddress), fitness: c.activity?.score || 0, bornGen: c.legs.length, legs: c.legs,
    parts: { grade: c.grade || 'B', aprScore: 0, momentum24h: mom || 0, calm: '—', feeDragPct: 0, impactLegs: 0 } }} style={DIAL_STYLE[c.dial] || 'momentum'} rank={0} budget={20} aura={c.aura || (TIER_FX[c.activity?.tier] || TIER_FX.calm).aura} /> : null; };
  const status = Object.fromEntries((br.board || []).map(x => [x.key, x]));
    const secs = Math.max(0, Math.round((b.endsAt || now) - now));
  // HP: each side starts at 100 and loses 6 HP per point the other card is ahead since the bell (min 5) — who's winning, at a glance
  const hp = (me, them) => Math.max(5, Math.min(100, 100 - Math.max(0, (them || 0) - (me || 0)) * 6));
  const [spot, setSpot] = useState(0); const [hold, setHold] = useState(false);
  // 🎥 one arena, a spotlight per fight — auto-cycles every 9s (pauses while you hover / focus), dots to jump between fights
  useEffect(() => { if (hold || b.pairs.length < 2 || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const t = setInterval(() => setSpot(x => (x + 1) % b.pairs.length), 9000); return () => clearInterval(t); }, [hold, b.pairs.length]);
  const cur = Math.min(spot, Math.max(0, b.pairs.length - 1));
  // the REAL card in each corner, with effects from its live activity tier (aura, embers, heat) — like the stage
  const corner = (p, k, i) => { const x = p[k]; const o = p[k === 'a' ? 'b' : 'a']; const h = hp(x.now, o.now); const st = status[x.key]; const c = cardOf(x.key);
    const tier = c?.activity?.tier || 'calm'; const fx = TIER_FX[tier] || TIER_FX.calm; const lead = (x.now || 0) - (o.now || 0);
    return <div key={fx[x.key] && fx[x.key].d < 0 ? `hit-${fx[x.key].t}` : x.key} className={`bf-corner ${k} t-${tier} ${lead > 0.05 ? 'is-lead' : lead < -0.05 ? 'is-hit' : ''} ${h < 40 ? 'is-hurt' : ''} ${fx[x.key] && fx[x.key].d < 0 && Date.now() - fx[x.key].t < 1500 ? 'is-shake' : ''}`}>
      {fx[x.key] && <span key={fx[x.key].t} className={`bf-dmg ${fx[x.key].d >= 0 ? 'up' : 'down'}`} aria-hidden="true">{fx[x.key].d >= 0 ? '+' : ''}{fx[x.key].d.toFixed(2)}%</span>}
      {cheers[x.key] && <span key={cheers[x.key].t} className="bf-cheer-burst" aria-hidden="true">{['🔥', '🚀', '💎', '🦍', '⚡', '🔥'].map((e, j) => <i key={j} style={{ '--i': j }}>{e}</i>)}</span>}
      <span className="bf-c-aura" aria-hidden="true" /><div className="bf-c-embers" aria-hidden="true">{Array.from({ length: fx.embers }, (_, e) => <i key={e} style={{ '--i': e }} />)}</div>
      <div className="bf-c-card" role="button" tabIndex={0} onClick={e => { if (!e.target.closest('.fcd-flip')) setCfgKey(x.key); }} onKeyDown={e => e.key === 'Enter' && setCfgKey(x.key)}
        data-tip="Tap to expand: configs, DNA, coins — copy it to your Lab" data-testid={`bf-card-${k}-${i}`}>{c?.legs?.length ? <FuseCard c={{ pools: c.legs.map(l => l.pairAddress), fitness: c.activity?.score || 0, bornGen: c.legs.length, legs: c.legs,
          parts: { grade: c.grade || 'B', aprScore: 0, momentum24h: x.now || 0, calm: '—', feeDragPct: 0, impactLegs: 0 } }} style={DIAL_STYLE[c.dial] || 'momentum'} rank={i * 2 + (k === 'a' ? 0 : 1)} budget={20} aura={c.aura || fx.aura} />
        : <span className="bf-c-ghost">{x.emoji || '🃏'}</span>}</div>
      <div className="bf-c-meta">
        <span className="bf-c-name"><button type="button" className="bf-fighter" onClick={() => setCfgKey(x.key)} aria-label={`${x.name} config`} data-tip="Card config — copy it to your Fuse Lab" data-testid={`bf-cfg-${k}-${i}`}>{x.emoji || '🃏'}</button>
          <b>{x.name}</b>{st && <em className={`bf-br br-${st.status}`}>{st.status === 'winners' ? '🏆' : st.status === 'losers' ? '💀' : '✕'} {st.w}–{st.l}</em>}</span>
        <span className="bf-hp" data-tip={`HP ${Math.round(h)} — drops while the other card is ahead`}><i style={{ transform: `scaleX(${h / 100})` }} /><small>HP {Math.round(h)}</small></span>
        <em className={`bf-c-pct m-num fl-tick ${x.now >= 0 ? 'm-pos' : 'm-neg'}`} key={x.now}>{pc(x.now)}</em>
        {x.paper && <span className="bf-paper" data-tip="This battle's paper book: $100 dealt at true fills (pool impact both ways) → what selling it all would pay now. Fees apart.">📄 {fmt$(x.paper.startUsd)} → {fmt$(x.paper.valueUsd)}</span>}
        <span className="bf-btns"><button type="button" className={`m-btn bf-back ${mine === x.key ? 'is-on' : ''}`} disabled={!!mine} onClick={() => back(x.key)} data-tip="Free · points only" data-testid={`back-${k}-${i}`}>{mine === x.key ? '✓ Backed' : '⚔ Back'} · {(x.backers || 0) + (mine === x.key ? 1 : 0)}</button>
        <button type="button" className="m-btn bf-buy" onClick={() => buyBack(x)} data-tip="Buy this card (you own it) — counts on the 💰 bar" data-testid={`buyback-${k}-${i}`}>💰 Buy & back</button>
        <button type="button" className="m-btn bf-cheer" onClick={() => cheer(x.key)} data-tip="Cheer your fighter (just for fun)" data-testid={`cheer-${k}-${i}`}>📣 {(cheers[x.key] || {}).n || ''}</button>
        <button type="button" className="m-btn bf-audit" onClick={() => setAudit(x)} data-tip="Paper audit: every coin's true-fill entry → now, $ in → $ now, fees apart, past books" data-testid={`audit-${k}-${i}`}>📜 Audit</button></span></div></div>; };
  const lg = b.league;
  return <section className="m-card m-live bf" data-testid="battlefield"><header className="m-row"><span className="m-label">{lg ? `⚔ ARENA SEASON #${lg.n} · ROUND ${Math.min(lg.round + 1, lg.rounds)}/${lg.rounds}` : `⚔ BATTLEFIELD · BRACKET #${br.season}`}</span>
    <small className="m-dim" data-testid="bf-rules">{lg ? `every card on its own $${lg.startUsd} book all season · bigger move this bell wins (3 pts · draw 1) · ≤ $${lg.cut.usd} or −${lg.cut.dropPct}% in ${lg.cut.bells} rounds = cycled for a playground card · top of the table after ${lg.rounds} rounds is crowned` : 'bigger move since the bell wins · 2 losses = out · last card standing is crowned'}</small>
    <span className="m-seg bf-lens" role="tablist" aria-label="Timeframe">{PIT_LENSES.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={lens === k} className={lens === k ? 'active' : ''} data-tip={tip} onClick={() => setLens(k)} data-testid={`bf-lens-${k}`}>{l}</button>)}</span>
    <b className={`bf-bell m-num ${secs < 60 ? 'is-soon' : ''}`} key={secs < 60 ? secs : 'x'}>🔔 {Math.floor(secs / 60)}:{String(secs % 60).padStart(2, '0')}</b></header>
    {audit && <PaperAudit k={audit.key} name={audit.name} onClose={() => setAudit(null)} />}
    {cfgCard && <CardConfig c={cfgCard} onClose={() => setCfgKey(null)} onLoad={onLoad} onBack={b.pairs.some(p => [p.a.key, p.b.key].includes(cfgKey)) && !mine ? () => back(cfgKey) : null}
      onBuyBack={b.pairs.some(p => [p.a.key, p.b.key].includes(cfgKey)) ? () => buyBack({ key: cfgKey, name: cfgCard.name }) : null} />}
    <div className={`bf-arena ${secs > 0 && secs <= 60 ? 'is-final' : ''}`} onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)} onFocus={() => setHold(true)} onBlur={() => setHold(false)} data-testid="bf-arena">
      <span className="bf-floor" aria-hidden="true" /><span className="bf-beam l" aria-hidden="true" /><span className="bf-beam r" aria-hidden="true" />
      {b.pairs.length > 0 && <span key={`intro-${b.endsAt}`} className="bf-intro" aria-hidden="true"><i className="bf-intro-flash" /><b>{lg ? `ROUND ${Math.min(lg.round + 1, lg.rounds)}` : 'NEW BELL'}</b><em>FIGHT!</em></span>}
      <span className="bf-show" aria-hidden="true"><i className="bfs-sweep a" /><i className="bfs-sweep b" /><i className="bfs-flash" />{Array.from({ length: 18 }, (_, k) => <i key={k} className="bfs-dot" style={{ '--i': k }} />)}</span>
      {b.pairs.length > 1 && <div className="bf-tabs" role="tablist" aria-label="Fights">{b.pairs.map((p, i) => <button key={p.a.key + p.b.key} type="button" role="tab" aria-selected={cur === i} className={cur === i ? 'active' : ''} onClick={() => setSpot(i)} data-testid={`bf-tab-${i}`}>
        FIGHT {i + 1}<small>{p.a.emoji} vs {p.b.emoji}</small></button>)}</div>}
      {b.pairs.map((p, i) => { const d = p.a.now - p.b.now; const share = Math.max(0.08, Math.min(0.92, 0.5 + d / 20));
        const lane = status[p.a.key]?.status === 'losers' && status[p.b.key]?.status === 'losers' ? 'losers' : status[p.a.key]?.status === 'winners' && status[p.b.key]?.status === 'winners' ? 'winners' : 'cross';
        return <div key={p.a.key + p.b.key} className={`bf-pair lane-${lane} ${d > 0.05 ? 'a-lead' : d < -0.05 ? 'b-lead' : 'even'} ${cur === i ? 'is-spot' : 'is-off'}`} style={{ '--i': i }} data-testid={`battle-${i}`} aria-hidden={cur !== i}>
          {flip[i] && Date.now() - flip[i] < 4000 && <span key={flip[i]} className="bf-flipbanner" aria-live="polite">⚡ LEAD CHANGE!</span>}
          <span className="bf-lane">{lg ? `🏆 ROUND ${Math.min(lg.round + 1, lg.rounds)} OF ${lg.rounds} · ${(status[p.a.key]?.rank ? `#${status[p.a.key].rank}` : '')} vs ${(status[p.b.key]?.rank ? `#${status[p.b.key].rank}` : '')}` : lane === 'winners' ? '🏆 WINNERS BRACKET' : lane === 'losers' ? '💀 LOSERS BRACKET · LOSE = OUT' : '⚔ CROSSOVER'}{lens !== 'bell' && <i className="bf-lensnote"> · reading the last {lens === '60' ? 'hour' : `${lens} min`} (the bell still decides)</i>}</span>
          <p className="bf-call" key={pitCall(p, secs)} aria-live="polite" data-testid={`bf-call-${i}`}>🎙 {pitCall(p, secs)}</p>
          <span className="bf-crowd" data-tip="How the crowd is split: free backs + bought backs. Points only today — real bids on a fight are planned, and this split becomes the odds." data-testid={`bf-crowd-${i}`}>
            <b className="m-num">{crowdShare(p)}%</b><i><i style={{ transform: `scaleX(${crowdShare(p) / 100})` }} /></i><b className="m-num">{100 - crowdShare(p)}%</b><small>CROWD</small></span>
          {corner(p, 'a', i)}
          <div className="bf-mid">
            <DuelBoard p={p} />
            <PitReel p={p} still={cur !== i} />
            <RaceLine p={p} />
            <i className="bf-tug" data-tip="Who's ahead since the bell"><i style={{ transform: `scaleX(${share})` }} /></i>
            <div className="bf-bars" data-testid={`bars-${i}`}>
              <span className="bf-bar is-paid" data-tip="Wallets that BOUGHT a side's card to back it (real buys, you own the card)"><small>{p.a.paidN || 0}</small><i><i style={{ transform: `scaleX(${tugShare(p.a.paidUsd || 0, p.b.paidUsd || 0)})` }} /></i><small>{p.b.paidN || 0}</small><em>💰 BUY BACKS {p.a.paidN || 0}/{p.b.paidN || 0} · ${Math.round(p.a.paidUsd || 0)}/${Math.round(p.b.paidUsd || 0)}</em></span>
              <span className="bf-bar is-free" data-tip="Free backs · +15 XP to back, winners count toward weekly quests → season rank"><small>{p.a.backers || 0}</small><i><i style={{ transform: `scaleX(${tugShare(p.a.backers || 0, p.b.backers || 0)})` }} /></i><small>{p.b.backers || 0}</small><em>⚔ BACKS {p.a.backers || 0}/{p.b.backers || 0} · +XP</em></span></div></div>
          {corner(p, 'b', i)}
          {cur === i && <div className="bf-tickrow"><CoinTicker legsA={cardOf(p.a.key)?.legs} legsB={cardOf(p.b.key)?.legs} nameA={p.a.name} nameB={p.b.name} /></div>}</div>; })}
    </div>
    {br.champions?.length > 0 && <Throne champs={br.champions} now={now} kingNode={nodeOf(br.champions[0].key, 0)} onOpen={k => cardOf(k) && setCfgKey(k)}
      challengers={power(br.board || []).filter(x => x.key !== br.champions[0].key && x.status !== 'out').slice(0, 2).map(x => ({ key: x.key, name: x.name, emoji: x.emoji, badge: `${x.w}W–${x.l}L`, node: nodeOf(x.key, x.pct) }))}
      onBuy={onLoad && (c => onLoad(c.legs, c.key?.startsWith('user:') ? { copyOf: c.key.slice(5), owner: c.name, champ: true, copyPct: (cardOf(c.key)?.copyPct || 10) * 2 } : { backName: c.name }))} />}
    {br.upNext?.length > 0 && <div className="bf-next" data-testid="bf-upnext"><span className="m-label">⏭ UP NEXT</span>{br.upNext.map((x, j) => <button key={x.key} type="button" className={`bf-nextcard br-${x.status}`} style={{ '--i': j }} onClick={() => setCfgKey(x.key)} data-tip="Fights at the next bell — tap for its config">
      <b>{x.emoji}</b><span>{x.name}</span><em>{x.status === 'winners' ? '🏆' : '💀'} {x.w}–{x.l}</em></button>)}</div>}
    {(br.board || []).length > 0 && <div className="bf-rail" data-testid="bf-power"><span className="m-label" data-tip="Every card in this season, top of the table first. 🔮 Call the champion (free) — right = season XP.">{lg ? `🏆 TABLE · ${b.bracket?.board?.length || 0}/${lg.fieldMax}` : '🥊 IN THE BRACKET'}</span>
      <div className="bf-rail-row">{power(br.board).map((x, i) => <span key={x.key} className={`bf-chip br-${x.status}`} style={{ '--i': i }}>
        <button type="button" className="bf-chip-name" onClick={() => setCfgKey(x.key)} data-tip="Config, coins and DNA — copy it to your Lab" data-testid={`power-cfg-${i}`}>{x.emoji} {x.name}</button>
        {x.pts != null ? <><em className="m-num" data-tip={`${x.w}W ${x.d || 0}D ${x.l}L — win 3 · draw 1`}>#{x.rank} · {x.pts} pts</em><small className={`m-num ${(x.usd || 0) >= (lg?.startUsd || 20) ? 'm-pos' : 'm-neg'}`} data-tip={`Its season book: started at $${lg?.startUsd || 20}`}>{fmt$(x.usd)}</small></>
          : <><em className="m-num">{x.status === 'out' ? '✕ out' : `${x.status === 'winners' ? '🏆' : '💀'} ${x.w}–${x.l}`}</em><small className={`m-num ${x.pct >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(x.pct)}</small></>}
        {x.status !== 'out' && <button type="button" className={`m-btn bf-call ${called === x.key ? 'is-on' : ''}`} disabled={!!called} onClick={() => callIt(x.key)} data-tip="Call it to win this bracket (free) — right = season XP" data-testid={`call-${i}`}>{called === x.key ? '✓' : '🔮'} {(x.calls || 0) + (called === x.key ? 1 : 0)}</button>}</span>)}</div></div>}
    {lg?.cycled?.length > 0 && <div className="bf-cycled" data-testid="bf-cycled"><span className="m-label">♻ CYCLED OUT</span>{lg.cycled.map(m => <small key={`${m.at}-${m.outKey}`}>{m.out} <em>{m.why}</em>{m.in ? ` → ${m.in}` : ''}</small>)}</div>}
    {b.log?.length > 0 && <div className="bf-log">{b.log.slice(0, 6).map(l => <small key={l.at + l.a} className={l.comeback ? 'is-comeback' : ''}>{l.draw ? `🤝 ${l.a} = ${l.b}` : `${l.comeback ? '🔥 COMEBACK ' : '🏆 '}${l.winner} beat ${l.winner === l.a ? l.b : l.a}`} <em>{pc(l.aMove)} vs {pc(l.bMove)}</em></small>)}</div>}
  </section>;
}

// ⚙ Every Arena card's config window: dial, exits, clock, stop mode, cycle and each coin's weight — copy it to the Fuse Lab
// (coins + configs come along, still editable) or back / buy it when it's fighting. Centered pop-up over a blurred page.
// What each DNA / config part means, in plain words (the legend under every card's config)
const CYCLE_WORDS = { off: 'keeps its own coins every round', steady: 'swaps a weak coin for the best runner', classic: 'majors → runners → majors → mixed',
  adaptive: 'losing → majors, +5% → runners, flat → mixed', safe: 'majors ⇄ mixed', press: 'runners ⇄ mixed', rescue: '🛡 safest ⇄ ⚖ breakeven', auto: 'the engine picks each round' };
const STOP_WORDS = { sell: 'a coin that hits its stop is sold', park: 'sold to SOL, bought back at entry with buyers', hold: 'never sold on a stop (the floor still protects)', replace: 'swapped for the best coin of its kind' };
export function CardConfig({ c, onClose, onLoad, onBack, onBuyBack }) {
  const [audit, setAudit] = useState(false);
  const [book, setBook] = useState(null);
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); document.body.classList.add('ce-open');
    return () => { window.removeEventListener('keydown', k); document.body.classList.remove('ce-open'); }; }, [onClose]);
  useEffect(() => { if (!c.kind || !c.id) return; fetch(apiUrl(`/api/reputation/fuses/paper?key=${encodeURIComponent(`${c.kind}:${c.id}`)}`)).then(r => r.json()).then(x => setBook(x?.live || null)).catch(() => {}); }, [c.kind, c.id]);
  const live = useLivePrices((c.legs || []).map(l => l.pairAddress));
  const cfg = c.cfg || {};
  const dna = c.dna || {};
  const copy = () => { onLoad?.(c.legs || [], { cfg: { ...cfg, ...(c.cycle ? { cycle: c.cycle } : {}), ...(c.dna ? { dna: c.dna } : {}) }, ...(c.kind === 'user' ? { copyOf: c.id, owner: c.owner, copyPct: c.copyPct } : {}) }); onClose(); };
  const bookLeg = pa => (book?.legs || []).find(x => x.pairAddress === pa);
  const rows = (c.legs || []).map(l => { const bl = bookLeg(l.pairAddress); const px = live.get?.(l.pairAddress)?.price || bl?.now; const entry = bl?.entry || l.entry;
    return { ...l, px, entry, pct: px && entry ? (px / entry - 1) * 100 : null, inUsd: bl?.inUsd, nowUsd: bl && px ? (bl.units || 0) * px : bl?.nowUsd, runner: l.runner || l.role === 'runner' }; });
  const pctCard = book ? book.pct : (c.index ? c.index - 100 : c.pnlPct);
  const cyc = dna.cycle || cfg.cycle || c.cycle;
  return createPortal(<div className="ce-shade is-pop" role="presentation" onClick={onClose} data-testid="card-config">
    <aside className="ce is-pop m-live cc-cfg ccx-win" role="dialog" aria-modal="true" aria-label={`${c.name} config`} onClick={e => e.stopPropagation()}>
      <header><span className="m-label">⚙ CARD · LIVE</span><h3>{c.emoji} {c.name}{c.dial && <span className={`ar-dial dl-${c.dial}`}>{DIAL_LABEL[c.dial]}</span>}</h3>
        <button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <div className="ccx-grid">
        {/* 🃏 the card itself, big and in its own design (drag to tilt · ⟲ flips to its money math) */}
        <div className="ccx-hero" data-testid="cfg-card">{(c.legs || []).length > 0 && <FuseCard c={{ pools: c.legs.map(l => l.pairAddress), fitness: c.activity?.score || 0, bornGen: c.legs.length, legs: c.legs,
          parts: { grade: c.grade || 'B', aprScore: 0, momentum24h: pctCard || 0, calm: '—', feeDragPct: 0, impactLegs: 0 } }} style={DIAL_STYLE[c.dial] || 'momentum'} rank={0} budget={20} aura={c.aura || ''} />}
          {c.tagline && <p className="m-dim">{c.tagline}</p>}
          <div className="cc-cfg-acts">{onLoad && <button type="button" className="m-btn primary m-go" onClick={copy} data-testid="cfg-copy">⚡ Copy to Fuse Lab</button>}
            {onBack && <button type="button" className="m-btn" onClick={() => { onBack(); onClose(); }} data-testid="cfg-back">⚔ Back it</button>}
            {c.kind && c.id && <button type="button" className="m-btn" onClick={() => setAudit(true)} data-tip="Paper audit: its battle books at true fills — entry → now per coin, $, fees apart, won / lost" data-testid="cfg-audit">📜 Paper audit</button>}
            {onBuyBack && <button type="button" className="m-btn bf-buy" onClick={() => { onBuyBack(); onClose(); }}>💰 Buy & back</button>}</div>
          <small className="m-dim">Copying loads the coins + these configs into your Lab — nothing moves until you approve one Fuse in.</small></div>
        <div className="ccx-main">
          <div className="ccx-pnl" data-testid="cfg-pnl">
            <span><small>CARD NOW</small><b className={`m-num fl-tick ${(pctCard || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={(pctCard || 0).toFixed(2)}>{pctCard == null ? '—' : pc(pctCard)}</b></span>
            {book && <span><small>PAPER BOOK</small><b className="m-num">{fmt$(book.startUsd)} → {fmt$(book.valueUsd)}</b><em className={book.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}>{book.pnlUsd >= 0 ? '+' : '−'}{fmt$(Math.abs(book.pnlUsd))}</em></span>}
            {c.record_wl && <span><small>BATTLES</small><b className="m-num">{c.record_wl.w}W · {c.record_wl.l}L</b></span>}
            <span><small>COINS</small><b className="m-num">{rows.length}</b><em>{rows.filter(r => r.runner).length} runners · {rows.filter(r => !r.runner).length} majors / pools</em></span></div>
          <div className="ccx-rows" role="table" aria-label="Coins, entry and live P&L">
            <div className="ccx-row is-head" role="row"><span>COIN</span><span>WEIGHT</span><span>ENTRY → NOW</span><span>P&L</span></div>
            {rows.map((l, i) => <div key={l.pairAddress} className="ccx-row" role="row" style={{ '--i': i }}><b>{l.runner ? '🏃' : '⚓'} ${l.symbol}</b>
              <span className="ccx-w"><i style={{ transform: `scaleX(${Math.min(1, (Number(l.weight) || 0) / 100)})` }} /><em className="m-num">{Math.round(Number(l.weight) || 0)}%</em></span>
              <span className="m-num">{l.entry ? `$${Number(l.entry).toPrecision(3)}` : '—'} → {l.px ? `$${Number(l.px).toPrecision(3)}` : '—'}</span>
              <em className={`m-num fl-tick ${(l.pct || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={l.pct == null ? 'x' : l.pct.toFixed(1)}>{l.pct == null ? '—' : pc(l.pct)}{l.nowUsd != null && <small> · {fmt$(l.nowUsd)}</small>}</em></div>)}</div></div>
        <div className="ccx-side">
          <section className="ccx-legend ccx-pane" data-testid="cfg-legend"><span className="m-label">🧬 HOW THIS CARD PLAYS</span>
            {cyc && <p><b>🔄 Cycle · {cyc}</b><span>{CYCLE_WORDS[cyc] || (String(cyc).includes(',') ? `its own: ${String(cyc).split(',').join(' → ')}` : '')}</span></p>}
            {(cfg.tp != null || cfg.sl != null) && <p><b>🎯 TP +{cfg.tp ?? '—'}% · SL −{cfg.sl ?? '—'}%</b><span>runners take profit at +{cfg.tp ?? '—'}%, stop at −{cfg.sl ?? '—'}%; ≥ +150% (or a round ≥ +80%) is 🏇 held instead</span></p>}
            {(dna.clock || cfg.rotateHours) && <p><b>⟳ Clock · {(v => (v >= 1 ? `${v}h` : `${Math.round(v * 60)}m`))(dna.clock || cfg.rotateHours)}</b><span>how often a weak (losing) coin may be swapped out</span></p>}
            {(dna.stop || cfg.slMode) && <p><b>✂ Stop · {dna.stop || cfg.slMode}</b><span>{STOP_WORDS[dna.stop || cfg.slMode] || ''}</span></p>}
            {dna.compound && <p><b>♻ Compound · {dna.compound}</b><span>{dna.compound === 'smart' ? 'gains go into the strongest coins' : dna.compound === 'even' ? 'gains split evenly over the other coins' : 'gains are not reinvested'}</span></p>}
            {dna.payoutPct != null && <p><b>💸 Payout · {dna.payoutPct}%</b><span>of PROFIT only — paid out only above what was put in; the rest stays in the card</span></p>}
            <p><b>🛟 Rescue</b><span>falls 50% under its start → safest ⇄ breakeven by itself</span></p></section>
          <section className="ccx-pane ccx-trail" data-testid="cfg-trail"><span className="m-label">📜 TRAIL · ITS PAPER BOOK</span>
            {(book?.events || []).length ? <ol>{book.events.slice(-7).reverse().map((e, i) => <li key={`${e.at}-${i}`} style={{ '--i': i }}><time className="m-num">{new Date(e.at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}</time><span>{e.why || e.kind}</span></li>)}</ol>
              : <small className="m-dim">The trail starts when this card steps into a battle: $100 dealt at true fills, every swap and the result land here.</small>}
            {book && <small className="m-dim">high {pc(book.hiPct || 0)} · low {pc(book.loPct || 0)} · fees {fmt$(book.feesUsd || 0)} apart</small>}</section>
        </div>
      </div>
    {audit && <PaperAudit k={`${c.kind}:${c.id}`} name={c.name || 'Card'} onClose={() => setAudit(false)} />}
    </aside></div>, document.body);
}

const DIAL_STYLE = { safe: 'steady', balanced: 'yield', degen: 'degen' };
const DIAL_LABEL = { safe: '🧊 COLD BLOOD', balanced: '⚡ VOLTAGE', degen: '🔥 INFERNO' };   // engine dials (backend runners.ENGINE_DIALS)
const SL_WORD = { sell: '✂ sell', park: '🅿 park', hold: '❄ hold' };
export function MegaCard({ c, i, onPicks, onLoad, onChat, chatOpen, onReplay }) {
  const [cfgOpen, setCfgOpen] = useState(false);
  const fx = TIER_FX[c.activity?.tier] || TIER_FX.calm;
  const live = useLivePrices((c.legs || []).map(l => l.pairAddress));
  const lp = liveStagePct(c, live);
  const move = lp ?? (c.index || 100) - 100;
  const runners = c.kind === 'lit' || c.kind === 'round';
  const use = () => (runners ? onPicks?.(c.legs.slice(0, MAX_RUNNERS).map(l => ({ mint: l.baseAddress, symbol: l.symbol, logo: l.logo, pairAddress: l.pairAddress, lane: 'runner' })))
    : onLoad?.(c.legs, c.kind === 'user' ? { copyOf: c.id, owner: c.owner, copyPct: c.copyPct } : null));
  return <article className={`ar-card t-${c.activity?.tier || 'calm'} ${c.dial ? `d-${c.dial}` : ''} ${c.bench ? 'is-bench' : ''}`} style={{ '--i': i, '--act': (c.activity?.score || 0) / 100 }} data-testid={`mega-${c.id}`}>
    <span className="ar-heat" aria-hidden="true" /><span className="ar-ring" aria-hidden="true" />{c.dial && <span className="ar-dialfx" aria-hidden="true"><i /><i /><i /></span>}
    <FuseCard c={{ pools: c.legs.map(l => l.pairAddress), fitness: c.activity?.score || 0, bornGen: c.legs.length, parts: { grade: c.grade || 'B', aprScore: 0, momentum24h: move, calm: '—', feeDragPct: 0, impactLegs: 0 }, legs: c.legs }}
      style={DIAL_STYLE[c.dial] || (c.kind === 'lit' ? 'degen' : 'momentum')} rank={0} budget={20} aura={c.aura || fx.aura} />
    <div className="ar-embers" aria-hidden="true">{Array.from({ length: fx.embers }, (_, k) => <i key={k} style={{ '--i': k }} />)}</div>
    <div className="ar-meta"><b>{c.emoji} {c.name}{c.version ? <small className="ar-ver" data-tip="Engine version of this card — the engine re-deals it every round"> v.{String(c.version).padStart(2, '0')}</small> : null}</b>{c.dial && <span className={`ar-dial dl-${c.dial}`}>{DIAL_LABEL[c.dial]}</span>}
      {c.dnaLabel && <span className="ar-dna" data-tip="This card's DNA — its own cycle, compound, payout, clock and stop (no two cards alike)" data-testid={`dna-${c.id}`}>🧬 {c.dnaLabel}</span>}
      {c.cfg && <span className="ar-cfg" data-testid={`cfg-${c.id}`}><i data-tip="Take-profit per runner">TP +{c.cfg.tp}%</i><i data-tip="Stop per runner">SL −{c.cfg.sl}%</i>{c.cfg.rotateHours != null && <i data-tip="Rotates weak coins every">⟳ {c.cfg.rotateHours >= 1 ? `${c.cfg.rotateHours}h` : `${Math.round(c.cfg.rotateHours * 60)}m`}</i>}{c.cfg.slMode && <i data-tip="At the stop">{SL_WORD[c.cfg.slMode] || c.cfg.slMode}</i>}</span>}
      <span className="ar-act" data-tip="Activity: FEELESS buys + buyers (24h), $ flow through its coins, index move. Drives the effects."><small>ACT</small><i style={{ transform: `scaleX(${(c.activity?.score || 0) / 100})` }} /><em className="m-num">{c.activity?.score || 0}</em></span>
      {c.record_wl && <span className="ar-wl" data-tip="Arena battle record (wins – losses – draws)" data-testid={`wl-${c.id}`}>⚔ {c.record_wl.w}–{c.record_wl.l}{c.record_wl.d ? `–${c.record_wl.d}` : ''}</span>}
      {(c.streak?.tier || c.compound?.tier || c.copies > 0) && <span className="ar-badges">{c.streak?.tier && <StreakBadge s={c.streak} />}{c.compound?.tier && <CompoundBadge s={c.compound} />}{c.copies > 0 && <span className="ar-copies" data-tip="Traders who fused this card too">⚡ {c.copies} {c.copies === 1 ? 'copy' : 'copies'}</span>}</span>}
      <small className="m-dim">{c.kind === 'scenario' ? "🎨 creator's pick · engine card" : c.kind === 'auto' ? `⚔ arena deal · ${c.tagline || ''}` : c.kind === 'feecat' ? `🐱 sim book · ${c.record?.winRate ?? '—'}% wins · ${(c.record?.realizedSol ?? 0) >= 0 ? '+' : ''}${c.record?.realizedSol ?? 0} SOL realized${c.record?.lives != null ? ` · ❤${c.record.lives}` : ''}` : c.kind === 'lit' ? '🔥 lit runner card' : c.kind === 'round' ? '⏳ this round · proving' : c.kind === 'user' ? `🃏 ${c.owner} · ${c.mode === 'swap' ? '⇄ swaps weak legs' : '🔒 holds together'}` : `⚛️ FEELESS card · ${c.legs.length} legs`} · <span className={`fl-tick ${move >= 0 ? 'm-pos' : 'm-neg'}`} key={move.toFixed(1)} data-tip={lp != null ? 'Live (3s prices)' : 'Last server update'}>{pc(move)}{lp != null && <i className="fl-livedot" />}</span>{c.buyers ? ` · ${c.buyers} buyers` : ''}</small>
      {cfgOpen && <CardConfig c={c} onClose={() => setCfgOpen(false)} onLoad={onLoad} />}
      <span className="ar-acts"><button type="button" className="m-btn" onClick={() => setCfgOpen(true)} data-tip="This card's config — copy it to your Fuse Lab" data-testid={`mega-cfg-${c.id}`}>⚙</button>{onReplay && <button type="button" className="m-btn" onClick={onReplay} data-tip="Replay the last 24h of this card" data-testid={`mega-replay-${c.id}`}>▶</button>}{c.chat && <button type="button" className={`m-btn ${chatOpen ? 'primary' : ''}`} onClick={onChat} aria-pressed={chatOpen} data-tip="This card's chat" data-testid={`mega-chat-${c.id}`}>💬</button>}
      <button type="button" className="m-btn primary m-go" onClick={use} data-testid={`mega-use-${c.id}`}>{runners ? 'Use runners →' : c.kind === 'user' ? '⚡ Fuse this too' : c.legs.length > 3 ? 'Load top 3 →' : 'Load →'}</button></span></div>
  </article>;
}

// ---- My cards: live cards + every action ------------------------------------------------------------------------------
const balancesOf = async (addr, legs) => Object.fromEntries(await Promise.all(legs.filter(l => l.mint && l.soldUsd == null).map(l => fetch(apiUrl(`/api/reputation/balance/${addr}/${l.mint}`)).then(x => (x.ok ? x.json() : null)).catch(() => null).then(b => [l.mint, b]))));
const solPrice = () => fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL_MINT}`).then(r => r.json()).then(d => Number(d?.[SOL_MINT]?.usdPrice) || 0).catch(() => 0);
export const collectSplit = (pct, legs) => (legs || []).filter(l => l.soldUsd == null).map(l => ({ ...l, pct }));

// 🤖 What this card's settings ask for — exactly what the FUSE Card program will run on its own once you sign (docs/GO_LIVE.md).
// Today every step is a one-tap alert you approve; nothing sells by itself yet.
export function AutoSpec({ r }) {
  const clk = h => (h >= 1 ? `${h}h` : `${Math.round(h * 60)}m`);
  const rows = [['🔄 Cycle', ({ adaptive: '🧠 adaptive — losing → majors, winning → runners', classic: '⚓→🔥 classic — anchor → degen → anchor → mixed', safe: '⚓⇄⚖ safe — anchor ⇄ mixed', press: '🔥⇄⚖ press — degen ⇄ mixed' })[r.cycle] || '➡ steady'], ['⟳ Reshuffle', `every ${clk(r.rotateHours || 24)}${r.mode === 'swap' ? ' · auto-rotate on' : ' · hold (you switch)'}`],
    ['💸 Profit split', `${r.payoutPct ?? 100}% to your wallet · ${100 - (r.payoutPct ?? 100)}% compounds (${r.compoundStyle || 'smart'})`], ['🛑 At a stop', ({ sell: '✂ sell', park: '🅿 park & buy back', hold: '❄ hold' })[r.slMode || 'sell']],
    ['🎯 Coin limits', `${Object.keys(r.legGuard || {}).length} coins with their own TP / SL`], ['❄ Frozen', `${(r.frozen || []).length} coin${(r.frozen || []).length === 1 ? '' : 's'} the engine never touches`]];
  return <section className="ce-spec" data-testid={`spec-${r.id}`}><span className="m-label">🤖 AUTO SPEC · WHAT THE CARD WILL DO</span>
    <dl>{rows.map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{v}</dd></React.Fragment>)}</dl>
    <small className="m-dim">Today: one-tap alerts you approve. With the FUSE Card contract (after audit + your signature) these run on their own and payouts land in your wallet without a click.</small></section>;
}

const ROTATE_PICKS = [[5 / 60, '5m'], [0.25, '15m'], [1, '1h'], [12, '12h'], [24, '24h']];   // ⇄ card clock (server: fuse_hq.ROTATE_OPTIONS)
const COIN_MODE = { sell: '✂ sell', park: '🅿 park', hold: '❄ hold' };
export function MyCards({ addr }) {
  const [d, setD] = useState(null);
  const [act, setAct] = useState(null);   // {id, kind, ...} — one open action at a time
  const [realN, setRealN] = useState(0);   // 💵 HQ real cards shown above (then "no cards" is just a one-liner)
  const load = useCallback(() => addr && fetch(apiUrl(`/api/reputation/fuses/pnl/${addr}`)).then(r => (r.ok ? r.json() : null)).then(setD).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 30000); window.addEventListener('feeless:fuse-pnl', load);
    return () => { clearInterval(t); window.removeEventListener('feeless:fuse-pnl', load); }; }, [load]);
  const ses = () => { const s = addr && readChatSession(addr); if (!s) toast.error('Open chat once to sign in your wallet first.'); return s; };
  const refresh = () => setTimeout(() => window.dispatchEvent(new Event('feeless:fuse-pnl')), 1200);
  // 🎚 One dial re-plans the whole card (server expands the id: every coin's TP/SL, profit level, collect/compound, rotation).
  const setRisk = async (r, risk) => { const s = ses(); if (!s || r.risk === risk) return;
    try { await post('/api/reputation/fuses/plan', { address: addr, session: s, id: r.id, plan: { risk } }); toast.success(`${RISK_DIALS[risk].label}: ${RISK_DIALS[risk].why}`); load(); } catch (e) { toast.error(e.message); } };
  const setAdv = async (r, patch) => { const s = ses(); if (!s) return;
    const plan = { mode: r.mode || 'hold', onProfit: r.onProfit || 'collect', at: r.autoYield?.at, legs: Object.fromEntries(Object.entries(r.legGuard || {}).map(([pa, g]) => [pa, { tp: g.tp, sl: g.sl }])), rotateHours: r.rotateHours || 24, slMode: r.slMode || 'sell', cycle: r.cycle || 'steady', payoutPct: r.payoutPct ?? 100, compoundStyle: r.compoundStyle || 'smart', autoFees: r.autoFees !== false, ...patch };
    try { await post('/api/reputation/fuses/plan', { address: addr, session: s, id: r.id, plan }); toast.success(patch.legs && patch.rideAt != null ? '🎯 Strategy on — exits, freeze and coin limits set' : patch.rideAt != null ? (patch.rideAt ? `❄ Freeze at +${patch.rideAt}%` : '❄ Freeze off') : patch.rideTrail != null ? `⇄ Sell alert −${patch.rideTrail}% off its peak` : patch.autoFees != null ? (patch.autoFees ? '💸 The card pays its round packs from profit' : 'You pay round packs yourself') : patch.payoutPct != null ? `Profit split: ${patch.payoutPct}% to your wallet` : patch.compoundStyle ? `Compound: ${patch.compoundStyle}` : patch.cycle ? `Round cycle: ${patch.cycle}` : patch.rotateHours ? `Rotation every ${(ROTATE_PICKS.find(([h]) => Math.abs(h - patch.rotateHours) < 0.005) || [0, `${patch.rotateHours}h`])[1]}` : `On a coin stop: ${patch.slMode}`); load(); } catch (e) { toast.error(e.message); } };
  const setMode = async (r, mode) => { const s = ses(); if (!s || (r.mode || 'hold') === mode) return;
    try { await post('/api/reputation/fuses/mode', { address: addr, session: s, id: r.id, mode }); toast.success(mode === 'swap' ? 'Swap mode: weak legs get a one-tap swap alert' : 'Hold mode: the card stays together'); load(); } catch (e) { toast.error(e.message); } };
  const open = useCallback(async (r, kind, extra = {}) => {
    if (act?.id === r.id && act.kind === kind && !extra.pct) { setAct(null); return; }
    if (kind === 'withdraw' || kind === 'take') {
      const bal = await balancesOf(addr, r.legs); const pct = extra.pct || (kind === 'withdraw' ? 100 : 50);
      setAct({ id: r.id, kind, pct, legs: (extra.legs || r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)), bal });
    } else if (kind === 'topup') {
      setAct({ id: r.id, kind, sol: extra.sol || '0.1', mode: extra.mode || 'equal', pick: extra.pick || '', solUsd: await solPrice() });
    } else if (kind === 'rebalance' || kind === 'switch') {
      const [bal, solUsd] = await Promise.all([balancesOf(addr, r.legs), solPrice()]);
      setAct({ id: r.id, kind, bal, solUsd, ...extra });
    } else setAct({ id: r.id, kind, ...extra });
  }, [act, addr]);
  // Alert links: ?collect=<id>&pct= (💸 auto-collect), ?rebalance=<id>, ?unfuse=<id>
  useEffect(() => { if (!d?.rows || act) return; const q = new URLSearchParams(window.location.search); const find = id => id && d.rows.find(x => x.id === id && !x.closed);
    const c = find(q.get('collect')); if (c) { open(c, 'take', { pct: Number(q.get('pct')) || 33, ...(q.get('legs') ? { legs: q.get('legs').split(',') } : {}) }); return; }
    const rb = find(q.get('rebalance')); if (rb) { open(rb, 'rebalance'); return; }
    const tu = find(q.get('topup')); if (tu) { open(tu, 'topup', { mode: 'one', pick: q.get('pair') }); return; }   // ↩ buy-back alert
    const sw = find(q.get('switch')); if (sw) { open(sw, 'switch', { from: q.get('out'), toMint: q.get('in'), toSymbol: q.get('sym') || 'NEW', toPair: q.get('pair') || undefined, toRole: 'runner' }); return; }
    const u = find(q.get('unfuse')); if (u) open(u, 'withdraw'); }, [d]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!addr) return <div className="m-card fp-empty"><b>Connect your Solana wallet to see your Fuse cards.</b></div>;
  if (!d) return <div className="m-card"><span className="loader" /> Loading your cards…</div>;
  const openRows = (d.rows || []).filter(r => !r.closed);
  return <><WeatherStrip /><HqRealCards addr={addr} onCount={setRealN} /><RealCardFixes addr={addr} /><MyCardsBody realN={realN} d={d} openRows={openRows} act={act} setAct={setAct} open={open} setMode={setMode} setRisk={setRisk} setAdv={setAdv} addr={addr} ses={ses} refresh={refresh} /></>;
}

function RealCardFixes({ addr }) {
  const { call } = useAdmin();
  const [cards, setCards] = useState([]);
  const [busy, setBusy] = useState('');
  const load = useCallback(() => fetch(apiUrl('/api/reputation/fuses/prime')).then(r => r.ok ? r.json() : null).then(x => setCards((x?.cards || []).filter(c => c.real))).catch(() => {}), []);
  useEffect(() => { if (!addr) return undefined; load(); const t = setInterval(() => !document.hidden && load(), 30000); window.addEventListener('feeless:prime', load); return () => { clearInterval(t); window.removeEventListener('feeless:prime', load); }; }, [addr, load]);
  if (!cards.length) return null;
  const recover = (c, r) => { if (!window.confirm(`Sell old ${r.symbol} still stuck in the Fuse wallet and return the confirmed SOL to ${c.label} card cash?`)) return;
    const key = `recover-${c.tpl}-${r.mint}`; setBusy(key); call('/admin/fuse-wallet/recover-sell', { method: 'POST', body: JSON.stringify({ tpl: c.tpl, mint: r.mint }) })
      .then(() => { toast.success(`${r.symbol} recovery sell started → ${c.label} cash`); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const payout = c => { const b = c.realBook || {}; const amt = Number(b.profitCashAvailableUsd || 0); if (!(amt > 0)) { toast.error('No profit cash is available yet'); return; }
    if (!window.confirm(`Pay out ${m$(amt)} of PROFIT from ${c.label}? Your funded principal stays in the card.`)) return;
    const key = `payout-${c.tpl}`; setBusy(key); call('/admin/fuse-wallet/payout-profit', { method: 'POST', body: JSON.stringify({ tpl: c.tpl, usd: amt }) })
      .then(x => { toast.success(`Paid out ${m$(x.paidUsd || amt)} profit · principal untouched`); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const withdraw = (c, usdNow) => { const left = Math.max(0, (c.realBook?.fundedUsd || 0) - (usdNow || 0));
    if (!window.confirm(`Take ${m$(usdNow)} of card cash out of ${c.label}? Your principal becomes ${m$(left)} — profit is then anything the card is worth above ${m$(left)}.`)) return;
    setBusy(`wd-${c.tpl}`); call('/admin/fuse-wallet/withdraw-cash', { method: 'POST', body: JSON.stringify({ tpl: c.tpl }) })
      .then(x => { toast.success(`↗ ${m$(x.tookUsd)} out · principal now ${m$(x.principalUsd)}`); window.dispatchEvent(new Event('feeless:prime')); }).catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const retryDead = (c, o) => { const key = `dead-${c.tpl}-${o.side}-${o.mint}`; setBusy(key);
    call('/admin/fuse-wallet/retry-dead', { method: 'POST', body: JSON.stringify({ tpl: c.tpl, side: o.side, mint: o.mint }) })
      .then(() => { toast.success(o.side === 'sell' ? `Retrying sell → ${c.label} cash` : `Retrying buy from ${c.label} cash`); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const sellAllDead = c => { const holdings = [...(c.realBook?.offCard || []), ...(c.realBook?.recoverable || [])]; const n = new Set(holdings.map(x => x.mint)).size;
    const now = (c.realBook?.offCard || []).reduce((sum, x) => sum + Number(x.usd || 0), 0);
    if (!n || !window.confirm(`Attempt to sell ${n} confirmed dead/off-card coin${n === 1 ? '' : 's'} (current quoted value ${m$(now)}) into ${c.label} card cash? Original cost cannot be restored after a coin loses market value. Failed buys with no confirmed coins are ignored. Cash and P&L update only after each sell confirms.`)) return;
    const key = `dead-all-${c.tpl}`; setBusy(key); call('/admin/fuse-wallet/recover-sell-all', { method: 'POST', body: JSON.stringify({ tpl: c.tpl }) })
      .then(x => { toast.success(`${x.queued || n} confirmed holding${(x.queued || n) === 1 ? '' : 's'} queued → ${c.label} cash · sells on the next keeper tick (~1 min), even while the card is paused`); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => toast.error(e.message)).finally(() => setBusy('')); };
  const useful = cards.filter(c => (c.realBook?.recoverable || []).length || (c.realBook?.profitAvailableUsd || 0) > 0 || (c.realBook?.fundedUsd || 0) > 0);
  if (!useful.length) return null;
  return <section className="m-card m-live" data-testid="real-card-fixes"><span className="m-label">🛠 REAL CARD CASH / RECOVERY</span>
    {useful.map(c => { const b = c.realBook || {}; const rec = b.recoverable || []; const off = b.offCard || []; const recon = b.reconciliation || {}; const profit = Number(b.profitAvailableUsd || 0); const cash = Number(b.profitCashAvailableUsd || 0); const recoveryNow = off.reduce((sum, x) => sum + Number(x.usd || 0), 0); const recoveryCost = off.reduce((sum, x) => sum + Number(x.costUsd || 0), 0); return <div key={c.tpl} className="fw-tier real-recovery-tier">
      <span><b>{c.label}</b><small className="m-dim"> · you have {m$(b.fundedUsd || 0)} in · profit above that {m$(profit)} · payable cash now {m$(cash)}</small>
        {profit <= 0 && <small className="m-dim">No payout yet — the card pays out only what it is worth above the money you still have in it.</small>}
        {profit > 0 && cash <= 0 && <small className="m-dim">Profit exists in coins, but none is card cash yet. It becomes payable as sells/rotations return SOL.</small>}</span>
      <span className="m-row"><button type="button" className="m-btn" disabled={cash <= 0 || !!busy} onClick={() => payout(c)} data-testid={`profit-payout-${c.tpl}`} data-tip="Profit = what the card is worth above the money you still have in it. Only profit that is already card cash can be paid out.">💸 Payout profit {m$(cash)}</button>
        <button type="button" className="m-btn" disabled={!(recon.cardCashUsd > 0.01) || !!busy} onClick={() => withdraw(c, recon.cardCashUsd)} data-testid={`withdraw-cash-${c.tpl}`}
          data-tip={`Take the card's cash out to your wallet. Your principal drops by the same amount (${m$(b.fundedUsd || 0)} → ${m$(Math.max(0, (b.fundedUsd || 0) - (recon.cardCashUsd || 0)))}), so profit is then counted above what is still in. Sell part of a coin first to make cash.`}>↗ Withdraw card cash {m$(recon.cardCashUsd || 0)}</button></span>
      {recon.cardEquityUsd != null && <div className="m-note" data-testid={`card-reconciliation-${c.tpl}`}><b>Card truth: {m$(recon.cardEquityUsd)}</b><small className="m-dim">Confirmed positions + {m$(recon.cardCashUsd || 0)} card cash. Wallet funds outside this card: {m$(recon.outsideCardUsd || 0)}; gas reserve stays separate.</small></div>}
      {(b.deadOrders || []).length > 0 && <details className="fw-tiers" data-testid={`dead-orders-${c.tpl}`}><summary>🧯 Failed attempts ({b.deadOrders.length}) · audit only</summary><small className="m-dim">Failed buys never became holdings and are not included in card value.</small>
        {(b.deadOrders || []).map((o, i) => <div key={`${o.side}-${o.mint || o.symbol}-${i}`} className="fw-tier"><span><b>{o.side === 'buy' ? '🟢 BUY' : '🔴 SELL'} ${o.symbol}</b><small className="m-dim"> · {o.err || o.status}</small></span>
          <button type="button" className="m-btn" disabled={!!busy || !o.mint} onClick={() => retryDead(c, o)}>{busy === `dead-${c.tpl}-${o.side}-${o.mint}` ? 'Retrying…' : o.side === 'sell' ? 'Retry sell → card cash' : 'Retry buy from card cash'}</button></div>)}</details>}
      {(off.length > 0 || rec.length > 0) && <button type="button" className="m-btn danger" disabled={!!busy} onClick={() => sellAllDead(c)} data-testid={`dead-sell-all-${c.tpl}`}>{busy === `dead-all-${c.tpl}` ? 'Queueing confirmed sells…' : `Attempt sell current value ${m$(recoveryNow)} → ${c.label} cash`}</button>}
      {off.length > 0 && <div className="fw-tiers" data-testid={`off-card-${c.tpl}`}><small className="m-dim">⏳ Confirmed wallet coins already included in Card truth · cost {m$(recoveryCost)} → current value {m$(recoveryNow)}. Only confirmed sale proceeds become card cash:</small>
        {off.map(o => { const cost = Number(o.costUsd || 0); const now = Number(o.usd || 0); const loss = cost > 0 ? ((now / cost) - 1) * 100 : null; return <div key={o.mint} className="fw-tier"><span><b>${o.symbol}</b><small className="m-dim"> · {o.status}</small></span><b>{m$(cost)} cost → {m$(now)} now{loss != null ? ` · ${loss.toFixed(1)}%` : ''}</b></div>; })}</div>}
      {rec.length > 0 && <div className="fw-tiers" data-testid={`dead-swaps-${c.tpl}`}><small className="m-dim">⚠ Failed / dead swaps still held by the Fuse wallet:</small>
        {rec.map(r => <div key={r.mint} className="fw-tier"><span><b>${r.symbol}</b><small className="m-dim"> · {r.lastErr || r.lastStatus || 'old keeper balance'}</small></span>
          <button type="button" className="m-btn danger" disabled={!!busy} onClick={() => recover(c, r)} data-testid={`dead-sell-${r.symbol}`}>{busy === `recover-${c.tpl}-${r.mint}` ? 'Selling…' : 'Sell → card cash'}</button></div>)}</div>}
    </div>; })}</section>;
}
const EARN_KIND = { sell: '💰 Profit / sell', buy: '⇄ Switched in', topup: '♻ Compounded / topped up' };
const sumKind = (r, k) => (r.events || []).filter(e => e.kind === k).reduce((a, e) => a + (e.usd || 0), 0);

function MyCardsBody({ realN, d, openRows, act, setAct, open, setMode, setRisk, setAdv, addr, ses, refresh }) {
  const [earn, setEarn] = useState(null);
  // ❄ Freeze a coin: the engine (swap mode / auto-rotate) never touches it — only the holder switches it.
  const freeze = async (r, l, on) => { const s = ses(); if (!s) return;
    try { await post('/api/reputation/fuses/freeze', { address: addr, session: s, id: r.id, pairAddress: l.pairAddress, frozen: on }); toast.success(on ? `❄ $${l.symbol} frozen — only you switch it` : `$${l.symbol} back under the engine`); refresh(); } catch (e) { toast.error(e.message); } };
  // per-coin stop mode: follow the card, or this coin sells / parks / holds on its own
  const coinMode = async (r, l, m) => { const s = ses(); if (!s) return;
    try { await post('/api/reputation/fuses/coin-mode', { address: addr, session: s, id: r.id, pairAddress: l.pairAddress, slMode: m }); toast.success(m === 'card' ? `$${l.symbol} follows the card` : `$${l.symbol} at its stop: ${COIN_MODE[m]}`); refresh(); } catch (e) { toast.error(e.message); } };
  const coinCfg = async (r, l, patch) => { const s = ses(); if (!s) return;
    try { await post('/api/reputation/fuses/coin-mode', { address: addr, session: s, id: r.id, pairAddress: l.pairAddress, ...patch }); toast.success(`$${l.symbol} ${patch.tp != null ? `TP +${patch.tp}%` : patch.sl != null ? `SL −${patch.sl}%` : patch.rotateHours ? 'own replace clock set' : 'follows the card clock'}`); refresh(); } catch (e) { toast.error(e.message); } };
  const live = useLivePrices(openRows.flatMap(r => r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)));
  const held = openRows.length ? liveBook(openRows, live) : { pnlUsd: d.held?.pnlUsd, pnlPct: d.held?.pnlPct, value: d.held?.valueUsd };
  return <section className="fp-cards" data-testid="my-cards">
    {!(realN && !openRows.length) && <div className="m-row fp-book"><span className="m-label">CARDS YOU HOLD</span><b className={`m-num fl-tick ${(held.pnlUsd || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={(held.pnlUsd || 0).toFixed(2)} data-testid="held-pnl">{m$(held.pnlUsd)} <small>{pc(held.pnlPct)}</small><i className="fl-livedot" /></b>
      <small className="m-dim">{m$(held.value)} now · {openRows.length} open · all-time {m$(d.pnlUsd)}</small>{d.feebackUsd > 0 && <span className="m-chip ok" data-tip="Fuse Fee-Back: your unlocked share of the fees you paid on cards">🎁 {m$(d.feebackUsd)} Fee-Back</span>}</div>}
    {!openRows.length && (realN ? <small className="m-dim" data-testid="no-bought-cards">Cards you buy from this wallet show here too, next to the real tier cards above.</small>
      : <div className="m-card fp-empty"><b>No open cards.</b><small className="m-dim">Build one in the Lab — 3 pools + up to 3 runners.</small></div>)}
    <div className="fp-cgrid">{openRows.map(r => <div key={r.id} className={`fp-cell ${r.onArena ? 'is-arena' : ''}`}><LiveFuseCard r={r} aura={r.onArena ? 'fire' : ''} />
      <CoinTable legs={r.legs.filter(l => l.soldUsd == null).map(l => { const px = live.get?.(l.pairAddress)?.price || l.priceNow; const nowUsd = px && l.tokens ? l.tokens * px + (l.realizedUsd || 0) : (l.valueUsd || 0);
        return { pairAddress: l.pairAddress, symbol: l.symbol, role: l.role, entryPx: l.tokens ? l.usd / l.tokens : null, nowPx: px, inUsd: l.usd || 0, nowUsd, pct: l.usd ? (nowUsd / l.usd - 1) * 100 : 0 }; })} />
      {r.missing?.length > 0 && <div className="fg-partial" data-testid={`missing-${r.id}`}><b>⚠ {r.missing.length} approved {r.missing.length === 1 ? 'coin' : 'coins'} didn't land</b><span>Only confirmed coins count on this card. Add {r.missing.length === 1 ? 'it' : 'them'} with ＋ Top up, or ↩ Withdraw to sell back what landed.</span></div>}
      {r.heldShort?.length > 0 && <div className="fg-partial" data-testid={`short-${r.id}`}><b>🔗 Your wallet holds less than this card</b><span>Some coins left the wallet outside FEELESS — the card now counts only what's really there (checked on-chain every minute).</span></div>}
      <div className="fp-risk"><RiskDial value={r.risk || 'custom'} onChange={id => setRisk(r, id)} testid={`card-risk-${r.id}`} /></div>
      <StrategyPicks hours={r.rotateHours || 24} current={{ rideAt: r.rideAt || 0, rideTrail: r.rideTrail || 10 }} testid={`card-strats-${r.id}`}
        onApply={st => setAdv(r, { rideAt: Number(st.cfg.rideAt), rideTrail: Number(st.cfg.trail), legs: Object.fromEntries(r.legs.filter(l => l.soldUsd == null).map(l => [l.pairAddress, { tp: Number(st.cfg.tp), sl: Number(st.cfg.sl) }])) })} />
      <div className="fp-freeze" data-testid={`card-freeze-${r.id}`}><span data-tip="A coin that runs past this is frozen: its take-profit alert waits while it keeps making highs. You get ONE sell alert when it falls off its peak (it still never sells by itself)">❄ Freeze at</span>
        <span className="m-seg" role="group">{[0, 10, 15, 20, 25, 50].map(v => <button key={v} type="button" className={(r.rideAt || 0) === v ? 'active' : ''} onClick={() => setAdv(r, { rideAt: v })} data-testid={`freeze-at-${r.id}-${v}`}>{v ? `+${v}%` : 'off'}</button>)}</span>
        <span data-tip="How far a frozen coin may fall from its highest price before the sell alert">⇄ off peak</span>
        <span className="m-seg" role="group">{[5, 8, 10, 15, 20, 30].map(v => <button key={v} type="button" disabled={!r.rideAt} className={(r.rideTrail || 10) === v ? 'active' : ''} onClick={() => setAdv(r, { rideTrail: v })} data-testid={`freeze-trail-${r.id}-${v}`}>−{v}%</button>)}</span></div>
      {r.beatCat?.length > 0 && <span className="fs-crown r-cat" data-tip="Weeks this card beat FeeCat's average trade" data-testid={`beatcat-${r.id}`}>🐱 Beat FeeCat ×{r.beatCat.length}</span>}
      {r.seasonWin && <span className={`fs-crown r-${r.seasonWin.rank}`} data-tip={`Fuse season · week of ${wk(r.seasonWin.week)} — +Fee-Back boost on this card`} data-testid={`crown-${r.id}`}>{MEDAL[r.seasonWin.rank]} #{r.seasonWin.rank} · week of {wk(r.seasonWin.week)}</span>}
      {(r.streak?.tier || r.compound?.tier || r.copies > 0) && <span className="ar-badges">{r.streak?.tier && <StreakBadge s={r.streak} />}{r.compound?.tier && <CompoundBadge s={r.compound} />}{r.copies > 0 && <span className="ar-copies" data-tip="Traders who copied this card — you earn a share of their FEELESS fee">⚡ {r.copies} {r.copies === 1 ? 'copy' : 'copies'} · {m$(r.copyEarnedUsd)} earned</span>}</span>}
      {r.feeback && <small className={`fp-fb ${r.feeback.unlocked ? 'is-on' : ''}`} data-tip={`Fee-Back: ${r.feeback.pct}% of the $${(r.feeback.feesUsd || 0).toFixed(2)} fees you paid on this card${r.feeback.arena ? ' (incl. Arena bonus)' : ''}`}>🎁 {r.feeback.unlocked ? `${m$(r.feeback.usd)} back · ${r.feeback.pct}%` : 'Fee-Back'}{r.feeback.next ? ` · ${r.feeback.next}` : ''}</small>}
      <div className="fp-quick" role="toolbar" aria-label={`${r.name} quick actions`}>
        <button type="button" className="m-btn primary m-go" data-tip="Sell 50% of every coin back to SOL (change to 25 / 33 / 100% or pick coins before you approve)" onClick={() => open(r, 'take', { pct: 50 })} data-testid={`act-take-${r.id}`}>💰 Take 50%</button>
        <SwitchButton r={r} onClick={() => open(r, 'switch')} />
        <button type="button" className="m-btn danger" data-tip="Sell every coin back to SOL — one approval. The card closes and its receipt goes to your profile." onClick={() => open(r, 'withdraw')} data-testid={`act-withdraw-${r.id}`}>↩ Withdraw all</button>
      </div>
      <button type="button" className="m-btn fp-earn" onClick={() => setEarn(r.id)} data-testid={`act-earn-${r.id}`} data-tip="Profit taken out, profit compounded back in (and where), every move — plus 💸 Collect">🪟 Open card · {m$(r.realizedUsd || 0)} out · {m$(sumKind(r, 'topup'))} compounded{r.autos?.length ? ` · ⚡${r.autos.length}` : ''}{r.frozen?.length ? ` · ❄${r.frozen.length}` : ''}</button>
      {earn === r.id && <CardEarnings title={r.name || 'Your card'} taken={r.realizedUsd || 0} compounded={sumKind(r, 'topup')}
        book={{ putIn: r.costUsd || 0, held: Math.max(0, (r.valueUsd || 0) - (r.realizedUsd || 0)), taken: r.realizedUsd || 0, fees: r.feesPaidUsd, rounds: r.roundsUsed, roundsPaid: r.roundsPaidUsd, owed: r.roundsOwedUsd }}
        events={[...(r.events || [])].reverse().map(e => ({ ...e, label: EARN_KIND[e.kind] || e.kind, to: e.kind === 'sell' ? ['cash'] : e.kind === 'topup' ? [e.symbol] : undefined, symbol: e.kind === 'topup' ? undefined : e.symbol }))}
        gainNow={Math.max(0, Math.min(r.pnlUsd || 0, (r.valueUsd || 0) - (r.realizedUsd || 0)))} onCollect={() => { setEarn(null); open(r, 'yield', { at: r.autoYield?.at || d.rules?.yieldDefault || 50, levels: d.rules?.yieldLevels || [25, 50, 100, 200] }); }} onClose={() => setEarn(null)}
        autos={r.autos || []} extra={<><TrailSummary events={(r.events || []).map(e => ({ ...e, kind: e.kind === 'sell' ? 'tp' : e.kind === 'buy' ? 'rotate' : e.kind }))} legs={r.legs.filter(l => l.soldUsd == null)} /><AutoSpec r={r} /><CardRounds card={r} onChange={() => refresh()} /></>} legs={r.legs.filter(l => l.soldUsd == null).map(l => ({ ...l, firstEntry: l.tokens ? l.usd / l.tokens : null, frozen: (r.frozen || []).includes(l.pairAddress), mode: (r.coinModes || {})[l.pairAddress] || 'card', tp: (r.legGuard || {})[l.pairAddress]?.tp, sl: (r.legGuard || {})[l.pairAddress]?.sl, rot: (r.coinRotate || {})[l.pairAddress] || 0 }))} onFreeze={(l, on) => freeze(r, l, on)}
        onMode={(l, m) => coinMode(r, l, m)} cardMode={r.slMode || 'sell'} onCoinCfg={(l, patch) => coinCfg(r, l, patch)}
        actions={[{ label: '＋ Top up', tip: 'Add SOL — equal split, by weight, or into one coin. One approval.', onClick: () => { setEarn(null); open(r, 'topup'); }, testid: `cw-topup-${r.id}` },
          { label: '💰 Take 50%', onClick: () => { setEarn(null); open(r, 'take', { pct: 50 }); } },
          { label: '⇄ Switch', disabled: r.nextSwitchAt > Date.now() / 1000, tip: 'One pool or coin per 24h', onClick: () => { setEarn(null); open(r, 'switch'); } },
          { label: '↩ Withdraw', cls: 'danger', onClick: () => { setEarn(null); open(r, 'withdraw'); } }]} />}
      <details className="fp-more"><summary>⋯ More · rotate · auto-collect · rebalance · limits · replay · charts</summary>
        <div className="m-seg fp-mode" role="radiogroup" aria-label="Card mode">{[['hold', '🔒 Hold · switch by hand', 'The card stays as you built it. You may still switch ONE pool or coin every 24h, your pick.'], ['swap', '🤖 Auto-rotate daily', `Once a day, if a coin fails a runner gate or drops ${d.rules?.swapDropPct ?? 25}%, we pre-fill the swap for the best gated runner — one approval. Still max one switch per 24h.`]].map(([k, l, tip]) =>
        <button key={k} type="button" role="radio" aria-checked={(r.mode || 'hold') === k} className={(r.mode || 'hold') === k ? 'active' : ''} data-tip={tip} onClick={() => setMode(r, k)} data-testid={`mode-${k}-${r.id}`}>{l}</button>)}</div>
        <div className="fp-adv" data-testid={`adv-${r.id}`}><span className="m-label" data-tip="Your card's own clock: how often you may switch a coin">⇄ ROTATE EVERY</span>
          <div className="m-seg">{ROTATE_PICKS.map(([h, l]) => <button key={l} type="button" className={Math.abs((r.rotateHours || 24) - h) < 0.005 ? 'active' : ''} onClick={() => setAdv(r, { rotateHours: h })} data-testid={`rot-${l}-${r.id}`}>{l}</button>)}</div>
          <span className="m-label" data-tip="Sell = the stop alert sells it · 🅿 Park = sell to SOL, then a one-tap buy-back alert when it's back at entry with buyers · ❄ Hold = no stop alerts">ON A COIN STOP</span>
          <span className="m-label" data-tip="Share of each profit take paid to your wallet — the rest compounds">💸 PROFIT SPLIT</span>
          <div className="m-seg">{[0, 25, 50, 75, 100].map(v => <button key={v} type="button" className={(r.payoutPct ?? 100) === v ? 'active' : ''} onClick={() => setAdv(r, { payoutPct: v, onProfit: v > 0 ? 'collect' : 'compound' })} data-testid={`pay-${v}-${r.id}`}>{v}%</button>)}</div>
          <div className="m-seg">{[['smart', '🧲 Smart'], ['even', '⚖ Even'], ['off', '✋ Off']].map(([k, l]) => <button key={k} type="button" className={(r.compoundStyle || 'smart') === k ? 'active' : ''} onClick={() => setAdv(r, { compoundStyle: k })} data-testid={`cmp-${k}-${r.id}`}>{l}</button>)}</div>
          <span className="m-label" data-tip="Adaptive: a losing card's weak coin swaps into a major, a winning card's into a fresh runner">🔄 ROUND CYCLE</span>
          <div className="m-seg">{[['steady', '➡ Steady'], ['classic', '⚓→🔥 Classic'], ['adaptive', '🧠 Adaptive'], ['safe', '⚓⇄⚖ Safe'], ['press', '🔥⇄⚖ Press'], ['rescue', '🛟 Rescue'], ['auto', '🤖 Auto']].map(([k, l]) => <button key={k} type="button" className={(r.cycle || 'steady') === k ? 'active' : ''} onClick={() => setAdv(r, { cycle: k })} data-testid={`cyc-${k}-${r.id}`}>{l}</button>)}</div>
          <CycleBuilder value={r.cycle} onChange={v => setAdv(r, { cycle: v })} />
          <div className="m-seg">{[['sell', 'Sell'], ['park', '🅿 Park & buy back'], ['hold', '❄ Hold']].map(([k, l]) => <button key={k} type="button" className={(r.slMode || 'sell') === k ? 'active' : ''} onClick={() => setAdv(r, { slMode: k })} data-testid={`sl-${k}-${r.id}`}>{l}</button>)}</div>
          <span className="m-label" data-tip="When the card's 5 rounds run out and it's up more than the pack price, it pays +5 rounds from its profit (owed until the next take). Never while it's flat or down. Swap fees always come out of the swap itself.">💸 FEES</span>
          <div className="m-seg">{[[true, '💸 Card pays from profit'], [false, '✋ I pay']].map(([k, l]) => <button key={l} type="button" className={(r.autoFees !== false) === k ? 'active' : ''} onClick={() => setAdv(r, { autoFees: k })} data-testid={`fees-${k ? 'card' : 'me'}-${r.id}`}>{l}</button>)}</div></div>
        <div className="fp-acts" role="toolbar" aria-label={`${r.name} more actions`}>
        <button type="button" className={`m-btn ${r.autoYield ? 'is-armed' : ''}`} data-tip="Auto-collect: alert + pre-filled Collect profit when the card is up +X% (sells only the gain). You approve once." onClick={() => open(r, 'yield', { at: r.autoYield?.at || d.rules?.yieldDefault || 50, levels: d.rules?.yieldLevels || [25, 50, 100, 200] })} data-testid={`act-yield-${r.id}`}>💸 {r.autoYield ? `Auto +${Math.round(r.autoYield.at)}%` : 'Auto-collect'}</button>
        <button type="button" className={`m-btn ${r.drift >= 5 ? 'is-warn' : ''}`} data-tip={`Back to the weights you bought (drift ${Math.round(r.drift || 0)} pts) — one approval`} onClick={() => open(r, 'rebalance')} data-testid={`act-rebalance-${r.id}`}>⚖ Rebalance</button>
        <button type="button" className={`m-btn ${r.guard && !r.guard.firedAt ? 'is-armed' : ''}`} data-tip="Take-profit / stop-loss / trailing on the whole card" onClick={() => open(r, 'limits', { tp: r.guard?.tp || 50, sl: r.guard?.sl || 20, trail: r.guard?.trail || '', legs: Object.fromEntries(Object.entries(r.legGuard || {}).map(([pa, g]) => [pa, { tp: g.tp ?? '', sl: g.sl ?? '' }])), onProfit: r.onProfit || 'collect' })} data-testid={`act-limits-${r.id}`}>🎯 Limits</button>
        <button type="button" className="m-btn" data-tip="Replay this card's last 24h" onClick={() => open(r, 'replay')} data-testid={`act-replay-${r.id}`}>▶ Replay</button>
        <span className="fp-legcharts" aria-label="Open each coin's chart (your trades marked)">{r.legs.filter(l => l.soldUsd == null).map(l => <button key={l.pairAddress} type="button" className="m-btn" data-tip={`${l.symbol}: open its chart — your confirmed buy is marked on the candles`} onClick={() => openCoin({ mint: l.mint, pairAddress: l.pairAddress, symbol: l.symbol, runner: l.role === 'runner' })} data-testid={`chart-${l.pairAddress}`}>📈 {l.symbol}</button>)}</span>
      </div></details>
      {act?.id === r.id && <ActionPanel r={r} act={act} setAct={setAct} addr={addr} ses={ses} refresh={refresh} />}
    </div>)}</div>
  </section>;
}

// ⇄ Switch: one pool or coin per card every 24h (hard-coded server-side; top-ups / rebalances don't count).
function SwitchButton({ r, onClick }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { if (!(r.nextSwitchAt > now)) return undefined; const t = setInterval(() => setNow(Date.now() / 1000), 30000); return () => clearInterval(t); }, [r.nextSwitchAt, now]);
  const wait = r.nextSwitchAt > now ? r.nextSwitchAt - now : 0;
  return <button type="button" className="m-btn" disabled={wait > 0} onClick={onClick} data-testid={`act-switch-${r.id}`}
    data-tip={wait ? `One switch per card every 24h — next in ${Math.floor(wait / 3600)}h ${Math.floor((wait % 3600) / 60)}m` : 'Swap ONE pool or coin for another (sell + buy in one approval). One switch per 24h.'}>
    ⇄ Switch{wait ? <small className="fp-wait"> · {Math.ceil(wait / 3600)}h</small> : ''}</button>;
}

function ActionPanel({ r, act, setAct, addr, ses, refresh }) {
  const close = () => setAct(null);
  if (act.kind === 'replay') return <CardReplay c={{ kind: 'user', id: r.id, name: r.name, emoji: '🃏' }} onClose={close} />;
  const live = r.legs.filter(l => l.soldUsd == null);
  if (act.kind === 'take' || act.kind === 'withdraw') {
    const chosen = r.legs.filter(l => act.legs.includes(l.pairAddress));
    const orders = unfuseOrders(chosen, act.bal, addr, 150, act.pct);
    return <div className="m-card fp-panel" data-testid="act-panel-take">
      {act.kind === 'take' && <><div className="m-seg">{[25, 33, 50, 100].map(p => <button key={p} type="button" className={act.pct === p ? 'active' : ''} onClick={() => setAct({ ...act, pct: p })}>{p}%</button>)}
        {![25, 33, 50, 100].includes(act.pct) && <button type="button" className="active" title="Gain only — your base stays in the card">{act.pct}% · gain only</button>}</div>
        <div className="m-row">{live.map(l => <label key={l.pairAddress} className="m-toggle"><input type="checkbox" checked={act.legs.includes(l.pairAddress)} onChange={e => setAct({ ...act, legs: e.target.checked ? [...act.legs, l.pairAddress] : act.legs.filter(x => x !== l.pairAddress) })} />{l.symbol} <small>{m$(l.heldUsd ?? l.valueUsd)}</small></label>)}</div></>}
      <FuseGo side="sell" orders={orders} position={r.id} onClose={() => { close(); refresh(); }} />
    </div>;
  }
  if (act.kind === 'yield') {
    const save = async off => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/auto-yield', { address: addr, session: s, id: r.id, at: Number(act.at) || 50, off }); toast.success(off ? 'Auto-collect off' : `Auto-collect armed at +${act.at}%`); close(); refresh(); } catch (e) { toast.error(e.message); } };
    const gain = Number(act.at) || 50; const sell = (gain / (100 + gain)) * 100;
    return <div className="m-card fp-panel" data-testid="act-panel-yield"><b>💸 Auto-collect profit</b>
      <div className="m-seg" role="radiogroup" aria-label="Collect at">{(act.levels || [25, 50, 100, 200]).map(v => <button key={v} type="button" role="radio" aria-checked={gain === v} className={gain === v ? 'active' : ''} onClick={() => setAct({ ...act, at: v })} data-testid={`yield-lvl-${v}`}>+{v}%</button>)}</div>
      <small className="m-dim">Counted from your confirmed buy (price move only — card P&L never mixes in fees). Fees show on the receipt when you sell (≈ {m$(r.exitFeeUsd)} now).</small>
      <p className="m-note">At +{gain}% we alert you (inbox + phone) with <b>Collect profit</b> pre-filled: it sells {sell.toFixed(1)}% of each leg — just the gain — and your base stays in the card. After you collect it re-arms from the new value. <b>FEELESS never signs for you</b>: you approve once, fees only on that sell.</p>
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => save(false)} data-testid="yield-save">Arm auto-collect</button>{r.autoYield && <button type="button" className="m-btn" onClick={() => save(true)}>Turn off</button>}<button type="button" className="m-btn" onClick={close}>Cancel</button></div></div>;
  }
  if (act.kind === 'limits') {
    const save = async off => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/guard', { address: addr, session: s, id: r.id, off, tp: Number(act.tp) || 0, sl: Number(act.sl) || 0, trail: Number(act.trail) || 0 }); toast.success(off ? 'Limits off' : 'Limits armed'); close(); refresh(); } catch (e) { toast.error(e.message); } };
    const f = (k, label, sign) => <label className="m-field"><span>{label}</span><span className="m-row">{sign}<input className="m-input m-num" inputMode="decimal" placeholder="off" value={act[k]} onChange={e => setAct({ ...act, [k]: e.target.value.replace(/[^0-9.]/g, '') })} />%</span></label>;
    const legLim = (pa, k, v) => setAct({ ...act, legs: { ...act.legs, [pa]: { ...(act.legs?.[pa] || {}), [k]: v.replace(/[^0-9.]/g, '') } } });
    const savePlan = async () => { const s = ses(); if (!s) return;
      try { await post('/api/reputation/fuses/plan', { address: addr, session: s, id: r.id, plan: { mode: r.mode || 'hold', onProfit: act.onProfit, legs: Object.fromEntries(Object.entries(act.legs || {}).map(([pa, v]) => [pa, { tp: Number(v.tp) || null, sl: Number(v.sl) || null }])) } });
        toast.success('Coin limits saved'); refresh(); } catch (e) { toast.error(e.message); } };
    return <div className="m-card fp-panel" data-testid="act-panel-limits"><b>🎯 Card limits</b><div className="m-row">{f('tp', 'Take profit', '+')}{f('sl', 'Stop loss', '−')}{f('trail', 'Trailing', '')}</div>
      <p className="m-note">Free to set. We check every minute and alert you with a one-tap exit; fees only if you exit.</p>
      <b>Per coin</b><div className="fp-leglims">{live.map(l => { const v = act.legs?.[l.pairAddress] || {}; const g = r.legGuard?.[l.pairAddress];
        return <div key={l.pairAddress} className={`fp-leglim ${g?.firedAt ? 'is-fired' : ''}`}><b>{l.symbol}</b><small className={(l.pnlPct || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(l.pnlPct)}</small>
          <label>TP +<input className="m-input m-num" inputMode="decimal" placeholder="off" value={v.tp ?? ''} onChange={e => legLim(l.pairAddress, 'tp', e.target.value)} data-testid={`leglim-tp-${l.pairAddress}`} />%</label>
          <label>SL −<input className="m-input m-num" inputMode="decimal" placeholder="off" value={v.sl ?? ''} onChange={e => legLim(l.pairAddress, 'sl', e.target.value)} />%</label>{g?.firedAt && <em>fired</em>}</div>; })}</div>
      <div className="m-row"><span className="m-dim">On profit</span><div className="m-seg">{[['collect', '💸 Collect'], ['compound', '♻ Compound']].map(([k, l]) => <button key={k} type="button" className={act.onProfit === k ? 'active' : ''} onClick={() => setAct({ ...act, onProfit: k })}>{l}</button>)}</div>
        <button type="button" className="m-btn" onClick={savePlan} data-testid="leglim-save">Save coin limits</button></div>
      <div className="fg-acts"><button type="button" className="m-btn primary m-go" onClick={() => save(false)}>Arm limits</button>{r.guard && <button type="button" className="m-btn" onClick={() => save(true)}>Turn off</button>}<button type="button" className="m-btn" onClick={close}>Cancel</button></div></div>;
  }
  const px = Object.fromEntries(r.legs.map(l => [l.pairAddress, Number(l.priceNow) || 0]));
  const record = (landed, s) => {   // sells close those legs; buys merge into the card
    const sells = landed.filter(l => l.side === 'sell').map(l => l.signature); const buys = landed.filter(l => l.side === 'buy');
    [5000, 20000].forEach(ms => setTimeout(() => {
      if (sells.length) post('/api/reputation/fuses/position/close', { address: addr, session: s, id: r.id, signatures: sells }).catch(() => {});
      if (buys.length) post('/api/reputation/fuses/position/switch', { address: addr, session: s, id: r.id, legs: buys.map(b => ({ pairAddress: b.pairAddress, symbol: b.symbol, role: b.role, signature: b.signature })) }).catch(() => {});
      refresh(); }, ms));
  };
  if (act.kind === 'rebalance') {
    const orders = rebalanceOrders(r, act.bal, px, act.solUsd, addr, 5);
    const auto = async on => { const s = ses(); if (!s) return; try { await post('/api/reputation/fuses/guard', on ? { address: addr, session: s, id: r.id, rebalance: 10 } : { address: addr, session: s, id: r.id, off: true }); toast.success(on ? 'Auto-rebalance on (alerts at 10 pts drift)' : 'Auto-rebalance off'); refresh(); } catch (e) { toast.error(e.message); } };
    return <div className="m-card fp-panel" data-testid="act-panel-rebalance"><div className="m-row"><b>⚖ Rebalance</b><label className="m-toggle"><input type="checkbox" checked={Boolean(r.autoRebalance)} onChange={e => auto(e.target.checked)} data-testid="auto-rebalance" />Auto-rebalance alerts</label></div>
      {!orders.length ? <p className="m-dim">Every leg is within 5 points of its weight — nothing to do.</p>
        : <><ul className="fp-moves">{orders.map(o => <li key={o.leg.pairAddress}>{o.target.symbol}: {o.why}</li>)}</ul><FuseGo side="sell" orders={orders} onLanded={record} onClose={close} /></>}</div>;
  }
  if (act.kind === 'topup') {
    const orders = topupOrders(r.legs, act.sol, act.mode, addr, act.pick);
    const usdOf = x => (act.solUsd ? m$(Number(x) * act.solUsd) : '');
    return <div className="m-card fp-panel" data-testid="act-panel-topup"><div className="m-row"><b>＋ Top up with SOL</b><small className="m-dim">buys merge into this card · one approval</small></div>
      <div className="m-row"><label className="m-field"><span>SOL</span><input className="m-input m-num" inputMode="decimal" value={act.sol} onChange={e => setAct({ ...act, sol: e.target.value.replace(/[^0-9.]/g, '') })} data-testid="topup-sol" /></label><small className="m-dim">{usdOf(act.sol)}</small>
        <div className="m-seg" role="radiogroup" aria-label="Split">{[['equal', '⚖ Equal', 'Same SOL into every coin'], ['weight', '📊 By weight', 'Keeps the card\'s current mix'], ['one', '🎯 One coin', 'All into the coin you pick']].map(([k, l, tip]) =>
          <button key={k} type="button" role="radio" aria-checked={act.mode === k} className={act.mode === k ? 'active' : ''} data-tip={tip} onClick={() => setAct({ ...act, mode: k, pick: act.pick || live[0]?.pairAddress })} data-testid={`topup-${k}`}>{l}</button>)}</div></div>
      {act.mode === 'one' && <div className="m-seg">{live.map(l => <button key={l.pairAddress} type="button" className={act.pick === l.pairAddress ? 'active' : ''} onClick={() => setAct({ ...act, pick: l.pairAddress })}>{l.symbol}</button>)}</div>}
      <ul className="fp-moves">{orders.map(o => <li key={o.leg.pairAddress}>{o.leg.symbol}: +{Number(o.request.amount).toFixed(4)} SOL <small className="m-dim">{usdOf(o.request.amount)}</small></li>)}</ul>
      {orders.length ? <FuseGo side="sell" orders={orders} onLanded={record} onClose={close} /> : <small className="m-dim">Enter at least 0.001 SOL.</small>}</div>;
  }
  // switch: sell one leg, buy a new coin (by mint) with roughly what it returns
  const leg = r.legs.find(l => l.pairAddress === act.from);
  const sellO = leg ? unfuseOrders([leg], act.bal, addr, 150, 100)[0] : null;
  const solOut = leg && act.solUsd ? ((Number(leg.heldUsd) || 0) / act.solUsd) * 0.97 : 0;
  const buyO = act.toMint && solOut >= 0.001 ? { leg: { pairAddress: act.toPair || act.toMint, symbol: act.toSymbol, role: act.toRole || 'pool' }, target: { mint: act.toMint, symbol: act.toSymbol },
    request: { input_mint: SOL_MINT, output_mint: act.toMint, amount: solOut.toFixed(9).replace(/\.?0+$/, ''), slippage_bps: 150, wallet: addr } } : null;
  return <div className="m-card fp-panel" data-testid="act-panel-switch"><b>⇄ Switch a leg</b>
    <label className="m-field"><span>Sell</span><select className="m-input" value={act.from || ''} onChange={e => setAct({ ...act, from: e.target.value })}><option value="">Pick a leg…</option>{live.map(l => <option key={l.pairAddress} value={l.pairAddress}>{l.symbol} · {m$(l.heldUsd)}</option>)}</select></label>
    <label className="m-field"><span>Buy instead (token address)</span><input className="m-input" placeholder="Paste the new coin's mint" value={act.toMint || ''} onChange={e => setAct({ ...act, toMint: e.target.value.trim(), toSymbol: act.toSymbol || 'NEW' })} /></label>
    <input className="m-input" placeholder="Symbol (shown on your card)" value={act.toSymbol || ''} onChange={e => setAct({ ...act, toSymbol: e.target.value.slice(0, 12) })} />
    {sellO && buyO ? <FuseGo side="sell" orders={[sellO, buyO]} onLanded={record} onClose={close} /> : <small className="m-dim">Pick the leg to sell and the coin to buy — both happen in one approval (≈{solOut.toFixed(3)} SOL moves across).</small>}</div>;
}

// ---- Profile › ⚛️ Fuse score: real card P&L, season medals, copies, streaks, holding + reputation (every point cited).
// The performance half also feeds back into the wallet's trust score (cached, −3…+6), so Fuse and rep move together.
export function FuseScore({ address }) {
  const [s, setS] = useState(null);
  useEffect(() => { let alive = true; if (address) fetch(apiUrl(`/api/reputation/fuses/score/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setS(x)).catch(() => {}); return () => { alive = false; }; }, [address]);
  if (!s || !s.cards) return null;
  const deg = Math.max(0, Math.min(100, s.score)) * 3.6;
  return <section className="wp-card fsc" data-testid="fuse-score"><div className="fsc-ring" style={{ '--deg': `${deg}deg` }}><span><b className="m-num">{s.score}</b><small>FUSE</small></span></div>
    <div className="fsc-body"><h3>⚛️ Fuse score</h3><small className="m-dim">{s.cards} card{s.cards === 1 ? '' : 's'} · performance {s.perf}/75 · reputation {s.rep}/25</small>
      <ul>{s.parts.map(p => <li key={p.label}><span>{p.label}</span><b className={`m-num ${p.points >= 0 ? 'm-pos' : 'm-neg'}`}>{p.points >= 0 ? '+' : ''}{p.points}</b></li>)}</ul></div></section>;
}

// ---- Profile › Fuse cards: every card the wallet holds (live) + one total P&L for all of them -----------------------------
export function FuseHeldCards({ address }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = () => address && fetch(apiUrl(`/api/reputation/fuses/pnl/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); return () => { alive = false; clearInterval(t); }; }, [address]);
  const held = (d?.rows || []).filter(r => !r.closed);
  const live = useLivePrices(held.flatMap(r => r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)));
  if (!held.length) return null;
  const bk = liveBook(held, live);
  return <section className="wp-card fp-held" data-testid="fuse-held"><div className="fp-held-head"><h3>🃏 Fuse cards</h3>
    <b className={`m-num fl-tick ${bk.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}`} key={bk.pnlUsd.toFixed(2)}>{m$(bk.pnlUsd)} <small>{pc(bk.pnlPct)}</small><i className="fl-livedot" /></b><small className="m-dim">{held.length} held · {m$(bk.value)} now · live</small></div>
    <div className="fp-held-row">{held.slice(0, 6).map(r => <div key={r.id} className="fp-held-card"><LiveFuseCard r={r} aura={r.onArena ? 'fire' : ''} /><small className="m-dim">{r.mode === 'swap' ? '⇄ swaps weak legs' : '🔒 holds together'}{r.onArena ? ' · 🏟 on Arena' : ''}</small></div>)}</div></section>;
}

// ---- Profile › Fuse receipts ----------------------------------------------------------------------------------------
export function FuseReceipts({ address }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; if (address) fetch(apiUrl(`/api/reputation/fuses/receipts/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {}); return () => { alive = false; }; }, [address]);
  if (!d?.receipts?.length) return null;
  const EV = { buy: '🟢 Bought', sell: '🔴 Sold', topup: '♻ Topped up', switch: '⇄ Switched' };
  return <section className="wp-card fp-receipts" data-testid="fuse-receipts"><h3>Fuse receipts</h3><small className="m-dim">Every withdrawn card, tap one for its whole story · fees shown apart, never inside P&L</small>
    <div className="fr-list">{d.receipts.map(r => <details key={r.id} className="fr-item" data-testid={`receipt-${r.id}`}>
      <summary><b>{r.name || 'Fuse card'}</b><small className="m-dim">{r.legs.map(l => l.symbol).join(' · ')} · {new Date((r.at || 0) * 1000).toLocaleDateString()} → {r.closedAt ? new Date(r.closedAt * 1000).toLocaleDateString() : 'open'}</small>
        <span className={`m-num ${r.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}`}>{m$(r.pnlUsd)} ({pc(r.pnlPct)})</span></summary>
      <div className="fr-body">
        <div className="fr-kv"><span><small>PUT IN</small><b className="m-num">{m$(r.costUsd)}</b></span><span><small>TOOK OUT</small><b className="m-num">{m$(r.realizedUsd || r.valueUsd)}</b></span>
          <span data-tip="FEELESS fee from the fee ledger (the flat $/coin bundle price or your % on bigger buys) + an estimate of Solana network fees. Paid at each buy / sell — that's why P&L doesn't include them."><small>FEES (APART)</small><b className="m-num m-dim">{m$((r.feesUsd || 0) + (r.netUsd || 0))}</b><em>{m$(r.feesUsd || 0)} FEELESS + ≈{m$(r.netUsd || 0)} network</em></span></div>
        <ul className="fr-legs">{r.legs.map(l => <li key={l.pairAddress + (l.sig || '')}><b>{l.role === 'runner' ? '🏃 ' : ''}${l.symbol}</b><span>in {m$(l.usd)} → out {m$(l.soldUsd ?? l.valueUsd)}</span><em className={l.pnlPct >= 0 ? 'm-pos' : 'm-neg'}>{pc(l.pnlPct)}</em>
          {l.sig && <a href={`https://solscan.io/tx/${l.sig}`} target="_blank" rel="noopener noreferrer" data-tip="The buy on-chain">tx ↗</a>}</li>)}</ul>
        {r.events?.length > 0 && <ol className="fr-tl">{r.events.map((e, i) => <li key={i}><b>{EV[e.kind] || e.kind}</b>{e.symbol && <span>${e.symbol}</span>}{e.usd != null && <em className="m-num">{m$(e.usd)}</em>}<time className="m-dim">{new Date((e.at || 0) * 1000).toLocaleString()}</time></li>)}</ol>}
        <div className="m-row fr-share"><ShareGifButton className="m-btn" label="🎞 Share receipt" card={{ mascot: 'feecat', tone: r.pnlUsd >= 0 ? 'up' : 'down', kicker: 'FEELESS · FUSE RECEIPT', title: r.name || 'Fuse card', big: pc(r.pnlPct),
          lines: [r.legs.map(l => `$${l.symbol}`).join(' · ').slice(0, 60), `in ${m$(r.costUsd)} → out ${m$(r.realizedUsd || r.valueUsd)}`, `fees ${m$((r.feesUsd || 0) + (r.netUsd || 0))} (shown apart)`], footer: 'feeless · fuse 🧬' }} />
          <a className="m-btn" target="_blank" rel="noopener noreferrer" href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(`My FEELESS ⚛️ Fuse card ${r.name || ''}: ${pc(r.pnlPct)} (${r.legs.map(l => '$' + l.symbol).join(' ')})`)}&url=${encodeURIComponent(`${window.location.origin}/terminal/profile/${address}`)}`}>𝕏 Post</a></div>
      </div></details>)}</div></section>;
}

// ---- Profile top › 🃏 Trader card: the wallet's Fuse record in one strip — score, season medals, battle W/L/D, FeeCat wins,
// held cards P&L — plus a Share GIF and a Post-to-X link. Every number comes from /fuses/score (FEELESS's own records).
// ⚔ Profile: this wallet's cards in Arena battles — live (their side highlighted, tug bar) + recent results + record.
export function MyBattles({ address }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = () => address && fetch(apiUrl(`/api/reputation/fuses/battles/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => { alive = false; clearInterval(t); }; }, [address]);
  if (!d || (!d.live.length && !d.past.length)) return null;
  return <section className="wp-card fp-mybattles" data-testid="my-battles"><header className="m-row"><span className="m-label">⚔ MY CARD BATTLES</span>
    <small className="m-dim">{d.record.w}W {d.record.l}L {d.record.d}D · bigger move since the bell wins</small><a className="m-btn" href="/terminal/fuse?tab=arena">Arena →</a></header>
    {d.live.map((p, i) => { const me = p[p.mine]; const them = p[p.mine === 'a' ? 'b' : 'a']; const lead = (me.now || 0) - (them.now || 0);
      return <div key={me.key + them.key} className={`fp-mb-live ${lead > 0.05 ? 'is-up' : lead < -0.05 ? 'is-down' : ''}`} style={{ '--i': i }} data-testid={`mb-live-${i}`}>
        <b>{me.emoji || '🃏'} {me.name}</b><em className={`m-num fl-tick ${(me.now || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={me.now}>{pc(me.now)}</em><span className="bf-vs">VS</span>
        <em className={`m-num ${(them.now || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(them.now)}</em><b>{them.emoji} {them.name}</b>
        <i className="bf-tug"><i style={{ transform: `scaleX(${Math.max(0.08, Math.min(0.92, 0.5 + lead / 20))})` }} /></i></div>; })}
    {d.past.length > 0 && <div className="bf-log">{d.past.slice(0, 8).map(r => <small key={r.at + r.a} className={r.won ? 'is-won' : r.draw ? '' : 'is-lost'}>{r.draw ? '🤝' : r.won ? '🏆' : '✕'} {r.mine === 'a' ? r.a : r.b} vs {r.mine === 'a' ? r.b : r.a} <em>{pc(r.mine === 'a' ? r.aMove : r.bMove)} vs {pc(r.mine === 'a' ? r.bMove : r.aMove)}</em></small>)}</div>}
  </section>;
}

// ⚡ Fuse from anywhere (profile / activity): the trader Lab in a centered pop-up over a blurred page. Esc / outside closes.
export function FusePopup({ onClose }) {
  const [picks, setPicks] = useState([]);
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); document.body.classList.add('ce-open');
    return () => { window.removeEventListener('keydown', k); document.body.classList.remove('ce-open'); }; }, [onClose]);
  return createPortal(<div className="ce-shade is-pop" role="presentation" onClick={onClose} data-testid="fuse-popup">
    <aside className="ce is-pop m-live fp-popup" role="dialog" aria-modal="true" aria-label="Fuse a card" onClick={e => e.stopPropagation()}>
      <header><span className="m-label">⚡ FUSE A CARD</span><h3>Pick pools + 1–3 runners, one approval.</h3><button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <FuseLab runnerPicks={picks} onRunnerPicks={setPicks} /></aside></div>, document.body);
}

export function TraderCard({ address }) {
  const [s, setS] = useState(null);
  useEffect(() => { let alive = true; if (address) fetch(apiUrl(`/api/reputation/fuses/score/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setS(x)).catch(() => {}); return () => { alive = false; }; }, [address]);
  if (!s?.cards || !s.trader) return null;
  const t = s.trader; const b = t.battles || {}; const m = t.medals || {};
  const medals = [['🥇', m['1']], ['🥈', m['2']], ['🥉', m['3']]].filter(([, n]) => n);
  const url = `${window.location.origin}/terminal/profile/${address}`;
  const lines = [`Fuse score ${s.score}/100 · ${s.cards} cards`, `⚔ ${b.w || 0}W ${b.l || 0}L ${b.d || 0}D · 🐱 beat FeeCat ${t.catWins}×`, medals.length ? `Season medals ${medals.map(([e, n]) => `${e}×${n}`).join(' ')}` : `Best card ${t.bestPct >= 0 ? '+' : ''}${t.bestPct}%`];
  const xText = encodeURIComponent(`My FEELESS ⚛️ Fuse record: score ${s.score} · ${b.w || 0}-${b.l || 0} in Arena battles · best card ${t.bestPct >= 0 ? '+' : ''}${t.bestPct}%`);
  return <section className="wp-card fp-trader" data-testid="trader-card">
    <div className="fp-trader-score" style={{ '--deg': `${Math.max(0, Math.min(100, s.score)) * 3.6}deg` }} data-tip={`Performance ${s.perf}/75 + reputation ${s.rep}/25`}><span><b className="m-num">{s.score}</b><small>FUSE</small></span></div>
    <div className="fp-trader-stats">
      <div data-tip="Crowned in a weekly Fuse season (top 3)"><small>SEASON MEDALS</small><b>{medals.length ? medals.map(([e, n]) => <span key={e}>{e}<em>×{n}</em></span>) : <em className="m-dim">none yet</em>}</b></div>
      <div data-tip="Arena battles: the card that moved more since the bell wins"><small>BATTLES</small><b className="m-num">{b.w || 0}<i>W</i> {b.l || 0}<i>L</i> {b.d || 0}<i>D</i></b></div>
      <div data-tip="Weeks a card of theirs beat FeeCat's average trade"><small>🐱 FEECAT WINS</small><b className="m-num">{t.catWins}</b></div>
      <div data-tip="Cards they hold right now, live P&L"><small>HELD CARDS</small><b className={`m-num ${t.heldPnlUsd >= 0 ? 'm-pos' : 'm-neg'}`}>{t.held} · {t.heldPnlUsd >= 0 ? '+' : '−'}${Math.abs(t.heldPnlUsd).toFixed(2)}</b></div>
      <div data-tip="Other traders who copied one of their cards"><small>COPIED</small><b className="m-num">{t.copies}×</b></div>
    </div>
    <div className="fp-trader-share"><ShareGifButton className="m-btn" label="🎞 Share card" card={{ mascot: 'feecat', tone: t.heldPnlUsd >= 0 ? 'up' : 'down', kicker: 'FEELESS · FUSE TRADER', title: `Fuse score ${s.score}`, big: `${b.w || 0}-${b.l || 0}`, lines, footer: 'feeless · fuse 🧬' }} />
      <a className="m-btn" href={`https://x.com/intent/post?text=${xText}&url=${encodeURIComponent(url)}`} target="_blank" rel="noopener noreferrer" data-testid="trader-x">𝕏 Post</a></div>
  </section>;
}
