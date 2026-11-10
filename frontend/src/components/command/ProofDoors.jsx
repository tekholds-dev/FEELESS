import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { Ic3 } from '../../lib/icon3d';
import { AgentDemo, DemoChart } from './AgentDemo';
import { ProofSeal } from './ProofVisuals';
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
    caps: [['replay', '🎯', 'One graded pick', 'Two minds pick blind, the scoreboard grades it'], ['parlay', '🧾', 'Builds a parlay', 'Legs from different sites, one proof']] },
  poc: { ic: '📣', t: 'PoC', full: 'Proof of Content', line: 'From what people read today to a post, a cut, an image or a 3D commercial.', folders: 'pocFolders', make: 'content', go: 'Start a PoC',
    caps: [['video', '🎬', 'AI cuts a video', 'Finds real footage, cuts it, adds words, exports'], ['image', '🖼', 'AI makes an image', 'Generates it, then builds the thumbnail'], ['piece:long-road-film', '🎥', '3D commercial', 'A film made by the 3D engine'], ['replay', '📡', 'Trend to post', 'What is moving, the angle, the finished post']] },
  poe: { ic: '📒', t: 'PoEco', full: 'Proof of Eco', line: 'Its books kept true: income, costs and tax set aside, every month drawn and hashed.', folders: 'poeFolders', open: 'poe', go: 'Open PoEco',
    caps: [['books', '📒', 'Its books, drawn', 'Income against costs, month by month, from its real books']] },
};
// Every proof type also shows two real things: its own proofs graded by OSSY + G4, and the kits it builds with (kept fresh daily).
const EVERY = [['reviews', '🧑‍⚖️', 'Graded by OSSY + G4', 'Its own proofs: the five checks each reviewer made, pass or fail'], ['kits', '🧰', 'Built with', 'The kits it builds with, at the version live today']];
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
  const [at, setAt] = useState(0);
  useEffect(() => { if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined; const t = setInterval(() => { if (!document.hidden) setAt(x => (x + 1) % n); }, ms); return () => clearInterval(t); }, [n, ms]);
  return [at];
}
const Steps = ({ names, at }) => <span className="prp-dots" aria-hidden="true">{names.map((l, i) => <em key={l} className={at === i ? 'is-on' : i < at ? 'is-done' : ''}>{l}</em>)}</span>;
const Tag = ({ t }) => <span className="prp-tag">SAMPLE RUN · {t}</span>;
const POW_STEPS = [['🔎', 'Scouts and reads', 'Five sites, a picture of each', ['dexscreener', 'x.com', 'birdeye', 'solscan', 'gmgn']], ['🧠', 'Both minds decide', 'Three turns to agree on one coin and a size'], ['🛡', 'Exits set first', 'Stop −30%, take +50%, before any buy'], ['⛏', 'Buys and trims', 'Real money through the pool, pinned on the chart'], ['🏅', 'Scored on the result', 'Money and hold time count most']];
function PowReplay() {
  const [at] = useSteps(POW_STEPS.length); const [t, setT] = useState(0);
  useEffect(() => { const c = setInterval(() => { if (!document.hidden) setT(x => x + 1); }, 900); return () => clearInterval(c); }, []);
  return <div className="prp" data-testid="pdr-pow-replay"><Tag t="not a real trade" /><Steps names={['READ', 'DECIDE', 'EXITS', 'BUY', 'SCORE']} at={at} /><div className="prp-main"><DemoChart seed={5} t={t} who="A" sym="SAMPLE" calls={at >= 3} /></div>
    <div className="prp-side">{POW_STEPS.map(([ic, b, say, chips], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small>{chips && i === at ? <span className="prp-chips">{chips.map(c => <em key={c}>{c}</em>)}</span> : null}</div>)}{at === 4 ? <span className="prp-seal"><ProofSeal rank="A" tone="good" size={70} parts={[{ label: 'Result', value: 0.9 }, { label: 'Held', value: 0.8 }, { label: 'Reads', value: 0.7 }, { label: 'Exits', value: 1 }, { label: 'New', value: 0.6 }]} />Its score, from its record</span> : null}</div></div>;
}
const POP_STEPS = [['🙈', 'Each mind calls blind', 'Neither sees the other. A call needs a number behind it'], ['📖', 'The calls open', 'They disagree, and both reasons are on the record'], ['📏', 'Lines on true candles', 'Entry, stop and where its leverage dies'], ['📊', 'True price grades it', 'A practice trade runs. No real money moves']];
function PerpReplay({ kits }) {
  const lev = useMemo(() => levOf(kits), [kits]); const [at] = useSteps(POP_STEPS.length, 3800); const px = lev?.mark;
  const lines = px && at >= 2 ? [{ id: 'e', price: px, title: 'A ENTRY', color: '#45e486' }, { id: 's', price: px * 0.975, title: 'A STOP', color: '#ffd54a', dash: true }, { id: 'l', price: lev.l10, title: '10x DIES', color: '#ff8fa3', dash: true }] : [];
  const open = at >= 1;
  return <div className="prp" data-testid="pdr-perp-replay"><Tag t="sample calls on today's real candles" /><Steps names={['BLIND', 'OPEN', 'LINES', 'GRADE']} at={at} /><div className="prp-main"><div className="pdr-chart" style={{ height: '100%' }}><Suspense fallback={<Wait what="Loading true candles…" />}><PerpsChart asset={lev?.sym || 'BTC'} iv="1h" lines={lines} /></Suspense></div>
    <div className="prp-calls">{[['MIND A', 'LONG 3x', 'Funding is negative while price holds its range', 'long'], ['MIND B', 'SHORT 5x', 'Open interest rose 9% into a flat tape', 'short']].map(([who, call, why, side]) => <div key={who} className={`prp-call${open ? ` is-${side}` : ' is-sealed'}`}><b>{who}</b><strong>{open ? call : 'SEALED'}</strong><small>{open ? why : 'Waiting for the other mind'}</small></div>)}</div></div>
    <div className="prp-side">{POP_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
const POB_STEPS = [['🔎', 'Each mind searches its own sites', 'One reads injuries and form, one reads the odds'], ['🎯', 'Picks blind', 'A pick, a confidence, and the site its number came from'], ['🏟', 'The game plays', 'Live numbers from the scoreboard'], ['✅', 'The scoreboard grades it', 'Never the mind that made the pick']];
function PickReplay() {
  const [at] = useSteps(POB_STEPS.length, 3600);
  return <div className="prp" data-testid="pdr-pick-replay"><Tag t="made-up game" /><Steps names={['READ', 'PICK', 'LIVE', 'GRADE']} at={at} /><div className="prp-main"><div className="prp-game"><div className="prp-teams"><b>HOME</b><em className="m-num">{at >= 2 ? (at >= 3 ? '112 – 104' : '58 – 55') : 'vs'}</em><b>AWAY</b></div>
    <div className="prp-minds">{[['MIND A · FORM', 'Home wins', 72, 'Away star out, says the injury report'], ['MIND B · ODDS', 'Home −4.5', 61, 'The line moved two points since noon']].map(([who, p, c, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{at >= 1 ? p : 'Reading…'}</strong><u><s style={{ transform: `scaleX(${at >= 1 ? c / 100 : 0})` }} /></u><small>{at >= 1 ? `${c}% · ${why}` : 'Its own sites, its own search'}</small></div>)}</div>{at === 3 ? <span className="prp-grade">BOTH RIGHT · GRADED BY THE FINAL SCORE</span> : null}</div></div>
    <div className="prp-side">{POB_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
const POC_STEPS = [['📡', 'Reads what is moving', 'Five trend sources, a picture of each'], ['💡', 'Each mind pitches an angle', 'Two different takes on the same story'], ['✍', 'Writes the finished post', 'In your voice, ready to use. It never posts by itself']];
function StoryReplay() {
  const [at] = useSteps(POC_STEPS.length, 4200);
  return <div className="prp" data-testid="pdr-story-replay"><Tag t="sample topics" /><Steps names={['TRENDS', 'ANGLES', 'POST']} at={at} /><div className="prp-main">
    {at === 0 ? <div className="prp-trend"><h4>RISING RIGHT NOW</h4><ul>{[['New phone launch', 0.92, '+340%'], ['Playoff race', 0.71, '+120%'], ['Solana ETF', 0.55, '+64%'], ['Coffee prices', 0.3, '+22%']].map(([l, v, g]) => <li key={l}><span>{l}</span><b className="m-num">{g}</b><u><s style={{ transform: `scaleX(${v})` }} /></u></li>)}</ul></div> : null}
    {at === 1 ? <div className="prp-game"><div className="prp-minds">{[['MIND A · THE ARGUMENT', 'Nobody needs this phone, and everyone will buy it', 'Replies are 3 to 1 against'], ['MIND B · BEFORE THE PEAK', 'The one feature reviewers skipped', 'Searches for it doubled today']].map(([who, p, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{p}</strong><small>{why}</small></div>)}</div></div> : null}
    {at === 2 ? <div className="prp-post"><article><header><i aria-hidden="true" />Your account</header><p>Every review skipped the one thing you'll use daily.{'\n'}I spent a week with it. Three things they missed 🧵</p><small>READY TO POST · ALSO A 40 SECOND SCRIPT AND A THUMBNAIL</small></article></div> : null}</div>
    <div className="prp-side">{POC_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
// 📊 Not every PoStatic is a 3D site (owner 2026-11-07: "a mix, not just games and repeated landing pages"). Example pages of the kinds the Build tiles start, labelled as examples with sample data.
export const EXAMPLE_PIECES = [
  { id: 'pulse-dash', kind: 'dash', name: 'Pulse', what: 'White dashboard, Day and Night', ask: 'A clean white analytics dashboard with a Day / Night switch and animated charts', things: ['stat cards', 'line chart', 'donut', 'bars'], src: '/showcase/pos/pulse-dash.html', thumb: '/showcase/pos/pulse-dash.jpg' },
  { id: 'tape-desk', kind: 'chart', name: 'Tape desk', what: 'Live chart desk', ask: 'A trading desk page: candles that tick, an order book and a trade tape with whales marked', things: ['candles', 'order book', 'trade tape'], src: '/showcase/pos/tape-desk.html', thumb: '/showcase/pos/tape-desk.jpg' },
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
      {at >= 2 ? <div className="flm-row"><small className="m-label">{t?.src ? 'IT WRITES IT' : 'CODE PLACES IT'}</small><span className="flm-build"><i /><i /><i /></span><small>{t?.src ? 'Layout, charts, motion, Day and Night' : 'Real models, a real place, light, camera, finish'}</small></div> : null}{err ? <p className="dbt-none">{err}</p> : at >= 3 && !page ? <p className="dbt-none">Opening it…</p> : null}</div></div>
    {ready ? <span className="flm-tag">{t?.src ? 'EXAMPLE PAGE · SAMPLE DATA' : t?.kind === 'game' ? 'BUILT BY AN AGENT · ITS BOT IS PLAYING' : 'BUILT BY AN AGENT · RUNNING LIVE'}</span> : null}</div>;
}
// 🎬 AI cuts a video: real public domain NASA footage, on a timeline, words on top, exported.
const CLIPS = [['Launch', 'https://images-assets.nasa.gov/video/KSC-20240525-MH-RKL01-0001-Rocket_Lab_PREFIRE_1_Launch_1080p-M6988/KSC-20240525-MH-RKL01-0001-Rocket_Lab_PREFIRE_1_Launch_1080p-M6988~mobile.mp4#t=16', 'WE LEFT'], ['Earth', 'https://images-assets.nasa.gov/video/Earth%20Views%20from%20the%20International%20Space%20Station/Earth%20Views%20from%20the%20International%20Space%20Station~mobile.mp4#t=8', 'AT DAWN'], ['Liftoff', 'https://images-assets.nasa.gov/video/KSC-20230507-MH-RLS01-TROPICS_Rocket_Launch-Rocket_Lab-WON_3330130/KSC-20230507-MH-RLS01-TROPICS_Rocket_Launch-Rocket_Lab-WON_3330130~mobile.mp4#t=20', 'AND KEPT GOING']];
const CUT_LOG = ['Reads your ask: 15 seconds, big words', 'Searches NASA for launch footage', 'Keeps 3 clips, public domain', 'Opens on the payoff, cuts every 4 seconds', 'Adds words people can read on a phone', 'Exports an MP4 on your machine'];
function VideoFilm() {
  const [at] = useSteps(CUT_LOG.length * 2, 2600); const step = Math.floor(at / 2); const on = Math.min(2, Math.max(0, step >= 3 ? at - 6 : 0)) % 3;
  return <div className="prp is-wide" data-testid="pdr-video"><Tag t="real NASA footage, public domain" /><div className="prp-main flm-mon">{CLIPS.map(([n, src], i) => (i === on ? <video key={n} src={src} autoPlay muted loop playsInline preload="metadata" /> : null))}{step >= 4 ? <p className="flm-word" key={on}>{CLIPS[on][2]}</p> : null}{step >= 5 ? <span className="flm-done">launch-cut.mp4 · 15 s · ready</span> : null}
    <div className="flm-time" aria-hidden="true"><span>{CLIPS.map(([n], i) => <i key={n} className={`${step >= i + 1 ? 'is-in' : ''}${i === on && step >= 3 ? ' is-on' : ''}`}>{step >= i + 1 ? n : ''}</i>)}</span><span className="is-words">{step >= 4 ? CLIPS.map(([n, , w]) => <b key={n}>{w}</b>) : null}</span><u style={{ transform: `translateX(${step >= 3 ? ((at % 12) / 12) * 100 : 0}%)` }} /></div></div>
    <ol className="flm-log prp-side">{CUT_LOG.map((l, i) => <li key={l} className={i === step ? 'is-on' : i < step ? 'is-done' : ''}>{l}</li>)}</ol></div>;
}
// 🖼 AI makes an image: a real generated picture comes into focus, then the thumbnail is built on it, layer by layer.
const IMG_LOG = ['Writes the prompt from your ask', 'Generates it with a free image model', 'Crops for a phone screen', 'Adds 3 big words', 'Adds the accent', 'Saves 3 versions to test'];
function ImageFilm() {
  const [at] = useSteps(IMG_LOG.length, 2600); const pics = ['/showcase/poc/gen1.jpg', '/showcase/poc/gen2.jpg', '/showcase/night-run.jpg'];
  return <div className="prp is-wide" data-testid="pdr-image"><Tag t="a real generated picture" /><div className="prp-main flm-art"><img src={pics[0]} alt="" className={at === 0 ? 'is-blur' : at === 1 ? 'is-soft' : at >= 2 ? 'is-crop' : ''} />{at === 0 ? <p className="flm-prompt">dramatic rocket launch at dusk, cinematic, wide shot</p> : null}{at >= 3 ? <h4 className="flm-big">We <em>left</em> at dusk</h4> : null}{at >= 4 ? <b className="flm-pill">NEW</b> : null}{at >= 5 ? <span className="flm-vers">{pics.map(p => <img key={p} src={p} alt="" loading="lazy" />)}</span> : null}</div>
    <ol className="flm-log prp-side">{IMG_LOG.map((l, i) => <li key={l} className={i === at ? 'is-on' : i < at ? 'is-done' : ''}>{l}</li>)}</ol></div>;
}
const PARLAY_STEPS = [['🔎', 'Reads a different site per leg', 'Injuries on one, lines on another'], ['🧾', 'Adds each leg with its reason', 'A number from a site, or no leg'], ['✖', 'Works out the real odds', 'Every leg has to hit'], ['✅', 'Grades leg by leg', 'From the final scores']];
const LEGS = [['Home wins', 72, 'rotowire'], ['Over 214.5', 58, 'oddsshark'], ['Star 25+ points', 64, 'teamrankings']];
function ParlayReplay() {
  const [at] = useSteps(PARLAY_STEPS.length, 3400); const n = Math.min(LEGS.length, at + 1); const all = LEGS.reduce((a, l) => a * (l[1] / 100), 1);
  return <div className="prp" data-testid="pdr-parlay"><Tag t="made-up games" /><Steps names={['READ', 'LEGS', 'ODDS', 'GRADE']} at={at} /><div className="prp-main"><div className="prp-game"><div className="prp-minds is-legs">{LEGS.slice(0, n).map(([p, c, site]) => <div key={p} className="prp-mind"><b>{site}.com</b><strong>{p}{at === 3 ? ' ✓' : ''}</strong><u><s style={{ transform: `scaleX(${c / 100})` }} /></u><small>{c}% by its read</small></div>)}</div>{at >= 2 ? <span className="prp-grade">ALL THREE: {Math.round(all * 100)}%{at === 3 ? ' · GRADED BY THE SCORES' : ''}</span> : null}</div></div><div className="prp-side">{PARLAY_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
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
export function KitWall({ kits, fresh, kind }) {
  const v = Object.fromEntries((fresh?.kits || []).map(x => [x.kit, x])); const rows = (kits || []).filter(x => (x.kinds || []).includes(kind));
  if (!rows.length) return <p className="dbt-none">No kit is set for this kind yet.</p>;
  return <div className="pkw" data-testid="pdr-kits"><p className="pkw-sum m-num">{rows.length} kits · {rows.filter(x => v[x.id]?.prev).length} moved up · checked daily, smoke-tested before use</p>
    <ul>{rows.map((x, i) => { const f = v[x.id]; return <li key={x.id} className={f?.prev ? 'is-moved' : ''} style={{ '--i': i }} data-tip={`${x.what} · ${x.license}${f ? ` · ${f.pkg}@${f.v}` : ' · read as a guide'}`} data-testid={`pdr-kit-${x.id}`}>
      <b>{x.name}</b><small>{x.what}</small><em className="m-num">{f ? <>{f.prev ? <><s>{f.prev}</s> → </> : null}v{f.v}</> : 'guide'}</em></li>; })}</ul></div>;
}
// 📒 Its books, drawn: income and costs per month as bars, the net on top. Real books only.
export function BooksDemo({ b }) {
  if (!b?.months?.length) return <p className="dbt-none" data-testid="pdr-no-books">No books yet. Its first PoEco draws here.</p>;
  const top = Math.max(1, ...b.months.flatMap(m => [m.income || 0, m.costs || 0])); const usd = n => `$${Math.round(n || 0).toLocaleString()}`;
  return <div className="pbk" data-testid="pdr-books"><header><b>{b.topic || 'Its books'}</b><span className="m-num">IN {usd(b.income)} · OUT {usd(b.costs)} · NET <i>{usd(b.net)}</i> · {b.margin ?? '—'}% margin</span></header>
    <ol className="pbk-bars">{b.months.map((m, i) => <li key={m.month} style={{ '--i': i }} data-tip={`${m.month}: in ${usd(m.income)}, out ${usd(m.costs)}, net ${usd(m.net)}`}><span><u className="is-in" style={{ transform: `scaleY(${(m.income || 0) / top})` }} /><u className="is-out" style={{ transform: `scaleY(${(m.costs || 0) / top})` }} /></span><small className="m-num">{m.month}</small><b className="m-num">{usd(m.net)}</b></li>)}</ol>
    {b.taxSetAside != null ? <p className="pbk-tax m-num">TAX SET ASIDE {usd(b.taxSetAside)}</p> : null}</div>;
}
export function ProofDoors({ cat, d, work, onCommand, onMake, onOpen, kindFirst = 'pos' }) {
  const [k, setK] = useState(kindFirst); const [counts, setCounts] = useState(null); const [kits, setKits] = useState([]); const [trade, setTrade] = useState(null); const [on, setOn] = useState(''); const [show, setShow] = useState(null); const p = PROOFS[k];
  useEffect(() => { let live = true; Promise.resolve().then(() => Promise.all([work(cat.id, { op: 'tools_show' }).catch(() => null), work(cat.id, { op: 'kit_list' }).catch(() => null), work(cat.id, { op: 'demo_trade' }).catch(() => null), work(cat.id, { op: 'showcase' }).catch(() => null)])).then(([a, b, t, sc]) => { if (!live) return; setCounts(a); setKits(b?.kits || []); setTrade(t?.trade || null); setShow(sc); }); return () => { live = false; }; }, [cat.id, work]);
  const rows = mixPieces([...(counts?.templates || []).filter(t => t.kind !== 'film'), ...(counts ? EXAMPLE_PIECES : [])]); const pieces = k === 'pos' ? rows : []; const caps = [...(pieces.length ? pieces.map(t => [`piece:${t.id}`, null, t.name, t.what, t.thumb, t.kind]) : p.caps).filter(c => c[0] !== 'chart' || k !== 'pow' || trade?.pair?.pairAddress), ...EVERY]; const now = caps.some(c => c[0] === on) ? on : caps[0]?.[0];
  const stage = () => {
    if (String(now).startsWith('piece:')) { const id = now.slice(6); return <Piece key={now} id={id} t={rows.find(t => t.id === id)} cat={cat} work={work} />; }
    if (now === 'demo') return <div className="pdr-agd" data-testid="pdr-agent"><AgentDemo kind="trading" mode="discuss" /></div>;
    if (now === 'replay') return k === 'pow' ? <PowReplay /> : k === 'pop' ? <PerpReplay kits={kits.filter(x => x.id === 'fl-liq')} /> : k === 'pob' ? <PickReplay /> : <StoryReplay />;
    if (now === 'chart') return k === 'pow' ? <TradeDemo t={trade} /> : <PerpDemo kits={kits.filter(x => x.id === 'fl-liq')} />;
    if (now === 'video') return <VideoFilm />;
    if (now === 'image') return <ImageFilm />;
    if (now === 'parlay') return <ParlayReplay />;
    if (now === 'reviews') return <ReviewReel key={k} rows={show?.reviews?.[k]} />;
    if (now === 'kits') return <KitWall kits={show?.kits} fresh={show?.fresh} kind={k} />;
    if (now === 'books') return <BooksDemo b={show?.books} />;
    return <p className="dbt-none pdr-wait">Opening it…</p>;
  };
  return <div className={`pdr is-${k}`} data-testid="pdr">
    <nav className="pdr-doors" role="tablist" aria-label="Proof types">{Object.entries(PROOFS).map(([x, v]) => <button key={x} type="button" role="tab" aria-selected={k === x} className={k === x ? 'is-on' : ''} onClick={() => { setK(x); setOn(''); }} data-tip={v.full} data-testid={`pdr-${x}`}><Ic3 e={v.ic} size="24px" /><b>{v.t}</b></button>)}</nav>
    <section className="pdr-main" key={k}>
      <aside className="pdr-rail"><p className="pdr-line">{p.line}</p><ul className="pdr-caps" role="tablist" aria-label={`What ${p.t} can do`}>{caps.map(([id, ic, t, say, thumb, kind], i) => <li key={id} style={{ '--i': i }}><button type="button" role="tab" aria-selected={now === id} className={`${now === id ? 'is-on' : ''}${thumb ? ' has-thumb' : ''}`} onClick={() => setOn(id)} data-tip={say} data-testid={`pdr-cap-${id.replace('piece:', '')}`}>{thumb ? <img src={thumb} alt="" loading="lazy" /> : <Ic3 e={ic} size="22px" />}<b>{t}</b>{kind ? <small className={`is-${kind}`}>{KIND_WORD[kind] || 'SITE'}</small> : null}</button></li>)}</ul>
        {k === 'pos' && counts ? <p className="pdr-count m-num" data-tip="Free to use, counted live from the library" data-testid="pdr-count">{K(counts.models)} models · {K(counts.hdris)} real places · {K(counts.textures)} surfaces</p> : null}
        <button type="button" className="m-btn m-go pdr-go" onClick={() => (p.open ? onOpen?.(p.open) : p.make ? onMake?.(p.make) : onCommand?.(p.cmd))} data-tip={p.open ? 'Opens its window' : p.make ? 'Makes its folder' : `Tells it: ${p.cmd}`} data-testid="pdr-go">{p.go}</button></aside>
      <div className="pdr-stage" data-testid="pdr-stage">{stage()}</div>
    </section></div>;
}
