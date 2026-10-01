import React, { lazy, Suspense, useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ShareGifButton } from './ShareGif';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { readChatSession } from '../lib/chatSession';
import { unfuseOrders, rebalanceOrders, SOL_MINT } from '../lib/fuseGo';
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

// Fuse 🧬 — the whole Fuse product in one tab: Lab (build + featured) · Runners (pick ≤3 fresh coins) · Arena (proof)
// · My cards (live cards + every action). Runner picks and "Load" carry across tabs. Every money action is a normal
// wallet-signed FuseGo approval; the server re-checks every signature before anything counts.
// 🧬 A real 3D double helix (CSS 3D, transform-only): 10 base-pair rungs, each turning on its own phase so the strands spiral.
export function DnaHelix({ rungs = 10 }) {
  return <span className="dna3d" aria-hidden="true" data-testid="dna3d">{Array.from({ length: rungs }, (_, i) => <i key={i} style={{ '--i': i }}><b /><b /></i>)}</span>;
}

// One fun line per tab, so a first-timer knows what each one is for in 5 seconds.
export const TAB_TIPS = {
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

export const FUSE_TABS = [['lab', '🧪 Lab'], ['runners', '🏃 Runners'], ['arena', '🏟 Arena'], ['cards', '🃏 My cards']];
const m$ = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0) >= 1e3 ? `${(Math.abs(v) / 1e3).toFixed(1)}K` : Math.abs(v || 0).toFixed(2)}`;
const pc = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;
const MAX_RUNNERS = 3;
const post = (path, body) => fetch(apiUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  .then(async r => { const x = await r.json().catch(() => ({})); if (!r.ok) throw new Error(x.detail || 'Request failed'); return x; });
const readTab = () => { const t = new URLSearchParams(window.location.search).get('tab'); return FUSE_TABS.some(([k]) => k === t) ? t : 'lab'; };

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
      <div className="m-seg fp-tabs" role="tablist" aria-label="Fuse">{FUSE_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} data-testid={`fuse-tab-${k}`} onClick={() => go(k)}>{l}{k === 'runners' && runnerPicks.length ? ` · ${runnerPicks.length}` : ''}</button>)}</div></header>
    <p className="fp-tabtip" key={`tip-${tab}`} data-testid="fp-tabtip">{TAB_TIPS[tab]}</p>
    <div className="fp-body" key={tab}>
      {tab === 'lab' && <div className="fz-split-view fp-lab"><FuseLab runnerPicks={runnerPicks} onRunnerPicks={setRunnerPicks} incoming={incoming} limits={limits} />
        <aside className="fp-right"><FeaturedFuses onLoad={f => setIncoming({ legs: f.legs, sol: 0, n: Date.now() })} /><FuseSide /></aside></div>}
      {tab === 'runners' && <RunnerPicker picks={runnerPicks} onPicks={setRunnerPicks} onDone={() => go('lab')} />}
      {tab === 'arena' && <ArenaBoard onPicks={list => { setRunnerPicks(list); go('lab'); }} onLoad={(legs, from) => { const run = legs.filter(l => l.runner); if (run.length) setRunnerPicks(run.slice(0, MAX_RUNNERS).map(l => ({ mint: l.baseAddress, symbol: l.symbol, logo: l.logo, pairAddress: l.pairAddress, lane: l.lane || 'runner' })));
        setIncoming({ legs: legs.filter(l => !l.runner).sort((x, y) => (y.weight || 0) - (x.weight || 0)), sol: 0, n: Date.now(), ...(from || {}) }); go('lab'); }} />}
      {tab === 'cards' && <MyCards addr={addr} />}
    </div>
  </section>;
}

// ---- Lab › Featured (Cmd Ctr marks Fuses "Featured in Fuse Lab") ----------------------------------------------------
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
const SRC_ICON = { bond: '🔔', arena: '🏟', lit: '🔥', pump: '🚀', snipers: '🎯', creator: '📣' };
export const filterBySource = (rows, src) => (src === 'all' ? rows : rows.filter(r => r.sources.some(s => s.kind === src)));

export function RunnerPicker({ picks, onPicks, onDone }) {
  const [d, setD] = useState(null); const [src, setSrc] = useState('all');
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/runners/discover')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 20000); return () => { alive = false; clearInterval(t); }; }, []);
  const live = useLivePrices((d?.runners || []).map(x => x.pairAddress));
  if (!d) return <div className="fp-disc is-loading" data-testid="runner-picker"><div className="fp-scan" /><span className="m-dim">Scanning launchpads, the arena, the radar and the callers…</span></div>;
  const rows = filterBySource(d.runners || [], src);
  return <section className="fp-disc" data-testid="runner-picker">
    <header className="fp-disc-head m-card m-live"><div><span className="m-label">🏃 RUNNER DISCOVERY · LIVE</span><h2>Good runners, found for you.</h2>
      <p className="m-dim">Every coin here passed every gate right now ({d.gates.slice(0, 3).join(' · ')}…). The more sources that like it, the higher it sits.</p></div>
      <div className="rn-clock"><small>NEXT ROUND</small><Countdown at={d.nextRoundAt} /></div></header>
    <div className="m-seg fp-src" role="tablist" aria-label="Source">{[['all', '✨ All', (d.runners || []).length], ...Object.entries(d.sources).map(([k, l]) => [k, l, d.counts[k] || 0])].map(([k, l, n]) =>
      <button key={k} type="button" role="tab" aria-selected={src === k} className={src === k ? 'active' : ''} onClick={() => setSrc(k)} data-testid={`src-${k}`}>{l} <em>{n}</em></button>)}</div>
    {(d.swaps || []).length > 0 && <div className="fp-swaps" aria-label="Auto-swaps">{d.swaps.slice().reverse().map(s => <span key={s.at} className="fp-swap">🔁 ${s.out.symbol} → ${s.in.symbol} <small>{s.why[0]}</small></span>)}</div>}
    {!rows.length && <p className="m-dim fp-none">Nothing from this source passes every gate right now — that's the gates working. Next scan in seconds.</p>}
    {rows.length < 6 && (d.watching || []).length > 0 && <div className="fp-watch" data-testid="fp-watching"><span className="m-label">👀 WATCHING · FAILED A GATE (NOT ADDABLE)</span>
      <div className="fp-watch-row">{d.watching.map((w, i) => <span key={w.mint} className="fp-wchip" style={{ '--i': i }} data-tip={(w.gates || []).join(' · ')}>
        <span className="fp-ava sm">{w.logo ? <img src={w.logo} alt="" loading="lazy" /> : '👀'}</span><b>${w.symbol}</b><small>{(w.gates || [])[0]}</small></span>)}</div></div>}
    <div className="fp-rgrid">{rows.map((r, i) => { const on = picks.some(p => p.mint === r.mint); const full = !on && picks.length >= MAX_RUNNERS; const hot = r.sources.length >= 2;
      return <article key={r.mint} className={`fp-runner ${on ? 'is-on' : ''} ${hot ? 'is-hot' : ''}`} style={{ '--i': Math.min(i, 14) }} data-testid={`runner-${r.mint}`}>
        {hot && <span className="fp-hotband">{r.sources.length} sources</span>}
        <div className="fp-rtop"><span className="fp-ava">{r.logo ? <img src={r.logo} alt="" loading="lazy" /> : '🏃'}</span><div><b>${r.symbol}</b><small>{r.lane || 'runner'} lane · score {Math.round(r.score || 0)}</small></div>
          {(() => { const lv = live.get(r.pairAddress); const mv = lv ? lv.m5 : r.chg1h; return <span className={`m-num fp-move fl-tick ${(mv || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={`${(mv || 0).toFixed(1)}`} data-tip={lv ? `Live · 5m · $${lv.price}` : 'Last hour'}>{pc(mv)}<small>{lv ? '5m' : '1h'}</small></span>; })()}</div>
        <i className="fp-score"><i style={{ transform: `scaleX(${Math.min(1, (r.score || 0) / 100)})` }} /></i>
        {(r.bond || []).length > 0 && <BondMeter checks={r.bond} />}
        <div className="fp-srcs">{r.sources.map(s => <span key={s.kind} className={`fp-chip src-${s.kind}`} data-tip={s.detail}>{SRC_ICON[s.kind]} {s.label.replace(/^\S+\s/, '')}</span>)}</div>
        <div className="m-row fp-rstats"><span>MC {m$(r.mcap)}</span><span>{Math.round(r.buyShare || 0)}% buys</span><span>{m$(r.vol1h)} 1h vol</span></div>
        <button type="button" className={`m-btn wide ${on ? 'primary' : ''}`} disabled={full} onClick={() => onPicks(togglePick(picks, r))} data-testid={`runner-add-${r.mint}`}>{on ? '✓ On your card' : full ? 'Card full (3)' : '+ Add to card'}</button>
      </article>; })}</div>
    {picks.length > 0 && picks.length < MAX_RUNNERS && <div className="fp-dock" data-testid="fp-dock"><span>{picks.map(p => `$${p.symbol}`).join(' · ')} <small className="m-dim">· {MAX_RUNNERS - picks.length} more fills the card</small></span><button type="button" className="m-btn primary m-go" onClick={onDone} data-testid="runners-to-lab">Build card with {picks.length} →</button></div>}
    {picks.length >= MAX_RUNNERS && <RunnerCardFull picks={picks} onDone={onDone} />}
  </section>;
}

// A full runner card looks exactly like a prebuilt card (FuseCard: tilt, ⟲ money-math back), then goes to the Lab to fuse in.
export const runnerLegs = picks => picks.map(p => ({ chainId: 'solana', pairAddress: p.pairAddress || p.mint, symbol: p.symbol, baseAddress: p.mint, logo: p.logo,
  weight: Math.round(10000 / picks.length) / 100, change24h: p.chg1h || 0, liquidityUsd: p.liq || 0 }));
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

// 🔔 Bond run meter: the 6 boxes a pre-bond coin must tick (Cmd Ctr tunes them) — they light up one by one as it charges.
export function BondMeter({ checks }) {
  const n = checks.filter(c => c.ok).length; const full = n === checks.length;
  return <div className={`bond-meter ${full ? 'is-full' : ''}`} data-testid="bond-meter" data-tip={checks.map(c => `${c.ok ? '✓' : '·'} ${c.label}`).join('\n')}>
    <small>{full ? '🔔 BOND RUN' : `bond ${n}/${checks.length}`}</small>{checks.map((c, i) => <i key={c.id} className={c.ok ? 'on' : ''} style={{ '--i': i }} />)}</div>;
}

// ---- Arena: the stage. Cmd Ctr mega cards + runner cards that lit after their rounds, each wrapped in effects driven by
// its real activity (server fuse_hq.activity → hard-coded tier: calm / warm / hot / blazing). Then the Runners show
// (RunnersPanel: proof ring, countdown, lanes, round card, live board, last rounds) and the strategies board.
export const TIER_FX = { calm: { aura: 'aurora', embers: 3 }, warm: { aura: 'sparkle', embers: 6 }, hot: { aura: 'fire', embers: 10 }, blazing: { aura: 'lightning', embers: 16 } };
export const stageTier = cards => (cards || []).reduce((top, c) => (['calm', 'warm', 'hot', 'blazing'].indexOf(c.activity?.tier) > ['calm', 'warm', 'hot', 'blazing'].indexOf(top) ? c.activity.tier : top), 'calm');

export function ArenaBoard({ onPicks, onLoad }) {
  const [a, setA] = useState(null);
  const [chat, setChat] = useState(null);
  const [replay, setReplay] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/arena')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setA(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => { alive = false; clearInterval(t); }; }, []);
  const mega = a?.mega || [];
  const top = stageTier(mega);
  return <section className={`fp-arena ar-tier-${top}`} data-testid="fuse-arena">
    <div className="ar-sky" aria-hidden="true">{Array.from({ length: TIER_FX[top].embers + 6 }, (_, i) => <i key={i} style={{ '--i': i }} />)}</div>
    <header className="ar-head m-card m-live"><span className="m-label">🏟 ARENA STAGE · LIVE</span><h2>Cards that made it.</h2>
      <p className="m-dim">Cmd Ctr mega cards, runner cards that lit after their rounds, and every trader's open card until it's withdrawn — cards up big take the top tier. The more real activity a card has — FEELESS buys, buyers, $ flowing through its coins, how far it moved — the hotter it burns.</p>
      <div className="ar-legend">{Object.keys(TIER_FX).map(k => <span key={k} className={`ar-chip t-${k}`}>{k}</span>)}</div></header>
    {!a ? <div className="ar-stage">{[0, 1, 2].map(i => <div key={i} className="frail-ghost" />)}</div>
      : !mega.length ? <p className="m-dim ar-none">No card on stage yet — a runner round that lights up lands here, and Cmd Ctr can stage its mega cards.</p>
      : <div className="ar-stage" data-testid="arena-stage">{mega.map((c, i) => <MegaCard key={`${c.kind}-${c.id}`} c={c} i={i} onPicks={onPicks} onLoad={onLoad} chatOpen={chat?.id === c.id} onChat={() => setChat(x => (x?.id === c.id ? null : c))}
        onReplay={() => setReplay(x => (x?.id === c.id ? null : c))} />)}</div>}
    {a?.battles?.pairs?.length > 0 && <Battlefield b={a.battles} />}
    {replay && <CardReplay c={replay} onClose={() => setReplay(null)} />}
    {chat && <CardChat c={chat} onClose={() => setChat(null)} />}
    <FuseSeason />
    <RunnersPanel />
    {a && <div className="m-card"><span className="m-label">STRATEGIES · WE RUN $5 FOR 24H</span><p className="m-dim">{a.outlook?.note || (a.outlook?.style ? `${a.outlook.style}: ${pc(a.outlook.avgPct)} avg over ${a.outlook.runs} runs, ${a.outlook.winRate}% won.` : 'Not enough settled runs yet.')}</p>
      <table className="vd-table"><thead><tr><th>Strategy</th><th>Runs</th><th>Avg</th><th>Won</th><th /></tr></thead><tbody>
      {(a.board || []).map(b => <tr key={b.style}><td><b>{b.style}</b>{a.bestStyle === b.style ? ' 👑' : ''}</td><td>{b.runs}</td><td className={(b.avgPct || 0) >= 0 ? 'm-pos' : 'm-neg'}>{pc(b.avgPct || 0)}</td><td>{Math.round(b.winRate ?? 0)}%</td><td>{b.runs >= a.minSettled && b.avgPct > 0 ? <span className="m-chip ok">proven</span> : <span className="m-chip">needs {a.minSettled}+</span>}</td></tr>)}</tbody></table></div>}
    <small className="m-dim">Effects show activity, never a promise. Our $5 runs use live prices after each round; fresh coins can go to zero in minutes.</small>
  </section>;
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
        <span className="fs-who"><b>{b.name || 'Fuse card'}{b.beatsCat && <em className="fs-beat" data-tip="Up more than FeeCat's average trade this week">🐱 beat</em>}</b><small>{b.handle}{b.closed ? ' · closed' : ''}</small></span>
        {b.streak?.tier ? <StreakBadge s={b.streak} /> : <span />}
        <i className="fs-bar"><i className={b.pnlPct >= 0 ? 'up' : 'down'} style={{ transform: `scaleX(${Math.max(0.03, Math.abs(b.pnlPct || 0) / top)})` }} /></i>
        <b className={`m-num ${b.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pc(b.pnlPct)}</b></li>)}</ol>}
    {s.past?.length > 0 && <div className="fs-past"><small className="m-label">PAST CHAMPIONS</small>{s.past.map(w => <span key={w.week} className="fs-champ" data-tip={w.top.map(t => `${MEDAL[t.rank]} ${t.handle || ''} ${t.name || ''} ${pc(t.pnlPct)}`).join('\n')}>
      <small>{wk(w.week)}</small>{MEDAL[1]} {w.top[0]?.handle || `${(w.top[0]?.wallet || '').slice(0, 4)}…`} <b className="m-pos">{pc(w.top[0]?.pnlPct)}</b></span>)}</div>}
  </section>;
}

// ⚔ Battlefield: stage cards fight in pairs (hot vs hot) — bigger move since the bell wins. Tug-of-war bar = who's ahead.
export function Battlefield({ b }) {
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const t = setInterval(() => setNow(Date.now() / 1000), 15000); return () => clearInterval(t); }, []);
  return <section className="m-card m-live bf" data-testid="battlefield"><header className="m-row"><span className="m-label">⚔ BATTLEFIELD · LIVE</span>
    <small className="m-dim">bigger move since the bell wins · next bell in {left((b.endsAt || now) - now)}</small></header>
    <div className="bf-pairs">{b.pairs.map((p, i) => { const d = p.a.now - p.b.now; const share = Math.max(0.08, Math.min(0.92, 0.5 + d / 20));
      return <div key={p.a.key + p.b.key} className={`bf-pair ${d > 0.05 ? 'a-lead' : d < -0.05 ? 'b-lead' : 'even'}`} style={{ '--i': i }} data-testid={`battle-${i}`}>
        <span className="bf-side a"><b>{p.a.emoji} {p.a.name}</b><em className={`m-num fl-tick ${p.a.now >= 0 ? 'm-pos' : 'm-neg'}`} key={p.a.now}>{pc(p.a.now)}</em></span>
        <span className="bf-vs" aria-hidden="true">VS</span>
        <span className="bf-side b"><b>{p.b.emoji} {p.b.name}</b><em className={`m-num fl-tick ${p.b.now >= 0 ? 'm-pos' : 'm-neg'}`} key={p.b.now}>{pc(p.b.now)}</em></span>
        <i className="bf-tug"><i style={{ transform: `scaleX(${share})` }} /></i></div>; })}</div>
    {b.log?.length > 0 && <div className="bf-log">{b.log.slice(0, 6).map(l => <small key={l.at + l.a}>{l.draw ? `🤝 ${l.a} = ${l.b}` : `🏆 ${l.winner} beat ${l.winner === l.a ? l.b : l.a}`} <em>{pc(l.aMove)} vs {pc(l.bMove)}</em></small>)}</div>}
  </section>;
}

export function MegaCard({ c, i, onPicks, onLoad, onChat, chatOpen, onReplay }) {
  const fx = TIER_FX[c.activity?.tier] || TIER_FX.calm;
  const live = useLivePrices((c.legs || []).map(l => l.pairAddress));
  const lp = liveStagePct(c, live);
  const move = lp ?? (c.index || 100) - 100;
  const runners = c.kind === 'lit' || c.kind === 'round';
  const use = () => (runners ? onPicks?.(c.legs.slice(0, MAX_RUNNERS).map(l => ({ mint: l.baseAddress, symbol: l.symbol, logo: l.logo, pairAddress: l.pairAddress, lane: 'runner' })))
    : onLoad?.(c.legs, c.kind === 'user' ? { copyOf: c.id, owner: c.owner, copyPct: c.copyPct } : null));
  return <article className={`ar-card t-${c.activity?.tier || 'calm'}`} style={{ '--i': i, '--act': (c.activity?.score || 0) / 100 }} data-testid={`mega-${c.id}`}>
    <span className="ar-heat" aria-hidden="true" /><span className="ar-ring" aria-hidden="true" />
    <FuseCard c={{ pools: c.legs.map(l => l.pairAddress), fitness: c.activity?.score || 0, bornGen: c.legs.length, parts: { grade: c.grade || 'B', aprScore: 0, momentum24h: move, calm: '—', feeDragPct: 0, impactLegs: 0 }, legs: c.legs }}
      style={c.kind === 'lit' ? 'degen' : 'momentum'} rank={0} budget={20} aura={c.aura || fx.aura} />
    <div className="ar-embers" aria-hidden="true">{Array.from({ length: fx.embers }, (_, k) => <i key={k} style={{ '--i': k }} />)}</div>
    <div className="ar-meta"><b>{c.emoji} {c.name}</b>
      <span className="ar-act" data-tip="Activity: FEELESS buys + buyers (24h), $ flow through its coins, index move. Drives the effects."><small>ACT</small><i style={{ transform: `scaleX(${(c.activity?.score || 0) / 100})` }} /><em className="m-num">{c.activity?.score || 0}</em></span>
      {c.record_wl && <span className="ar-wl" data-tip="Arena battle record (wins – losses – draws)" data-testid={`wl-${c.id}`}>⚔ {c.record_wl.w}–{c.record_wl.l}{c.record_wl.d ? `–${c.record_wl.d}` : ''}</span>}
      {(c.streak?.tier || c.compound?.tier || c.copies > 0) && <span className="ar-badges">{c.streak?.tier && <StreakBadge s={c.streak} />}{c.compound?.tier && <CompoundBadge s={c.compound} />}{c.copies > 0 && <span className="ar-copies" data-tip="Traders who fused this card too">⚡ {c.copies} {c.copies === 1 ? 'copy' : 'copies'}</span>}</span>}
      <small className="m-dim">{c.kind === 'auto' ? '⚔ dealt by the arena this round · traders load 3 + 3' : c.kind === 'feecat' ? `🐱 sim book · ${c.record?.winRate ?? '—'}% wins · ${(c.record?.realizedSol ?? 0) >= 0 ? '+' : ''}${c.record?.realizedSol ?? 0} SOL realized${c.record?.lives != null ? ` · ❤${c.record.lives}` : ''}` : c.kind === 'lit' ? '🔥 lit runner card' : c.kind === 'round' ? '⏳ this round · proving' : c.kind === 'user' ? `🃏 ${c.owner} · ${c.mode === 'swap' ? '⇄ swaps weak legs' : '🔒 holds together'}` : `⚛️ Cmd Ctr · ${c.legs.length} legs`} · <span className={`fl-tick ${move >= 0 ? 'm-pos' : 'm-neg'}`} key={move.toFixed(1)} data-tip={lp != null ? 'Live (10s prices)' : 'Last server update'}>{pc(move)}{lp != null && <i className="fl-livedot" />}</span>{c.buyers ? ` · ${c.buyers} buyers` : ''}</small>
      <span className="ar-acts">{onReplay && <button type="button" className="m-btn" onClick={onReplay} data-tip="Replay the last 24h of this card" data-testid={`mega-replay-${c.id}`}>▶</button>}{c.chat && <button type="button" className={`m-btn ${chatOpen ? 'primary' : ''}`} onClick={onChat} aria-pressed={chatOpen} data-tip="This card's chat" data-testid={`mega-chat-${c.id}`}>💬</button>}
      <button type="button" className="m-btn primary m-go" onClick={use} data-testid={`mega-use-${c.id}`}>{runners ? 'Use runners →' : c.kind === 'user' ? '⚡ Fuse this too' : c.legs.length > 3 ? 'Load top 3 →' : 'Load →'}</button></span></div>
  </article>;
}

// ---- My cards: live cards + every action ------------------------------------------------------------------------------
const balancesOf = async (addr, legs) => Object.fromEntries(await Promise.all(legs.filter(l => l.mint && l.soldUsd == null).map(l => fetch(apiUrl(`/api/reputation/balance/${addr}/${l.mint}`)).then(x => (x.ok ? x.json() : null)).catch(() => null).then(b => [l.mint, b]))));
const solPrice = () => fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL_MINT}`).then(r => r.json()).then(d => Number(d?.[SOL_MINT]?.usdPrice) || 0).catch(() => 0);
export const collectSplit = (pct, legs) => (legs || []).filter(l => l.soldUsd == null).map(l => ({ ...l, pct }));

export function MyCards({ addr }) {
  const [d, setD] = useState(null);
  const [act, setAct] = useState(null);   // {id, kind, ...} — one open action at a time
  const load = useCallback(() => addr && fetch(apiUrl(`/api/reputation/fuses/pnl/${addr}`)).then(r => (r.ok ? r.json() : null)).then(setD).catch(() => {}), [addr]);
  useEffect(() => { load(); const t = setInterval(() => !document.hidden && load(), 30000); window.addEventListener('feeless:fuse-pnl', load);
    return () => { clearInterval(t); window.removeEventListener('feeless:fuse-pnl', load); }; }, [load]);
  const ses = () => { const s = addr && readChatSession(addr); if (!s) toast.error('Open chat once to sign in your wallet first.'); return s; };
  const refresh = () => setTimeout(() => window.dispatchEvent(new Event('feeless:fuse-pnl')), 1200);
  const setMode = async (r, mode) => { const s = ses(); if (!s || (r.mode || 'hold') === mode) return;
    try { await post('/api/reputation/fuses/mode', { address: addr, session: s, id: r.id, mode }); toast.success(mode === 'swap' ? 'Swap mode: weak legs get a one-tap swap alert' : 'Hold mode: the card stays together'); load(); } catch (e) { toast.error(e.message); } };
  const open = useCallback(async (r, kind, extra = {}) => {
    if (act?.id === r.id && act.kind === kind && !extra.pct) { setAct(null); return; }
    if (kind === 'withdraw' || kind === 'take') {
      const bal = await balancesOf(addr, r.legs); const pct = extra.pct || (kind === 'withdraw' ? 100 : 50);
      setAct({ id: r.id, kind, pct, legs: (extra.legs || r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)), bal });
    } else if (kind === 'rebalance' || kind === 'switch') {
      const [bal, solUsd] = await Promise.all([balancesOf(addr, r.legs), solPrice()]);
      setAct({ id: r.id, kind, bal, solUsd, ...extra });
    } else setAct({ id: r.id, kind, ...extra });
  }, [act, addr]);
  // Alert links: ?collect=<id>&pct= (💸 auto-collect), ?rebalance=<id>, ?unfuse=<id>
  useEffect(() => { if (!d?.rows || act) return; const q = new URLSearchParams(window.location.search); const find = id => id && d.rows.find(x => x.id === id && !x.closed);
    const c = find(q.get('collect')); if (c) { open(c, 'take', { pct: Number(q.get('pct')) || 33, ...(q.get('legs') ? { legs: q.get('legs').split(',') } : {}) }); return; }
    const rb = find(q.get('rebalance')); if (rb) { open(rb, 'rebalance'); return; }
    const sw = find(q.get('switch')); if (sw) { open(sw, 'switch', { from: q.get('out'), toMint: q.get('in'), toSymbol: q.get('sym') || 'NEW', toPair: q.get('pair') || undefined, toRole: 'runner' }); return; }
    const u = find(q.get('unfuse')); if (u) open(u, 'withdraw'); }, [d]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!addr) return <div className="m-card fp-empty"><b>Connect your Solana wallet to see your Fuse cards.</b></div>;
  if (!d) return <div className="m-card"><span className="loader" /> Loading your cards…</div>;
  const openRows = (d.rows || []).filter(r => !r.closed);
  return <MyCardsBody d={d} openRows={openRows} act={act} setAct={setAct} open={open} setMode={setMode} addr={addr} ses={ses} refresh={refresh} />;
}

function MyCardsBody({ d, openRows, act, setAct, open, setMode, addr, ses, refresh }) {
  const live = useLivePrices(openRows.flatMap(r => r.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress)));
  const held = openRows.length ? liveBook(openRows, live) : { pnlUsd: d.held?.pnlUsd, pnlPct: d.held?.pnlPct, value: d.held?.valueUsd };
  return <section className="fp-cards" data-testid="my-cards">
    <div className="m-row fp-book"><span className="m-label">CARDS YOU HOLD</span><b className={`m-num fl-tick ${(held.pnlUsd || 0) >= 0 ? 'm-pos' : 'm-neg'}`} key={(held.pnlUsd || 0).toFixed(2)} data-testid="held-pnl">{m$(held.pnlUsd)} <small>{pc(held.pnlPct)}</small><i className="fl-livedot" /></b>
      <small className="m-dim">{m$(held.value)} now · {openRows.length} open · all-time {m$(d.pnlUsd)}</small>{d.feebackUsd > 0 && <span className="m-chip ok" data-tip="Fuse Fee-Back: your unlocked share of the fees you paid on cards">🎁 {m$(d.feebackUsd)} Fee-Back</span>}</div>
    {!openRows.length && <div className="m-card fp-empty"><b>No open cards.</b><small className="m-dim">Build one in the Lab — 3 pools + up to 3 runners.</small></div>}
    <div className="fp-cgrid">{openRows.map(r => <div key={r.id} className={`fp-cell ${r.onArena ? 'is-arena' : ''}`}><LiveFuseCard r={r} aura={r.onArena ? 'fire' : ''} />
      <div className="m-seg fp-mode" role="radiogroup" aria-label="Card mode">{[['hold', '🔒 Hold together', 'The card stays as you built it'], ['swap', '⇄ Swap weak legs', `When a leg fails a gate or drops ${d.rules?.swapDropPct ?? 25}%, we alert you with the best gated runner pre-filled — one approval`]].map(([k, l, tip]) =>
        <button key={k} type="button" role="radio" aria-checked={(r.mode || 'hold') === k} className={(r.mode || 'hold') === k ? 'active' : ''} data-tip={tip} onClick={() => setMode(r, k)} data-testid={`mode-${k}-${r.id}`}>{l}</button>)}</div>
      {r.beatCat?.length > 0 && <span className="fs-crown r-cat" data-tip="Weeks this card beat FeeCat's average trade" data-testid={`beatcat-${r.id}`}>🐱 Beat FeeCat ×{r.beatCat.length}</span>}
      {r.seasonWin && <span className={`fs-crown r-${r.seasonWin.rank}`} data-tip={`Fuse season · week of ${wk(r.seasonWin.week)} — +Fee-Back boost on this card`} data-testid={`crown-${r.id}`}>{MEDAL[r.seasonWin.rank]} #{r.seasonWin.rank} · week of {wk(r.seasonWin.week)}</span>}
      {(r.streak?.tier || r.compound?.tier || r.copies > 0) && <span className="ar-badges">{r.streak?.tier && <StreakBadge s={r.streak} />}{r.compound?.tier && <CompoundBadge s={r.compound} />}{r.copies > 0 && <span className="ar-copies" data-tip="Traders who copied this card — you earn a share of their FEELESS fee">⚡ {r.copies} {r.copies === 1 ? 'copy' : 'copies'} · {m$(r.copyEarnedUsd)} earned</span>}</span>}
      {r.feeback && <small className={`fp-fb ${r.feeback.unlocked ? 'is-on' : ''}`} data-tip={`Fee-Back: ${r.feeback.pct}% of the $${(r.feeback.feesUsd || 0).toFixed(2)} fees you paid on this card${r.feeback.arena ? ' (incl. Arena bonus)' : ''}`}>🎁 {r.feeback.unlocked ? `${m$(r.feeback.usd)} back · ${r.feeback.pct}%` : 'Fee-Back'}{r.feeback.next ? ` · ${r.feeback.next}` : ''}</small>}
      <div className="fp-acts" role="toolbar" aria-label={`${r.name} actions`}>
        <button type="button" className="m-btn" data-tip="Sell part of chosen legs back to SOL (25 / 50 / 100%)" onClick={() => open(r, 'take')} data-testid={`act-take-${r.id}`}>💰 Take profit</button>
        <button type="button" className={`m-btn ${r.autoYield ? 'is-armed' : ''}`} data-tip="Auto-collect: alert + pre-filled Collect profit when the card is up +X% (sells only the gain). You approve once." onClick={() => open(r, 'yield', { at: r.autoYield?.at || d.rules?.yieldDefault || 50, levels: d.rules?.yieldLevels || [25, 50, 100, 200] })} data-testid={`act-yield-${r.id}`}>💸 {r.autoYield ? `Auto +${Math.round(r.autoYield.at)}%` : 'Auto-collect'}</button>
        <button type="button" className={`m-btn ${r.drift >= 5 ? 'is-warn' : ''}`} data-tip={`Back to the weights you bought (drift ${Math.round(r.drift || 0)} pts) — one approval`} onClick={() => open(r, 'rebalance')} data-testid={`act-rebalance-${r.id}`}>⚖ Rebalance</button>
        <button type="button" className="m-btn" data-tip="Sell one leg and buy a new pool or runner in one approval" onClick={() => open(r, 'switch')} data-testid={`act-switch-${r.id}`}>⇄ Switch</button>
        <button type="button" className={`m-btn ${r.guard && !r.guard.firedAt ? 'is-armed' : ''}`} data-tip="Take-profit / stop-loss / trailing on the whole card" onClick={() => open(r, 'limits', { tp: r.guard?.tp || 50, sl: r.guard?.sl || 20, trail: r.guard?.trail || '', legs: Object.fromEntries(Object.entries(r.legGuard || {}).map(([pa, g]) => [pa, { tp: g.tp ?? '', sl: g.sl ?? '' }])), onProfit: r.onProfit || 'collect' })} data-testid={`act-limits-${r.id}`}>🎯 Limits</button>
        <button type="button" className="m-btn" data-tip="Replay this card's last 24h" onClick={() => open(r, 'replay')} data-testid={`act-replay-${r.id}`}>▶ Replay</button>
        <span className="fp-legcharts" aria-label="Open each coin's chart (your trades marked)">{r.legs.filter(l => l.soldUsd == null).map(l => <button key={l.pairAddress} type="button" className="m-btn" data-tip={`${l.symbol}: open its chart — your confirmed buy is marked on the candles`} onClick={() => openWarRoom({ chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol } })} data-testid={`chart-${l.pairAddress}`}>📈 {l.symbol}</button>)}</span>
        <button type="button" className="m-btn danger" data-tip="Sell every leg back to SOL — one approval" onClick={() => open(r, 'withdraw')} data-testid={`act-withdraw-${r.id}`}>↩ Withdraw</button>
      </div>
      {act?.id === r.id && <ActionPanel r={r} act={act} setAct={setAct} addr={addr} ses={ses} refresh={refresh} />}
    </div>)}</div>
  </section>;
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
  return <section className="wp-card fp-receipts" data-testid="fuse-receipts"><h3>Fuse receipts</h3><ol>{d.receipts.map(r => <li key={r.id}>
    <b>{r.name}</b><small className="m-dim">{r.legs.map(l => l.symbol).join(' · ')} · {new Date((r.at || 0) * 1000).toLocaleDateString()} → {r.closedAt ? new Date(r.closedAt * 1000).toLocaleDateString() : 'open'}</small>
    <span className={r.pnlUsd >= 0 ? 'm-pos' : 'm-neg'}>{m$(r.pnlUsd)} ({pc(r.pnlPct)})</span><small className="m-dim">in {m$(r.costUsd)} · out {m$(r.realizedUsd || r.valueUsd)}</small></li>)}</ol></section>;
}

// ---- Profile top › 🃏 Trader card: the wallet's Fuse record in one strip — score, season medals, battle W/L/D, FeeCat wins,
// held cards P&L — plus a Share GIF and a Post-to-X link. Every number comes from /fuses/score (FEELESS's own records).
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
