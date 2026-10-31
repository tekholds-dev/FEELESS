import React, { useEffect, useMemo, useRef, useState } from 'react';
import '../../styles/agentDemo.css';

// 🛸 AGENT DEMO (owner, 2026-10-29: "based on if trader or general picked show a demo — 2 trade chart windows; if general 2 demo browser windows
// for what they would do, with a demo live activity over both windows so users get the gist"). Drawn from scratch: SVG candles on a random walk
// with the germ floor + each brain's BUY / TRIM pins, or two cloud browsers typing their URL, scrolling, the cursor landing on the find. A DEMO
// strip says so on every window — nothing here is a real trade or a real page. One clock per demo, stopped off-screen and under reduced motion.

// pure: a seeded random walk of candles (tests feed a seed)
export function walk(seed = 1, n = 30, start = 100) {
  let s = seed * 9301 + 49297; const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const out = []; let c = start;
  for (let i = 0; i < n; i++) { const o = c; c = Math.max(20, o * (1 + (rnd() - 0.47) * 0.06)); out.push({ o, c, h: Math.max(o, c) * (1 + rnd() * 0.02), l: Math.min(o, c) * (1 - rnd() * 0.02) }); }
  return out;
}

function useClock(ms) {
  const ref = useRef(null); const [t, setT] = useState(0);
  useEffect(() => {
    const still = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (still) return undefined;
    let seen = true; let id = null;
    const run = () => { clearInterval(id); if (seen) id = setInterval(() => { if (!document.hidden) setT(x => x + 1); }, ms); };
    const io = typeof IntersectionObserver !== 'undefined' && ref.current ? new IntersectionObserver(([e]) => { seen = e.isIntersecting; run(); }) : null;
    if (io) io.observe(ref.current);
    run(); return () => { clearInterval(id); io?.disconnect(); };
  }, [ms]);
  return [ref, t];
}

// 📈 one drawn chart: candles roll in, the germ floor holds, the brain pins its calls. Also the empty-desk ghost (Fee's NO COIN YET panel).
export function DemoChart({ seed = 1, t = 0, who = 'A', sym = 'GERM', calls = true }) {
  const base = useMemo(() => walk(seed, 64), [seed]);
  const at = t % 34; const bars = base.slice(at, at + 30);
  const live = { ...bars[bars.length - 1] }; const wig = Math.sin(t * 1.7 + seed) * 0.012; live.c = live.c * (1 + wig); live.h = Math.max(live.h, live.c); live.l = Math.min(live.l, live.c);
  bars[bars.length - 1] = live;
  const hi = Math.max(...bars.map(b => b.h)); const lo = Math.min(...bars.map(b => b.l)); const y = v => 8 + (hi - v) / Math.max(1e-9, hi - lo) * 96;
  const floor = Math.min(...bars.slice(0, 20).map(b => b.l)); const w = 240 / bars.length;
  const buyI = 18; const trimI = 26; const showBuy = calls && at % 17 > 3; const showTrim = calls && at % 17 > 10;
  const pct = ((live.c / bars[buyI].c - 1) * 100);
  return <svg className="agd-chart" viewBox="0 0 240 120" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
    {[30, 60, 90].map(g => <line key={g} className="agd-grid" x1="0" x2="240" y1={g} y2={g} />)}
    <line className="agd-floor" x1="0" x2="240" y1={y(floor)} y2={y(floor)} /><text className="agd-floor-t" x="4" y={y(floor) - 3}>GERM FLOOR</text>
    {bars.map((b, i) => <g key={i} className={b.c >= b.o ? 'up' : 'dn'}><line x1={i * w + w / 2} x2={i * w + w / 2} y1={y(b.h)} y2={y(b.l)} />
      <rect x={i * w + w * 0.18} width={w * 0.64} y={y(Math.max(b.o, b.c))} height={Math.max(1.2, Math.abs(y(b.o) - y(b.c)))} rx="0.6" /></g>)}
    <line className="agd-last" x1="0" x2="240" y1={y(live.c)} y2={y(live.c)} />
    {showBuy ? <g className="agd-pin is-buy" transform={`translate(${buyI * w + w / 2} ${y(bars[buyI].l) + 8})`}><circle r="4.5" /><text y="12">{`${who} · BUY`}</text></g> : null}
    {showTrim ? <g className="agd-pin is-trim" transform={`translate(${trimI * w + w / 2} ${y(bars[trimI].h) - 8})`}><circle r="4.5" /><text y="-8">{`TRIM ${pct >= 0 ? '+' : ''}${pct.toFixed(0)}%`}</text></g> : null}
    <text className="agd-sym" x="236" y="14" textAnchor="end">{`$${sym}`}</text>
  </svg>;
}

// 🎥 the two minds' browsers play REAL recordings (owner 2026-10-30): scripts/record-agent-demo.py drives a headless Chromium on Wikipedia and saves
// each step (frame · URL · caption · where it clicked) to /agent-demo/frames.json — fetched once, shared by every demo on the page
let recP = null;
export function loadRecording() {
  if (!recP) recP = (typeof fetch === 'function' ? fetch('/agent-demo/frames.json').then(r => (r.ok ? r.json() : null)) : Promise.resolve(null)).catch(() => null);
  return recP;
}
function useRecording(want = true) {
  const [rec, setRec] = useState(null);
  useEffect(() => { if (!want) return undefined; let on = true; loadRecording().then(r => on && setRec(r)); return () => { on = false; }; }, [want]);
  return rec;
}
export const FRAME_TICKS = 4;   // a frame stays ~2.6s (the general demo ticks every 650ms)
function DemoBrowser({ frames, t, who, credit, label = 'MIND' }) {
  if (!frames?.length) return <div className="agd-browser"><span className="agd-url"><i aria-hidden="true">🔒</i><b>loading the recording…</b></span>
    <div className="agd-page"><i className="agd-sk w80" /><i className="agd-sk w60" /><i className="agd-sk w90" /></div></div>;
  const k = Math.floor(t / FRAME_TICKS) % frames.length; const sub = t % FRAME_TICKS; const f = frames[k];
  const typed = f.url.slice(0, sub ? f.url.length : Math.ceil(f.url.length / 3));
  return <div className="agd-browser is-rec">
    <span className="agd-url"><i aria-hidden="true">🔒</i><b>{typed}</b><u className="agd-caret" aria-hidden="true" /><em className="agd-rec">● REC</em></span>
    <div className="agd-screen">
      {frames.map((x, i) => <img key={x.src} src={x.src} alt="" className={i === k ? 'is-on' : ''} loading="lazy" draggable="false" />)}
      <span className="agd-track" style={{ transform: `translate(${f.cursor[0]}%, ${f.cursor[1]}%)` }} aria-hidden="true">
        <span className={`agd-click${sub === 1 ? ' is-on' : ''}`} key={k} /><svg viewBox="0 0 12 16"><path d="M0 0 L0 13 L3.5 10 L6 15.5 L8 14.6 L5.6 9.4 L10 9.4 Z" /></svg></span>
      <span className={`agd-done is-on at-${who === 'B' ? 'right' : 'left'}`} key={`c${k}`}>{label} {who} · {f.caption}</span>
      <span className="agd-step" aria-hidden="true">{frames.map((x, i) => <i key={x.src} className={i <= k ? 'on' : ''} />)}</span>
    </div>
    {credit ? <small className="agd-credit">{credit}</small> : null}
  </div>;
}

export const DEMO_FEED = {
  trading: ['🧠 A · scanning 412 fresh coins', '🧠 B · $GERM on its germ floor · buyers 71%', '🤝 A + B agree · BUY 0.05 SOL', '👛 sent from ITS wallet · inside your caps',
    '🛡 guard · skipped $RUGZ — 6 bundlers', '📈 $GERM +18% · TRIM half', '💵 banked · fees on the receipt, never in P&L'],
  general: ['⚡ you asked: what is Solana + how do prediction markets work?', '🧠 A · searches Wikipedia for Solana', '🧠 B · opens Prediction market', '✋ a sign-in? that window pauses for you',
    '🔗 A merges both halves · every source kept', '📝 one answer with links — nothing posted', '✅ done · $0.012 of your $0.10 cap'],
};

// 🧭 the two windows follow the mode you picked (owner 2026-10-30): one coin when they discuss / judge together, two coins when they take turns or
// battle; one question split in halves (plan) or two separate jobs with a handoff (jobs)
export const DEMO_MODE = {
  discuss: { same: true, sub: ['reads it first', 'challenges · final call'], line: '🧠 B · challenges A\'s read — agrees · BUY 0.05 SOL' },
  together: { same: true, sub: ['its own read', 'its own read'], line: '🤝 A + B both said BUY · 0.05 SOL' },
  turns: { sub: ['its turn', 'next turn'], line: '🧠 A\'s turn · BUY 0.05 SOL — B takes the next coin' },
  battle: { sub: ['its own record', 'its own record'], line: '⚔ A buys $GERM · B buys $NEON · each on its own record' },
  plan: { sub: ['half 1 of your ask', 'half 2 · checks A'] },
  jobs: { sub: ['job 1 · research', 'job 2 · uses A\'s handoff'], feed: ['⚡ two jobs: research Solana · write a thread on it', '🧠 A · researches Solana', '🧠 B · drafts the thread',
    '📦 A hands its notes + sources to B', '📝 B\'s thread cites A\'s sources', '👀 you review both before anything posts', '✅ both delivered · $0.014 of your $0.10 cap'] },
};
// 🖨 the free space beside the windows prints what each mind does, line by line (owner 2026-10-30) — A's lines left, B's right, shared ones both sides
export const printsFor = (feed, who) => feed.filter(l => !/(^|\s)[AB](\s·|'s|\s\+)/.test(l) || new RegExp(`(^|\\s)${who}(\\s·|'s|\\s\\+)`).test(l));
function Prints({ feed, who, k }) {
  const mine = printsFor(feed, who); const n = mine.length || 1;
  const rows = [5, 4, 3, 2, 1, 0].map(j => ({ id: k - j, text: mine[((k - j) % n + n) % n] })).filter(x => x.id >= 0 && x.text);
  return <ol className={`agd-print p-${who}`} aria-hidden="true">{rows.map((r, i) => <li key={r.id} className={i === rows.length - 1 ? 'is-now' : ''}><time>{String(Math.floor(r.id * 1.3 / 60)).padStart(2, '0')}:{String(Math.round(r.id * 1.3) % 60).padStart(2, '0')}</time>{r.text}</li>)}</ol>;
}
export function AgentDemo({ kind = 'trading', models = [], mode }) {
  const gen = kind === 'general'; const [ref, t] = useClock(gen ? 650 : 900);
  const rec = useRecording();
  const how = DEMO_MODE[mode] || DEMO_MODE[gen ? 'plan' : 'discuss']; const jobs = gen && mode === 'jobs';   // two jobs ⇒ two different recorded sites
  const feed = how.feed || (how.line ? DEMO_FEED.trading.map((l, j) => (j === 2 ? how.line : l)) : DEMO_FEED[gen ? 'general' : 'trading']); const k = Math.floor(t / 2);
  const lines = [0, 1, 2].map(j => ({ id: k - j, text: feed[((k - j) % feed.length + feed.length) % feed.length] })).filter(x => x.id >= 0).reverse();
  const name = i => models[i]?.name?.replace(/^[^:]+:\s*/, '') || (i ? 'second pick' : 'your pick');
  return <div className={`agd is-${gen ? 'general' : 'trading'}`} ref={ref} data-testid="agent-demo">
    <i className="agd-hex" aria-hidden="true" /><i className="agd-scan" aria-hidden="true" />
    <span className="agd-tag">◈ DEMO · {gen ? 'what its two minds do' : 'how its two brains trade'} · not real</span>
    <div className="agd-stage"><Prints feed={feed} who="A" k={k} />
    <div className="agd-wins">{[0, 1].map(i => <div key={i} className={`agd-win w${i}`} style={{ '--i': i }}>
      <span className="agd-bar is-go"><i /><i /><i /><b>{gen ? `MIND ${'AB'[i]}` : `BRAIN ${'AB'[i]}`}</b><small>{name(i)} · {how.sub[i]}</small><em className="agd-live">● LIVE</em></span>
      {gen ? <DemoBrowser frames={rec?.[(jobs ? 'cd' : 'ab')[i]] || rec?.['ab'[i]]} t={t + i * 2} who={'AB'[i]} credit={i ? (jobs ? rec?.jobsCredit : rec?.credit) : null} />
        : rec?.t?.length ? <DemoBrowser label="BRAIN" frames={rec[(i && !how.same && rec.u?.length) ? 'u' : 't']} t={t + (how.same ? 0 : i * 2)} who={'AB'[i]} credit={i ? rec.chartCredit : null} />
          : <DemoChart seed={i && !how.same ? 7 : 3} t={t + (how.same ? 0 : i * 9)} who={'AB'[i]} sym={i && !how.same ? 'NEON' : 'GERM'} />}
    </div>)}</div><Prints feed={feed} who="B" k={k} /></div>
    <ol className="agd-feed" aria-live="off">{lines.map(l => <li key={l.id}>{l.text}</li>)}</ol>
  </div>;
}
