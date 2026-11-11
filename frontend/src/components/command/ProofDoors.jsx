import { toggleFull } from '../../lib/fullView';
import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { Ic3 } from '../../lib/icon3d';
import { AgentDemo, DemoChart } from './AgentDemo';
import { ProofSeal } from './ProofVisuals';
import { priceTip, priceWord, useProofPrices } from '../../lib/proofPrice';
const TrenchChart = lazy(() => import('../terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
const PerpsChart = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));

// 🎬 The reel (owner 2026-11-07: "not for the user to click… a preview of what the agents are capable of, how the agent built it"). Nothing here is operated: tap a capability on the left and watch the agent do it. Its finished pages scroll and press their own buttons, its games play themselves. The tools themselves live in each proof's folder. Every model gets the same tools; a stronger mind makes better work with them.
const PROOFS = {
  pos: { ic: '💻', t: 'PoStatic', full: 'Proof of Static', line: 'Sites, dashboards, tools and games from one sentence.', folders: 'psFolders', make: 'build', go: 'Start a PoStatic', caps: [] },
  pow: { ic: '⛏', t: 'PoW', full: 'Proof of Work', line: 'A real trade, and everything it read before it.', folders: 'powFolders', cmd: 'file a PoW', go: 'Start a PoW',
    caps: [['replay', '⛏', 'One whole trade', 'From scouting a coin to the score it earns'], ['demo', '🧠', 'Two minds at work', 'Both windows, recorded on real sites'], ['chart', '📈', 'Its best real trade', 'On the real chart, with what it read']] },
  pop: { ic: '📉', t: 'PoP', full: 'Proof of Perps', line: 'Both minds call a market blind, on paper, with a number behind every call.', folders: 'popFolders', cmd: 'file a perp', go: 'Start a PoP',
    caps: [['replay', '🙈', 'Blind calls', 'Sealed, opened, then put on the true chart'], ['chart', '💀', 'Where leverage dies', 'True candles with live liquidation lines']] },
  pob: { ic: '🎲', t: 'PoB', full: 'Proof of Bids', line: 'Picks on any game or market, graded by the scoreboard, never by the mind.', folders: 'pobFolders', cmd: 'file a pob best NFL picks', go: 'Start a PoB',
    caps: [['live', '📺', 'Watches the game live', 'Your stream in the room, its agent reading every play beside it'], ['replay', '🎯', 'One graded pick', 'Two minds pick blind, the scoreboard grades it'], ['parlay', '🧾', 'Builds a parlay', 'Legs from different sites, one proof']] },
  poc: { ic: '📣', t: 'PoC', full: 'Proof of Content', line: 'From what people read today to a post, a cut, an image or a 3D commercial.', folders: 'pocFolders', make: 'content', go: 'Start a PoC',
    caps: [['viral', '🔥', 'Viral AI clips', 'Real clips made today on 5 models, the formats trending on TikTok'], ['video', '🎬', 'AI cuts a video', 'Finds real footage, cuts it, adds words, exports'], ['image', '🖼', 'AI makes an image', 'Generates it, then builds the thumbnail'], ['piece:long-road-film', '🎥', '3D commercial', 'A film made by the 3D engine'], ['replay', '📡', 'Trend to post', 'What is moving, the angle, the finished post']] },
  poe: { ic: '📒', t: 'PoEco', full: 'Proof of Eco', line: 'Its books kept true: income, costs and tax set aside, every month drawn and hashed.', folders: 'poeFolders', open: 'poe', go: 'Open PoEco',
    caps: [['books', '📒', 'Its books, drawn', 'Income against costs, month by month, from its real books']] },
};
// A proof type with graded proofs also shows them, graded by OSSY + G4; the kits it builds with are one quiet line under the stage.
const EVERY = [['reviews', '🧑‍⚖️', 'Graded by OSSY + G4', 'Its own proofs: the five checks each reviewer made, pass or fail']];
const K = n => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K` : String(n || 0));

const num = v => +String(v).replace(/,/g, '');
const levOf = kits => { const m = kits.flatMap(k => k.fresh || []).map(x => String(x).match(/^(\w+) mark \$([\d,.]+): 3x long \$([\d,.]+) \/ short \$([\d,.]+), 10x long \$([\d,.]+) \/ short \$([\d,.]+)/)).find(Boolean); return m ? { sym: m[1], mark: num(m[2]), l3: num(m[3]), s3: num(m[4]), l10: num(m[5]), s10: num(m[6]) } : null; };
const Wait = ({ what }) => <p className="dbt-none">{what}</p>;
// ⛏ The real chart its best trade was made on, and the real pictures of what it read before buying.
function TradeDemo({ t }) {
  if (!t?.pair?.pairAddress) return <p className="dbt-none" data-testid="pdr-no-trade">No real trade yet. Its first one shows here on its real chart.</p>;
  const q = agentAuthQuery();
  return <div className="pdr-demo" data-testid="pdr-trade"><div className="pdr-chart"><Suspense fallback={<Wait what="Loading its chart…" />}><TrenchChart key={t.pair.pairAddress} pair={t.pair} defaultInterval="1m" tools={false} tape={false} /></Suspense></div>{t.files?.length ? <ul className="pdr-film" aria-label="Sites it read before buying">{t.files.map(f => <li key={f.file} data-tip={`It read ${f.site}`}><img src={apiUrl(`/api/cats/${t.cat}/powshot/${t.id}/${f.file}?${q}`)} alt={f.site} loading="lazy" onError={e => { e.currentTarget.parentElement.style.display = 'none'; }} /></li>)}</ul> : null}</div>;
}
// 📉 Real candles (TradingView Lightweight Charts) with where 3x and 10x die, from the Leverage Math kit's live numbers.
function PerpDemo({ kits }) {
  const lev = useMemo(() => levOf(kits), [kits]); const lines = lev ? [['l10', lev.l10, '10x LONG DIES'], ['s10', lev.s10, '10x SHORT DIES']].map(([id, price, title]) => ({ id, price, title, color: '#ff8fa3', dash: true })) : [];
  return <div className="pdr-demo" data-testid="pdr-perp"><div className="pdr-chart"><Suspense fallback={<Wait what="Loading true candles…" />}><PerpsChart asset={lev?.sym || 'BTC'} iv="1h" lines={lines} /></Suspense></div></div>;
}
// 🎞 A proof's own replay: a sample run on its own tools, labelled as a sample on the stage.
function useSteps(n, ms = 3400) {
  const [at, setAt] = useState(0); const hold = useRef(0);   // a click jumps to that step and holds it 12 s before the reel plays on
  useEffect(() => { if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined; const t = setInterval(() => { if (!document.hidden && Date.now() > hold.current) setAt(x => (x + 1) % n); }, ms); return () => clearInterval(t); }, [n, ms]);
  const go = useCallback(i => { hold.current = Date.now() + 12000; setAt(((i % n) + n) % n); }, [n]);
  return [at, go];
}
const Steps = ({ names, at, go }) => <span className="prp-dots" role="tablist" aria-label="Steps">{names.map((l, i) => <button type="button" role="tab" aria-selected={at === i} key={l} className={at === i ? 'is-on' : i < at ? 'is-done' : ''} onClick={() => go?.(i)} data-tip={`Jump to ${l}`}>{l}</button>)}</span>;
const Tag = ({ t, real }) => <span className={`prp-tag${real ? ' is-real' : ''}`}>{real ? 'REAL RESULT' : 'SAMPLE RUN'} · {t}</span>;
const POW_STEPS = [['🔎', 'Scouts and reads', 'Five sites, a picture of each', ['dexscreener', 'x.com', 'birdeye', 'solscan', 'gmgn']], ['🧠', 'Both minds decide', 'Three turns to agree on one coin and a size'], ['🛡', 'Exits set first', 'Stop −30%, take +50%, before any buy'], ['⛏', 'Buys and trims', 'Real money through the pool, pinned on the chart'], ['🏅', 'Scored on the result', 'Money and hold time count most']];
function PowReplay() {
  const [at, go] = useSteps(POW_STEPS.length); const [t, setT] = useState(0);
  useEffect(() => { const c = setInterval(() => { if (!document.hidden) setT(x => x + 1); }, 900); return () => clearInterval(c); }, []);
  return <div className="prp" data-testid="pdr-pow-replay"><Tag t="not a real trade" /><Steps names={['READ', 'DECIDE', 'EXITS', 'BUY', 'SCORE']} at={at} go={go} /><div className="prp-main"><DemoChart seed={5} t={t} who="A" sym="SAMPLE" calls={at >= 3} /></div>
    <div className="prp-side">{POW_STEPS.map(([ic, b, say, chips], i) => <button type="button" key={b} onClick={() => go(i)} data-tip="Show this step" className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small>{chips && i === at ? <span className="prp-chips">{chips.map(c => <em key={c}>{c}</em>)}</span> : null}</button>)}{at === 4 ? <span className="prp-seal"><ProofSeal rank="A" tone="good" size={70} parts={[{ label: 'Result', value: 0.9 }, { label: 'Held', value: 0.8 }, { label: 'Reads', value: 0.7 }, { label: 'Exits', value: 1 }, { label: 'New', value: 0.6 }]} />Its score, from its record</span> : null}</div></div>;
}
const POP_STEPS = [['🙈', 'Each mind calls blind', 'Neither sees the other. A call needs a number behind it'], ['📖', 'The calls open', 'They disagree, and both reasons are on the record'], ['📏', 'Lines on true candles', 'Entry, stop and where its leverage dies'], ['📊', 'True price grades it', 'A practice trade runs. No real money moves']];
function PerpReplay({ kits }) {
  const lev = useMemo(() => levOf(kits), [kits]); const [at, go] = useSteps(POP_STEPS.length, 3800); const px = lev?.mark;
  const lines = px && at >= 2 ? [{ id: 'e', price: px, title: 'A ENTRY', color: '#b48cff' }, { id: 's', price: px * 0.975, title: 'A STOP', color: '#ffd54a', dash: true }, { id: 'l', price: lev.l10, title: '10x DIES', color: '#ff8fa3', dash: true }] : [];
  const open = at >= 1;
  return <div className="prp" data-testid="pdr-perp-replay"><Tag t="sample calls on today's real candles" /><Steps names={['BLIND', 'OPEN', 'LINES', 'GRADE']} at={at} go={go} /><div className="prp-main"><div className="pdr-chart" style={{ height: '100%' }}><Suspense fallback={<Wait what="Loading true candles…" />}><PerpsChart asset={lev?.sym || 'BTC'} iv="1h" lines={lines} /></Suspense></div>
    <div className="prp-calls">{[['MIND A', 'LONG 3x', 'Funding is negative while price holds its range', 'long'], ['MIND B', 'SHORT 5x', 'Open interest rose 9% into a flat tape', 'short']].map(([who, call, why, side]) => <div key={who} className={`prp-call${open ? ` is-${side}` : ' is-sealed'}`}><b>{who}</b><strong>{open ? call : 'SEALED'}</strong><small>{open ? why : 'Waiting for the other mind'}</small></div>)}</div></div>
    <div className="prp-side">{POP_STEPS.map(([ic, b, say], i) => <button type="button" key={b} onClick={() => go(i)} data-tip="Show this step" className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></button>)}</div></div>;
}
const POB_STEPS = [['🔎', 'Each mind searches its own sites', 'One reads injuries and form, one reads the odds'], ['🎯', 'Picks blind', 'A pick, a confidence, and the site its number came from'], ['🏟', 'The game plays', 'Live numbers from the scoreboard'], ['✅', 'The scoreboard grades it', 'Never the mind that made the pick']];
function PickReplay() {
  const [at, go] = useSteps(POB_STEPS.length, 3600);
  return <div className="prp" data-testid="pdr-pick-replay"><Tag t="made-up game" /><Steps names={['READ', 'PICK', 'LIVE', 'GRADE']} at={at} go={go} /><div className="prp-main"><div className="prp-game"><div className="prp-teams"><b>HOME</b><em className="m-num">{at >= 2 ? (at >= 3 ? '112 – 104' : '58 – 55') : 'vs'}</em><b>AWAY</b></div>
    <div className="prp-minds">{[['MIND A · FORM', 'Home wins', 72, 'Away star out, says the injury report'], ['MIND B · ODDS', 'Home −4.5', 61, 'The line moved two points since noon']].map(([who, p, c, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{at >= 1 ? p : 'Reading…'}</strong><u><s style={{ transform: `scaleX(${at >= 1 ? c / 100 : 0})` }} /></u><small>{at >= 1 ? `${c}% · ${why}` : 'Its own sites, its own search'}</small></div>)}</div>{at === 3 ? <span className="prp-grade">BOTH RIGHT · GRADED BY THE FINAL SCORE</span> : null}</div></div>
    <div className="prp-side">{POB_STEPS.map(([ic, b, say], i) => <button type="button" key={b} onClick={() => go(i)} data-tip="Show this step" className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></button>)}</div></div>;
}
const POC_STEPS = [['📡', 'Reads what is moving', 'Five trend sources, a picture of each'], ['💡', 'Each mind pitches an angle', 'Two different takes on the same story'], ['✍', 'Writes the finished post', 'In your voice, ready to use. It never posts by itself']];
function StoryReplay() {
  const [at, go] = useSteps(POC_STEPS.length, 4200);
  return <div className="prp" data-testid="pdr-story-replay"><Tag t="sample topics" /><Steps names={['TRENDS', 'ANGLES', 'POST']} at={at} go={go} /><div className="prp-main">
    {at === 0 ? <div className="prp-trend"><h4>RISING RIGHT NOW</h4><ul>{[['New phone launch', 0.92, '+340%'], ['Playoff race', 0.71, '+120%'], ['Solana ETF', 0.55, '+64%'], ['Coffee prices', 0.3, '+22%']].map(([l, v, g]) => <li key={l}><span>{l}</span><b className="m-num">{g}</b><u><s style={{ transform: `scaleX(${v})` }} /></u></li>)}</ul></div> : null}
    {at === 1 ? <div className="prp-game"><div className="prp-minds">{[['MIND A · THE ARGUMENT', 'Nobody needs this phone, and everyone will buy it', 'Replies are 3 to 1 against'], ['MIND B · BEFORE THE PEAK', 'The one feature reviewers skipped', 'Searches for it doubled today']].map(([who, p, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{p}</strong><small>{why}</small></div>)}</div></div> : null}
    {at === 2 ? <div className="prp-post"><article><header><i aria-hidden="true" />Your account</header><p>Every review skipped the one thing you'll use daily.{'\n'}I spent a week with it. Three things they missed 🧵</p><small>READY TO POST · ALSO A 40 SECOND SCRIPT AND A THUMBNAIL</small></article></div> : null}</div>
    <div className="prp-side">{POC_STEPS.map(([ic, b, say], i) => <button type="button" key={b} onClick={() => go(i)} data-tip="Show this step" className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></button>)}</div></div>;
}
// 📊 Not every PoStatic is a 3D site (owner 2026-11-07: "a mix, not just games and repeated landing pages"). Example pages of the kinds the Build tiles start, labelled as examples with sample data.
export const EXAMPLE_PIECES = [
  { id: 'pulse-dash', kind: 'dash', name: 'Pulse', what: 'White dashboard, Day and Night', ask: 'A clean white analytics dashboard with a Day / Night switch and animated charts', things: ['stat cards', 'line chart', 'donut', 'bars'], src: '/showcase/pos/pulse-dash.html', thumb: '/showcase/pos/pulse-dash.jpg' },
  { id: 'tape-desk', kind: 'chart', name: 'Tape desk', what: 'Live chart desk', ask: 'A trading desk page: candles that tick, an order book and a trade tape with whales marked', things: ['candles', 'order book', 'trade tape'], src: '/showcase/pos/tape-desk.html', thumb: '/showcase/pos/tape-desk.jpg' },
  { id: 'wick-breaker', kind: 'game', name: 'Wick Breaker', what: 'Brick breaker on a candle chart', ask: 'A brick breaker where the bricks are a candle chart: red candles take two hits, gold ones drop power-ups, combos multiply the score', things: ['ball physics', 'power-ups', 'combos', 'a bot that plays'], src: '/showcase/pos/wick-breaker.html', thumb: '/showcase/pos/wick-breaker.jpg' },
  { id: 'mempool', kind: 'game', name: 'Mempool', what: 'Twin-stick shooter in waves', ask: 'A twin-stick space shooter: you are the validator clearing spam, MEV bots dash at you, whales split, snipers shoot back', things: ['waves', 'dash', 'auto-aim', 'pickups'], src: '/showcase/pos/mempool.html', thumb: '/showcase/pos/mempool.jpg' },
  { id: 'loan-tool', kind: 'tool', name: 'Keyhole', what: 'Loan calculator', ask: 'A loan calculator: sliders, the monthly payment as a big number and a chart of interest against principal', things: ['sliders', 'area chart', 'year table'], src: '/showcase/pos/loan-tool.html', thumb: '/showcase/pos/loan-tool.jpg' },
];
const KIND_WORD = { game: 'GAME', site: 'SITE', dash: 'DASHBOARD', chart: 'CHART', tool: 'TOOL' };
// one of each kind in turn, so the reel opens on a mix and never runs a row of the same thing
export const mixPieces = rows => { const by = {}; rows.forEach(t => { (by[t.kind] = by[t.kind] || []).push(t); }); const out = []; for (let i = 0; out.length < rows.length; i++) Object.values(by).forEach(l => { if (l[i]) out.push(l[i]); }); return out; };
// 🎬 How the agent built it: the ask, its choices, the real things it found, then the finished page playing by itself.
const BUILD_MS = [2600, 2400, 2200];
function Piece({ id, t, cat, work }) {
  const [page, setPage] = useState(''); const [err, setErr] = useState(''); const [at, setAt] = useState(0);
  useEffect(() => { let on = true; setPage(''); setErr(''); if (t?.src) { setPage('src'); return undefined; } Promise.resolve().then(() => work(cat.id, { op: 'tools_showcase', job: id })).then(j => on && setPage(j.preview || '')).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id, work, id, t?.src]);
  useEffect(() => { setAt(0); if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setAt(3); return undefined; } let n = 0; const ts = BUILD_MS.map(ms => { n += ms; return setTimeout(() => setAt(x => x + 1), n); }); return () => ts.forEach(clearTimeout); }, [id]);
  const ready = at >= 3 && page;
  return <div className="flm" data-testid="pdr-piece">{page ? <iframe className="pdr-frame" title={t?.name || 'Finished work'} {...(t?.src ? { src: `${t.src}?demo=1` } : { srcDoc: page })} sandbox="allow-scripts" tabIndex={-1} data-testid="pdr-piece-frame" /> : null}
    <div className={`flm-over${ready ? ' is-off' : ''}`} aria-hidden={ready}><div className="flm-card"><small className="m-label">YOU ASK</small><p className="flm-ask" key={id}>{t?.ask}</p>
      {at >= 1 ? <div className="flm-row"><small className="m-label">IT CHOOSES</small><span className="flm-chips">{t?.mood ? <em>Mood: {t.mood}</em> : null}{(t?.things || []).map(x => <em key={x}>{x === 'blackhole' ? 'black hole' : x}</em>)}</span></div> : null}
      {at >= 2 ? <div className="flm-row"><small className="m-label">{t?.src ? 'IT WRITES IT' : 'CODE PLACES IT'}</small><span className="flm-build"><i /><i /><i /></span><small>{t?.src ? (t.kind === 'game' ? 'Physics, controls, sound, a bot that plays it' : 'Layout, charts, motion, Day and Night') : 'Real models, a real place, light, camera, finish'}</small></div> : null}{err ? <p className="dbt-none">{err}</p> : at >= 3 && !page ? <p className="dbt-none">Opening it…</p> : null}</div></div>
    {ready ? <span className="flm-tag">{t?.src ? (t.kind === 'game' ? 'EXAMPLE GAME · ITS BOT IS PLAYING · PLAYABLE' : 'EXAMPLE PAGE · SAMPLE DATA') : t?.kind === 'game' ? 'BUILT BY AN AGENT · ITS BOT IS PLAYING' : 'BUILT BY AN AGENT · RUNNING LIVE'}</span> : null}</div>;
}
// 🎬 AI cuts a video: real public domain NASA footage, on a timeline, words on top, exported.
const CLIPS = [['Launch', 'https://images-assets.nasa.gov/video/KSC-20240525-MH-RKL01-0001-Rocket_Lab_PREFIRE_1_Launch_1080p-M6988/KSC-20240525-MH-RKL01-0001-Rocket_Lab_PREFIRE_1_Launch_1080p-M6988~mobile.mp4#t=16', 'WE LEFT'], ['Earth', 'https://images-assets.nasa.gov/video/Earth%20Views%20from%20the%20International%20Space%20Station/Earth%20Views%20from%20the%20International%20Space%20Station~mobile.mp4#t=8', 'AT DAWN'], ['Liftoff', 'https://images-assets.nasa.gov/video/KSC-20230507-MH-RLS01-TROPICS_Rocket_Launch-Rocket_Lab-WON_3330130/KSC-20230507-MH-RLS01-TROPICS_Rocket_Launch-Rocket_Lab-WON_3330130~mobile.mp4#t=20', 'AND KEPT GOING']];
const CUT_LOG = ['Reads your ask: 15 seconds, big words', 'Searches NASA for launch footage', 'Keeps 3 clips, public domain', 'Opens on the payoff, cuts every 4 seconds', 'Adds words people can read on a phone', 'Exports an MP4 on your machine'];
function VideoFilm() {
  const [at, go] = useSteps(CUT_LOG.length * 2, 2600); const step = Math.floor(at / 2); const on = Math.min(2, Math.max(0, step >= 3 ? at - 6 : 0)) % 3;
  return <div className="prp is-wide" data-testid="pdr-video"><Tag t="real NASA footage, public domain" /><div className="prp-main flm-mon">{CLIPS.map(([n, src], i) => (i === on ? <video key={n} src={src} autoPlay muted loop playsInline preload="metadata" /> : null))}{step >= 4 ? <p className="flm-word" key={on}>{CLIPS[on][2]}</p> : null}{step >= 5 ? <span className="flm-done">launch-cut.mp4 · 15 s · ready</span> : null}
    <div className="flm-time" aria-hidden="true"><span>{CLIPS.map(([n], i) => <i key={n} className={`${step >= i + 1 ? 'is-in' : ''}${i === on && step >= 3 ? ' is-on' : ''}`}>{step >= i + 1 ? n : ''}</i>)}</span><span className="is-words">{step >= 4 ? CLIPS.map(([n, , w]) => <b key={n}>{w}</b>) : null}</span><u style={{ transform: `translateX(${step >= 3 ? ((at % 12) / 12) * 100 : 0}%)` }} /></div></div>
    <ol className="flm-log prp-side">{CUT_LOG.map((l, i) => <li key={l} className={i === step ? 'is-on' : i < step ? 'is-done' : ''}><button type="button" onClick={() => go(i * 2)} data-tip="Show this step">{l}</button></li>)}</ol></div>;
}
// 🔥 Viral AI clips (owner 2026-11-10: "best img/video… real and relevant to the viral AI videos today"): the formats trending on
// TikTok / Reels, each a REAL result made on its model (OpenRouter, 2026-11-10), with the model, its price and how long it took.
// The list is the server's own (media_models presets), so the Showcase and the in-chat maker can never disagree.
function ViralReel({ cat, work }) {
  const [rows, setRows] = useState(null); const [on, setOn] = useState(0);
  useEffect(() => { let live = true; if (cat?.id && work) work(cat.id, { op: 'media_models' }).then(d => { if (live) setRows((d?.presets || []).filter(x => x.sample)); }).catch(() => live && setRows([])); else setRows([]); return () => { live = false; }; }, [cat?.id, work]);
  useEffect(() => { if (!rows?.length) return undefined; const t = setInterval(() => { if (!document.hidden) setOn(i => (i + 1) % rows.length); }, 6000); return () => clearInterval(t); }, [rows]);
  if (!rows?.length) return <div className="prp is-wide pdr-viral" data-testid="pdr-viral"><p className="dbt-none pdr-wait">{rows ? 'No clips yet.' : 'Opening it…'}</p></div>;
  const x = rows[on % rows.length];
  return <div className="prp is-wide pdr-viral" data-testid="pdr-viral"><Tag real t="made on these models 2026-11-10, unedited" />
    <div className="prp-main pdv-stage">{x.kind === 'video' ? <video key={x.id} src={x.sample} autoPlay muted loop playsInline preload="metadata" aria-label={`${x.label}, made on ${x.modelLabel}`} />
      : <img key={x.id} src={x.sample} alt={`${x.label}, made on ${x.modelLabel}`} decoding="async" />}
      <span className="pdv-cap"><b>{x.label}</b><small>{x.modelLabel} · ${Number(x.usd).toFixed(2)}{x.secs ? ` · ${x.secs}s to make` : ''}</small></span></div>
    <ol className="flm-log prp-side pdv-list">{rows.map((r, i) => <li key={r.id} className={i === on ? 'is-on' : ''}><button type="button" onClick={() => setOn(i)} data-testid={`pdv-${r.id}`} data-tip={r.trend}>{r.kind === 'video' ? '🎬' : '🖼'} {r.label}<small>{r.trend}</small></button></li>)}</ol></div>;
}
// 🖼 AI makes an image: a real generated picture comes into focus, then the thumbnail is built on it, layer by layer.
const IMG_LOG = ['Writes the prompt from your ask', 'Generates it with a free image model', 'Crops for a phone screen', 'Adds 3 big words', 'Adds the accent', 'Saves 3 versions to test'];
function ImageFilm() {
  const [at, go] = useSteps(IMG_LOG.length, 2600); const pics = ['/showcase/poc/gen1.jpg', '/showcase/poc/gen2.jpg', '/showcase/night-run.jpg'];   // landscape art: this reel crops for a phone screen (a 9:16 still blew up blurry here; the vertical ones live in 🔥 Viral AI clips)
  return <div className="prp is-wide" data-testid="pdr-image"><Tag t="a real generated picture" /><div className="prp-main flm-art"><img src={pics[0]} alt="" className={at === 0 ? 'is-blur' : at === 1 ? 'is-soft' : at >= 2 ? 'is-crop' : ''} />{at === 0 ? <p className="flm-prompt">dramatic rocket launch at dusk, cinematic, wide shot</p> : null}{at >= 3 ? <h4 className="flm-big">We <em>left</em> at dusk</h4> : null}{at >= 4 ? <b className="flm-pill">NEW</b> : null}{at >= 5 ? <span className="flm-vers">{pics.map(p => <img key={p} src={p} alt="" loading="lazy" />)}</span> : null}</div>
    <ol className="flm-log prp-side">{IMG_LOG.map((l, i) => <li key={l} className={i === at ? 'is-on' : i < at ? 'is-done' : ''}><button type="button" onClick={() => go(i)} data-tip="Show this step">{l}</button></li>)}</ol></div>;
}
const PARLAY_STEPS = [['🔎', 'Reads a different site per leg', 'Injuries on one, lines on another'], ['🧾', 'Adds each leg with its reason', 'A number from a site, or no leg'], ['✖', 'Works out the real odds', 'Every leg has to hit'], ['✅', 'Grades leg by leg', 'From the final scores']];
const LEGS = [['Home wins', 72, 'rotowire'], ['Over 214.5', 58, 'oddsshark'], ['Star 25+ points', 64, 'teamrankings']];
function ParlayReplay() {
  const [at, go] = useSteps(PARLAY_STEPS.length, 3400); const n = Math.min(LEGS.length, at + 1); const all = LEGS.reduce((a, l) => a * (l[1] / 100), 1);
  return <div className="prp" data-testid="pdr-parlay"><Tag t="made-up games" /><Steps names={['READ', 'LEGS', 'ODDS', 'GRADE']} at={at} go={go} /><div className="prp-main"><div className="prp-game"><div className="prp-minds is-legs">{LEGS.slice(0, n).map(([p, c, site]) => <div key={p} className="prp-mind"><b>{site}.com</b><strong>{p}{at === 3 ? ' ✓' : ''}</strong><u><s style={{ transform: `scaleX(${c / 100})` }} /></u><small>{c}% by its read</small></div>)}</div>{at >= 2 ? <span className="prp-grade">ALL THREE: {Math.round(all * 100)}%{at === 3 ? ' · GRADED BY THE SCORES' : ''}</span> : null}</div></div><div className="prp-side">{PARLAY_STEPS.map(([ic, b, say], i) => <button type="button" key={b} onClick={() => go(i)} data-tip="Show this step" className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></button>)}</div></div>;
}
// 📺 Watches the game live (owner 2026-11-10: "overlay edits of how agents work live if they added nfl+ or nba tv to each room"): the owner's own
// stream plays in the room, its agent reads the live score and play-by-play beside it, and its pick is graded by the final score. The footage
// here is AI-made (no league, no logos), so nothing is anyone's broadcast; the calls are a sample.
const GAMES = [{ src: '/showcase/pob/gridiron.mp4', poster: '/showcase/pob/gridiron.jpg', sport: 'FOOTBALL', home: 'HOME', away: 'AWAY', start: [17, 20], end: [24, 20], clock: ['Q4', 134], plays: [
  ['READS', 'Third and 8, two deep safeties, the corner is playing off'], ['SPOTS', 'Receiver 29 has a step on the outside'], ['CALLS', 'Deep shot is on. Home win chance 41% → 68%'], ['PICK', 'Home +2.5 holds · 66% · graded by the final score']] },
{ src: '/showcase/pob/hoops.mp4', poster: '/showcase/pob/hoops.jpg', sport: 'BASKETBALL', home: 'HOME', away: 'AWAY', start: [98, 101], end: [102, 101], clock: ['Q4', 71], plays: [
  ['READS', 'Home on a 9–2 run, their big has 4 fouls'], ['SPOTS', 'Drive to the rim: the help defender is late'], ['CALLS', 'Run keeps going. Home win chance 44% → 61%'], ['PICK', 'Home moneyline · 61% · graded by the final score']] }];
const LIVE_LOG = ['Your NFL+ or NBA TV plays in the room', 'It reads the live score and every play', 'Win chance moves, and it says why', 'Its pick waits for the final score'];
function LiveGame() {
  const [at, go] = useSteps(4, 2600); const [g, setG] = useState(0); const [ok, setOk] = useState({});
  const rows = GAMES.filter(x => ok[x.src] !== false); const x = rows[g % Math.max(1, rows.length)] || GAMES[0];
  useEffect(() => { if (at === 3) { const t = setTimeout(() => setG(i => i + 1), 2400); return () => clearTimeout(t); } return undefined; }, [at]);
  const sc = at >= 2 ? x.end : x.start; const sec = Math.max(0, x.clock[1] - at * 9); const win = [x.plays[2][1].match(/(\d+)% → (\d+)%/)].map(m => (m ? [+m[1], +m[2]] : [50, 50]))[0];
  return <div className="prp is-wide pdr-live" data-testid="pdr-live"><Tag t="AI-made footage, no real league · sample calls" />
    <div className="prp-main plv-stage"><video key={x.src} src={x.src} poster={x.poster} autoPlay muted loop playsInline preload="metadata" onError={() => setOk(o => ({ ...o, [x.src]: false }))} aria-label={`${x.sport.toLowerCase()} footage, AI-made`} />
      <span className="plv-bug" aria-hidden="true"><b>{x.home}</b><i className="m-num" key={`h${sc[0]}`}>{sc[0]}</i><i className="m-num" key={`a${sc[1]}`}>{sc[1]}</i><b>{x.away}</b><small className="m-num">{x.clock[0]} {Math.floor(sec / 60)}:{String(sec % 60).padStart(2, '0')}</small></span>
      <span className="plv-live" aria-hidden="true"><s />LIVE · YOUR STREAM</span>
      <span className="plv-ring" style={{ '--x': at === 1 ? '72%' : '50%', '--y': at === 1 ? '62%' : '55%' }} aria-hidden="true" />
      <aside className="plv-mind" aria-live="polite"><header><Ic3 e="🧠" size="16px" /><b>ITS AGENT · READING</b></header>
        <ol>{x.plays.slice(0, at + 1).map(([k, say], i) => <li key={`${g}-${k}`} className={i === at ? 'is-on' : ''}><em>{k}</em>{say}</li>)}</ol>
        <div className="plv-win"><small>HOME WIN CHANCE</small><b className="m-num">{at >= 2 ? win[1] : win[0]}%</b><u><s style={{ transform: `scaleX(${(at >= 2 ? win[1] : win[0]) / 100})` }} /></u></div></aside></div>
    <ol className="flm-log prp-side">{LIVE_LOG.map((l, i) => <li key={l} className={i === at ? 'is-on' : i < at ? 'is-done' : ''}><button type="button" onClick={() => go(i)} data-tip="Show this step">{l}</button></li>)}</ol></div>;
}
// 🧩 Builds its own tool (owner 2026-11-10: "have ur agent build a component off stash that best fits proof file request"): the file asks for a
// watcher, its agent searches the stash, the best fit is forked (v1.00 → v1.01 in its git folder) and the tool runs. The parts are the real kits
// for this proof kind; the fit numbers and the tool's readings are a sample run.
// 🧑‍⚖️ Its own proofs, graded: each reviewer's five checks light up one by one, pass or fail. Real rows only.
export function ReviewReel({ rows }) {
  const [i, setI] = useState(0); const r = rows?.[i % Math.max(1, rows?.length || 1)];
  const [at] = useSteps(6, 900);
  if (!rows?.length) return <p className="dbt-none" data-testid="pdr-no-reviews">No graded proof of this kind yet. OSSY and G4 grade its first one within minutes of it closing.</p>;
  return <div className="prv" data-testid="pdr-reviews"><header><span className="m-seg" role="tablist" aria-label="Which proof">{rows.map((x, n) => <button key={x.id} type="button" role="tab" aria-selected={n === i % rows.length} className={n === i % rows.length ? 'is-on' : ''} onClick={() => setI(n)} data-tip={`Score ${x.score} · ${x.verdict}`}>{x.title}</button>)}</span>
    <b className={`prv-score is-${r.verdict}`} data-tip="The two reviewers' average; each check is worth 20"><i className="m-num">{r.score ?? '—'}</i><small>{String(r.verdict || '').toUpperCase()}{r.agree === false ? ' · SPLIT' : ''}</small></b></header>
    <div className="prv-minds">{Object.entries(r.by || {}).map(([n, v]) => <section key={n} className={`prv-mind is-${v.verdict}`}><h5>{n.toUpperCase()} <i className="m-num">{v.score}</i><small>{v.answeredBy || ''}</small></h5>
      <ol>{(v.checks || []).map((c, k) => <li key={k} className={`${k < at ? 'is-in' : ''} ${String(c).startsWith('✓') ? 'is-ok' : 'is-no'}`} style={{ '--i': k }}>{c}</li>)}</ol></section>)}</div></div>;
}
// 🧰 What it builds with: every kit for this kind, its live version, and an arrow when the daily check moved it up.
// 📒 Its books, drawn: income and costs per month as bars, the net on top. Real books only.
export function BooksDemo({ b }) {
  if (!b?.months?.length) return <p className="dbt-none" data-testid="pdr-no-books">No books yet. Its first PoEco draws here.</p>;
  const top = Math.max(1, ...b.months.flatMap(m => [m.income || 0, m.costs || 0])); const usd = n => `$${Math.round(n || 0).toLocaleString()}`;
  return <div className="pbk" data-testid="pdr-books"><header><b>{b.topic || 'Its books'}</b><span className="m-num">IN {usd(b.income)} · OUT {usd(b.costs)} · NET <i>{usd(b.net)}</i> · {b.margin ?? '—'}% margin</span></header>
    <ol className="pbk-bars">{b.months.map((m, i) => <li key={m.month} style={{ '--i': i }} data-tip={`${m.month}: in ${usd(m.income)}, out ${usd(m.costs)}, net ${usd(m.net)}`}><span><u className="is-in" style={{ transform: `scaleY(${(m.income || 0) / top})` }} /><u className="is-out" style={{ transform: `scaleY(${(m.costs || 0) / top})` }} /></span><small className="m-num">{m.month}</small><b className="m-num">{usd(m.net)}</b></li>)}</ol>
    {b.taxSetAside != null ? <p className="pbk-tax m-num">TAX SET ASIDE {usd(b.taxSetAside)}</p> : null}</div>;
}
// 📰 Today's proofs brief (owner 2026-11-10: "daily proofs update… a quick draw for a summary on best proof types to work in"): straight from
// the proof record (filed, reviewed by the other minds, graded) and the kits that moved today. No model writes it, so it can't be talked up.
const BRIEF_NAME = { pow: 'PoW', pop: 'PoP', pob: 'PoB', poc: 'PoC', pos: 'PoStatic', poe: 'PoEco' };
const BRIEF_DOOR = { pos: 'pos', pow: 'pow', pop: 'pop', pob: 'pob', poc: 'poc', poe: 'poe' };
// 🃏 THE TYPE ROW (owner 2026-11-11: "un-necessary tabs with no design … so much to click each proof type"): the six proof types as lit cards
// that carry today's live numbers (filed this week, graded right, review score) — the brief box and the tab row are one row now. One click per type.
export function ProofBrief({ k, onPick }) {
  const [b, setB] = useState(null);
  useEffect(() => { let live = true; fetch(apiUrl('/api/cats/brief/proofs')).then(r => (r.ok ? r.json() : null)).then(j => live && setB(j || { rows: [] })).catch(() => live && setB({ rows: [] })); return () => { live = false; }; }, []);
  const by = Object.fromEntries((b?.rows || []).map(r => [r.kind, r]));
  return <nav className="pdr-types" role="tablist" aria-label="Proof types" data-testid="proof-brief">{Object.entries(PROOFS).map(([x, v], i) => { const r = by[x];
    return <button key={x} type="button" role="tab" aria-selected={k === x} className={`pdr-type is-${x}${k === x ? ' is-on' : ''}${b?.best === x ? ' is-best' : ''}`} style={{ '--i': i }} onClick={() => onPick?.(x)} data-testid={`pdr-${x}`}
      data-tip={r ? `${v.full}: ${r.filed24} filed today, ${r.filed7} this week · ${r.reviews} reviewed${r.passPct != null ? ` (${r.passPct}% passed)` : ''} · graded ${r.right} right / ${r.wrong} wrong` : v.full}>
      <span className="pdr-type-ic"><Ic3 e={v.ic} size="26px" /></span><b>{v.t}</b>
      <small className="m-num" data-testid={`proof-brief-${x}`}>{r ? `${r.filed7} this wk${r.rightPct != null ? ` · ${r.rightPct}% right` : ''}` : v.full}</small>
      <u aria-hidden="true"><s style={{ transform: `scaleX(${(r?.avgScore || 0) / 100})` }} /></u>{b?.best === x ? <em className="pdr-type-hot" data-tip="Where the work is today: most filed this week">HOT</em> : null}</button>; })}</nav>;
}
export function kitLine(fresh) {   // what it builds with, one quiet line under the stage (was a whole tab)
  const moved = fresh?.kits?.filter(x => x.prev) || []; return moved.length ? `🧰 ${moved.length} kit${moved.length > 1 ? 's' : ''} updated today: ${moved.slice(0, 5).map(x => `${x.pkg || x.id} ${x.prev} → ${x.v}`).join(' · ')}` : '';
}

// ▶ Every preview ends in a start (owner 2026-11-11: "start something is the point of showcase"). Pick a ready ask or write your own, then Start:
// PoStatic / PoC make their folder with the ask in its chat box (nothing runs until you send); PoW / PoP / PoB send the ask to the agent's chat.
const TRADE_ASKS = {
  pow: [['⛏', 'Hottest young coin', 'file a PoW on the hottest pump.fun coin under an hour old'], ['🛡', 'Rug check first', 'file a PoW on a coin with clean holders and a locked pool'], ['🐋', 'Follow a whale', 'file a PoW on the coin the biggest wallet bought today'], ['📚', 'Edge desk', 'edge']],
  pop: [['📉', 'BTC blind call', 'file a perp on BTC: long or short, entry, stop and the number behind it'], ['💀', 'Where 10x dies', 'file a perp on SOL and show where 10x longs get liquidated'], ['🔄', 'Funding flip', 'file a perp on the market whose funding just flipped']],
  pob: [['🏈', 'Tonight\'s NFL', 'file a pob best NFL picks tonight'], ['🏀', 'NBA value pick', 'file a pob one NBA pick with real value'], ['🧾', '3-leg parlay', 'file a pob a 3 leg parlay, each leg from a different site']],
};
// 🎬 Its ad for this proof type, made by the owner's agent through a real Build folder and recorded to video ($1.25 cap for all six).
// Only the owner sees it: the video comes from an owner-only door, and Download saves the .webm.
const AD_STATE = { waiting: 'Waiting its turn', building: 'Its mind is building the page', recording: 'Recording the page to video', done: 'Ready', 'no video': 'Built, but the video did not record', 'no page': 'The mind returned no page', 'over budget': 'Stopped at the $1.25 cap', 'no room for a folder': 'No room for another folder', fixing: 'Its page crashed: one fix pass with the error', 'page error': 'Its page still crashes, so no video' };
export function AdReel({ k, cat, work, ads: given }) {
  const [ads, setAds] = useState(given || null); const [run, setRun] = useState(false); const [err, setErr] = useState('');
  const pull = useCallback(() => work(cat.id, { op: 'show_ads' }).then(j => { setAds(a => ({ ...(a || {}), ...j.ads, cat: (a || given || {}).cat || cat.id })); setRun(!!j.running); }).catch(e => setErr(e.message)), [cat.id, work, given]);
  useEffect(() => { pull(); }, [cat.id]);   // eslint-disable-line react-hooks/exhaustive-deps -- each open reads the real state: the Showcase's copy went stale after a run
  useEffect(() => { if (!run) return undefined; const t = setInterval(() => { if (!document.hidden) pull(); }, 8000); return () => clearInterval(t); }, [run, pull]);
  const row = ads?.rows?.[k]; const src = row?.video && ads?.cat ? apiUrl(`/api/cats/${ads.cat}/showad/${k}?${agentAuthQuery()}`) : '';
  const redo = async () => { setErr(''); try { const j = await work(cat.id, { op: 'show_ads', text: `redo:${k}` }); setAds(a => ({ ...(a || {}), ...j.ads, cat: cat.id })); setRun(!!j.running); } catch (e) { setErr(e.message); } };
  const go = async () => { setErr(''); try { const j = await work(cat.id, { op: 'show_ads', text: 'go' }); setAds(a => ({ ...(a || {}), ...j.ads, cat: cat.id })); setRun(!!j.running); } catch (e) { setErr(e.message); } };
  return <div className="adr" data-testid="pdr-ad">{src ? <video className="adr-vid" src={src} autoPlay loop muted playsInline data-testid="adr-video" /> : <div className="adr-wait"><i className="adr-orb" aria-hidden="true" /><b>{row?.ws ? AD_STATE[row.state] || row.state : 'Its ad is not made yet'}</b>
      <small>{ads ? `$${(ads.spent || 0).toFixed(2)} of $${(ads.budget || 1.25).toFixed(2)} spent · ${Object.values(ads.rows || {}).filter(r => r.video).length} of 6 ads ready` : 'Your agent builds one ad page per proof type, then records each to video. $1.25 cap for all six.'}</small>
      {ads?.rows ? <span className="adr-steps" aria-label="Each ad">{Object.entries(ads.rows).map(([x, r]) => <i key={x} className={`is-${r.video ? 'done' : r.ws ? 'on' : 'off'}`} data-tip={`${r.name}: ${r.ws ? AD_STATE[r.state] || r.state : 'waiting'}${r.cost ? ` · $${r.cost.toFixed(3)}` : ''}${r.err ? ` · ${r.err}` : ''}`}>{r.name}</i>)}</span> : null}
      <button type="button" className="m-btn m-go" disabled={run} onClick={go} data-tip="Starts the next ad that is missing. It stops before $1.25" data-testid="adr-make">{run ? 'Making…' : ads?.spent ? 'Make the rest' : 'Have this agent make the ads'}</button>{err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>}
    {src ? <a className="m-btn adr-dl" href={`${src}&dl=1`} download data-tip="Saves this ad as a .webm (only you can)" data-testid="adr-dl">⬇ Download</a> : null}
    {row?.ws && !['building', 'recording', 'fixing'].includes(row.state) ? <button type="button" className="m-btn adr-redo" onClick={redo} data-tip={`Builds this ad again from scratch. What it cost so far stays counted toward the $${(ads?.budget || 1.25).toFixed(2)} cap`} data-testid="adr-redo">↻ Redo this ad</button> : null}</div>;
}
export function ShowStart({ k, starters = {}, onMake, onCommand, onOpen, p, cost = '', costTip = '', seed = null }) {
  const rows = k === 'pos' ? starters.build || [] : k === 'poc' ? [...(starters.content || []), ...(starters.research || []).slice(0, 2).map(r => [...r, 'research'])] : TRADE_ASKS[k] || [];
  const ask0 = r => [].concat(r?.[3] ?? r?.[2] ?? '')[0] || '';
  const [at, setAt] = useState(0); const [text, setText] = useState(() => (k === 'pow' || k === 'pop' || k === 'pob' ? rows[0]?.[2] : ask0(rows[0])) || '');
  useEffect(() => { if (seed?.ask) { setText(seed.ask); setAt(-1); } }, [seed?.ask]);   // the page on the stage: its own ask, ready to make your version
  if (k === 'poe') return <div className="sst" data-testid="show-start"><span className="sst-say"><b>Its books, kept true</b><small>Income, costs and tax set aside, drawn every month</small></span><button type="button" className="m-btn m-go sst-go" onClick={() => onOpen?.(p.open)} data-testid="sst-go">Open PoEco ▸</button></div>;
  const trade = !!TRADE_ASKS[k];
  const pick = (r, i) => { setAt(i); setText(trade ? (r[2] === 'edge' ? '' : r[2]) : ask0(r)); if (trade && r[2] === 'edge') onMake?.('edge', ['📚', 'Edge desk', '', '']); };
  const go = () => { const t = text.trim(); if (!t) return; if (trade) onCommand?.(t); else { const r = at < 0 ? ['💻', seed?.name || p.t, ''] : rows[at] || []; onMake?.(r[4] === 'research' ? 'research' : k === 'pos' ? 'build' : 'content', [r[0] || p.ic, r[1] || p.t, r[2] || '', t]); } };
  return <form className="sst" onSubmit={e => { e.preventDefault(); go(); }} data-testid="show-start">
    <ul className="sst-chips" aria-label="Ready asks">{rows.slice(0, 8).map((r, i) => <li key={r[1]} style={{ '--i': i }}><button type="button" className={at === i ? 'is-on' : ''} aria-pressed={at === i} onClick={() => pick(r, i)} data-tip={trade ? r[2] : r[2]} data-testid={`sst-chip-${i}`}><Ic3 e={r[0]} size="16px" />{r[1]}</button></li>)}</ul>
    <span className="sst-row"><input className="m-input sst-in" value={text} onChange={e => setText(e.target.value)} maxLength={600} placeholder={`Tell it what to make: ${p.line}`} aria-label="Your ask" data-testid="sst-text" />
      <button type="submit" className="m-btn m-go sst-go" disabled={!text.trim()} data-tip={trade ? `Sends this to its chat. ${costTip}` : 'Makes the folder with this ask in its chat box. Nothing runs until you send'} data-testid="sst-go">{p.go} ▸{cost ? <small className="pdr-go-cost" data-testid="pdr-go-cost">{cost}</small> : null}</button></span></form>;
}
export function ProofDoors({ cat, d, work, onCommand, onMake, onOpen, kindFirst = 'pos', starters }) {
  const [k, setK] = useState(kindFirst); const [counts, setCounts] = useState(null); const [kits, setKits] = useState([]); const [trade, setTrade] = useState(null); const [on, setOn] = useState(''); const [show, setShow] = useState(null); const p = PROOFS[k]; const prices = useProofPrices(cat?.id, work); const cost = p.cmd ? priceWord(prices?.[k]) : '';
  useEffect(() => { let live = true; Promise.resolve().then(() => Promise.all([work(cat.id, { op: 'tools_show' }).catch(() => null), work(cat.id, { op: 'kit_list' }).catch(() => null), work(cat.id, { op: 'demo_trade' }).catch(() => null), work(cat.id, { op: 'showcase' }).catch(() => null)])).then(([a, b, t, sc]) => { if (!live) return; setCounts(a); setKits(b?.kits || []); setTrade(t?.trade || null); setShow(sc); }); return () => { live = false; }; }, [cat.id, work]);
  const rows = mixPieces([...(counts?.templates || []).filter(t => t.kind !== 'film' && t.kind !== 'game'), ...(counts ? EXAMPLE_PIECES : [])]); const pieces = k === 'pos' ? rows : []; const adMade = !!show?.ads?.rows?.[k]?.video; const adCap = adMade || show?.adsOk ? [['ad', '🎬', 'Its ad', 'The ad your agent made for this proof, recorded to video']] : [];
  const own = (pieces.length ? pieces.slice(0, 6).map(t => [`piece:${t.id}`, null, t.name, t.what, t.thumb, t.kind]) : p.caps).filter(c => c[0] !== 'chart' || k !== 'pow' || trade?.pair?.pairAddress);
  const caps = [...(adMade ? adCap : []), ...own, ...(show?.reviews?.[k]?.length ? [EVERY[0]] : []), ...(adMade ? [] : adCap)]; const now = caps.some(c => c[0] === on) ? on : caps[0]?.[0];
  const next = () => { const i = caps.findIndex(c => c[0] === now); if (caps.length > 1) setOn(caps[(i + 1) % caps.length][0]); };   // 📖 a chapter that played out hands over to the next (the bar's own animation, paused on hover)
  const stage = () => {
    if (String(now).startsWith('piece:')) { const id = now.slice(6); return <Piece key={now} id={id} t={rows.find(t => t.id === id)} cat={cat} work={work} />; }
    if (now === 'ad') return <AdReel key={k} k={k} cat={cat} work={work} ads={show?.ads} />;
    if (now === 'demo') return <div className="pdr-agd" data-testid="pdr-agent"><AgentDemo kind="trading" mode="discuss" /></div>;
    if (now === 'replay') return k === 'pow' ? <PowReplay /> : k === 'pop' ? <PerpReplay kits={kits.filter(x => x.id === 'fl-liq')} /> : k === 'pob' ? <PickReplay /> : <StoryReplay />;
    if (now === 'chart') return k === 'pow' ? <TradeDemo t={trade} /> : <PerpDemo kits={kits.filter(x => x.id === 'fl-liq')} />;
    if (now === 'viral') return <ViralReel cat={cat} work={work} />;
    if (now === 'live') return <LiveGame />;
    if (now === 'video') return <VideoFilm />;
    if (now === 'image') return <ImageFilm />;
    if (now === 'parlay') return <ParlayReplay />;
    if (now === 'reviews') return <ReviewReel key={k} rows={show?.reviews?.[k]} />;
    if (now === 'books') return <BooksDemo b={show?.books} />;
    return <p className="dbt-none pdr-wait">Opening it…</p>;
  };
  const pick = x => { if (x && PROOFS[x]) { setK(x); setOn(''); } }; const kitsNow = kitLine(show?.fresh);
  return <div className={`pdr is-${k}`} data-testid="pdr"><ProofBrief k={k} onPick={pick} />
    <section className="pdr-main" key={k}>
      <header className="pdr-head"><b>{p.full}</b><span className="pdr-line">{p.line}</span>{k === 'pos' && counts ? <small className="pdr-count m-num" data-tip="Free to use, counted live from the library" data-testid="pdr-count">{K(counts.models)} models · {K(counts.hdris)} real places · {K(counts.textures)} surfaces</small> : null}</header>
      <div className="pdr-fit"><div className="pdr-stage" data-testid="pdr-stage">{stage()}<button type="button" className="pdr-full" onClick={e => toggleFull(e.currentTarget.parentElement)} aria-label="Full screen" data-tip="Full screen (Esc to leave)" data-testid="pdr-full">⤢</button></div></div>
      {caps.length > 1 ? <nav className="pdr-chaps" role="tablist" aria-label={`What ${p.t} can do`}>{caps.map(([id, ic, t, say, thumb, kind], i) => <button key={id} type="button" role="tab" aria-selected={now === id} className={now === id ? 'is-on' : ''} style={{ '--i': i }} onClick={() => setOn(id)} data-tip={say} data-testid={`pdr-cap-${id.replace('piece:', '')}`}>
        <i className="pdr-chap-bar" aria-hidden="true">{now === id ? <u style={{ '--dur': id === 'ad' ? '16s' : '10s' }} onAnimationEnd={next} /> : null}</i>
        <span className="pdr-chap-t">{thumb ? <img src={thumb} alt="" loading="lazy" /> : <Ic3 e={ic} size="18px" />}<b>{t}</b>{kind ? <small className={`is-${kind}`}>{KIND_WORD[kind] || 'SITE'}</small> : null}</span></button>)}</nav> : null}
      {kitsNow ? <p className="pdr-kits m-num" data-testid="pdr-kits-line">{kitsNow}</p> : null}
      <ShowStart key={k} k={k} p={p} seed={String(now).startsWith('piece:') ? rows.find(t => `piece:${t.id}` === now) || null : null} cost={cost} costTip={p.cmd ? priceTip(prices?.[k]) : ''} starters={starters} onMake={onMake} onCommand={onCommand} onOpen={onOpen} />
    </section></div>;
}
