import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { ProofTools } from './ProofTools';
import { Ic3 } from '../../lib/icon3d';
import { KitPick } from './KitPick';
import { ProofCard } from './ProofGallery';
import { AgentDemo, DemoChart } from './AgentDemo';
import { ProofSeal } from './ProofVisuals';
const TrenchChart = lazy(() => import('../terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
const PerpsChart = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));
const VideoEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.VideoEditor })));
const ImageEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.ImageEditor })));

// 🎬 Proofs (owner 2026-11-07: "a cool display of how complex and worthy each proof is… the user clicks the different capabilities and sees a preview of some of the best work, not play around not knowing how"). One stage that fits the window, finished work playing in it, and every capability one tap away. Every model gets the same tools; a stronger mind makes better work with them.
const PROOFS = {
  pos: { ic: '💻', t: 'PoStatic', full: 'Proof of Static', line: 'Real sites and real games, built from one sentence, checked in a real browser.', folders: 'psFolders', gallery: 'PoStatic', make: 'build', go: 'Start a PoStatic', caps: [] },
  pow: { ic: '⛏', t: 'PoW', full: 'Proof of Work', line: 'A real trade, and everything it read before it.', folders: 'powFolders', gallery: 'PoW', cmd: 'file a PoW', go: 'Start a PoW',
    caps: [['replay', '⛏', 'One whole trade', 'From scouting a coin to the score it earns'], ['demo', '🧠', 'Two minds at work', 'Both windows, recorded on real sites'], ['chart', '📈', 'Its real chart', 'Its best real trade on the real chart'], ['tools', '🛡', 'Live tools', 'Exit ladder and the numbers it reads']] },
  pop: { ic: '📉', t: 'PoP', full: 'Proof of Perps', line: 'Both minds call a market blind, on paper, with a number behind every call.', folders: 'popFolders', gallery: 'PoP', cmd: 'file a perp', go: 'Start a PoP',
    caps: [['replay', '🙈', 'Blind calls', 'Sealed, opened, then put on the true chart'], ['chart', '💀', 'Where leverage dies', 'True candles with live liquidation lines'], ['tools', '📊', 'Live tools', 'Funding, open interest and the maths']] },
  pob: { ic: '🎲', t: 'PoB', full: 'Proof of Bids', line: 'Picks on any game or market, graded by the scoreboard and never by the mind.', folders: 'pobFolders', gallery: 'PoB', cmd: 'file a pob best NFL picks', go: 'Start a PoB',
    caps: [['replay', '🎯', 'One graded pick', 'Two minds pick blind, the scoreboard grades it'], ['tools', '🏟', 'Game room', 'Every game with live numbers. Build a parlay']] },
  poc: { ic: '📣', t: 'PoC', full: 'Proof of Content', line: 'From what people read today to a post, a cut, a thumbnail or a 3D commercial.', folders: 'pocFolders', gallery: 'PoC', make: 'content', go: 'Start a PoC',
    caps: [['piece:long-road-film', '🎥', '3D commercial', 'A film made by the 3D engine'], ['replay', '📡', 'Trend to post', 'What is moving, the angle, the finished post'], ['thumbs', '🖼', 'Thumbnails', 'Made from its own 3D scenes'], ['video', '🎬', 'Video editor', 'Cuts, text and music, an MP4 on your machine'], ['image', '🖼', 'Image editor', 'Layers and text. The agent can start it'], ['tools', '🧾', 'Live tools', 'What it watches and drafts']] },
};
const SHARED = [['best', '🏆', 'Your best', 'The best one your agents have filed'], ['kits', '🧰', 'Its kits', 'Pick what it brings to this proof']];
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
// 🎞 A proof's own replay: a sample run on its own tools, one step at a time. Tap a step to hold it. Labelled as a sample on the stage.
function useSteps(n, ms = 3400) {
  const [at, setAt] = useState(0); const [held, setHeld] = useState(false);
  useEffect(() => { if (held || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined; const t = setInterval(() => { if (!document.hidden) setAt(x => (x + 1) % n); }, ms); return () => clearInterval(t); }, [n, ms, held]);
  return [at, i => { setAt(i); setHeld(true); }];
}
const Steps = ({ names, at, pick }) => <span className="prp-dots" role="group" aria-label="Steps">{names.map((l, i) => <button key={l} type="button" className={at === i ? 'is-on' : ''} aria-pressed={at === i} onClick={() => pick(i)} data-tip={`Hold on: ${l}`} data-testid={`prp-step-${i}`}>{l}</button>)}</span>;
const Tag = ({ t }) => <span className="prp-tag">SAMPLE RUN · {t}</span>;
const POW_STEPS = [['🔎', 'Scouts and reads', 'Five sites, a picture of each', ['dexscreener', 'x.com', 'birdeye', 'solscan', 'gmgn']], ['🧠', 'Both minds decide', 'Three turns to agree on one coin and a size'], ['🛡', 'Exits set first', 'Stop −30%, take +50%, before any buy'], ['⛏', 'Buys and trims', 'Real money through the pool, pinned on the chart'], ['🏅', 'Scored on the result', 'Money and hold time count most']];
function PowReplay() {
  const [at, pick] = useSteps(POW_STEPS.length); const [t, setT] = useState(0);
  useEffect(() => { const c = setInterval(() => { if (!document.hidden) setT(x => x + 1); }, 900); return () => clearInterval(c); }, []);
  return <div className="prp" data-testid="pdr-pow-replay"><Tag t="not a real trade" /><Steps names={['READ', 'DECIDE', 'EXITS', 'BUY', 'SCORE']} at={at} pick={pick} /><div className="prp-main"><DemoChart seed={5} t={t} who="A" sym="SAMPLE" calls={at >= 3} /></div>
    <div className="prp-side">{POW_STEPS.map(([ic, b, say, chips], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small>{chips && i === at ? <span className="prp-chips">{chips.map(c => <em key={c}>{c}</em>)}</span> : null}</div>)}{at === 4 ? <span className="prp-seal"><ProofSeal rank="A" tone="good" size={70} parts={[{ label: 'Result', value: 0.9 }, { label: 'Held', value: 0.8 }, { label: 'Reads', value: 0.7 }, { label: 'Exits', value: 1 }, { label: 'New', value: 0.6 }]} />Its score, from its record</span> : null}</div></div>;
}
const POP_STEPS = [['🙈', 'Each mind calls blind', 'Neither sees the other. A call needs a number behind it'], ['📖', 'The calls open', 'They disagree, and both reasons are on the record'], ['📏', 'Lines on true candles', 'Entry, stop and where its leverage dies'], ['📊', 'True price grades it', 'A practice trade runs. No real money moves']];
function PerpReplay({ kits }) {
  const lev = useMemo(() => levOf(kits), [kits]); const [at, pick] = useSteps(POP_STEPS.length, 3800); const px = lev?.mark;
  const lines = px && at >= 2 ? [{ id: 'e', price: px, title: 'A ENTRY', color: '#45e486' }, { id: 's', price: px * 0.975, title: 'A STOP', color: '#ffd54a', dash: true }, { id: 'l', price: lev.l10, title: '10x DIES', color: '#ff8fa3', dash: true }] : [];
  const open = at >= 1;
  return <div className="prp" data-testid="pdr-perp-replay"><Tag t="sample calls on today's real candles" /><Steps names={['BLIND', 'OPEN', 'LINES', 'GRADE']} at={at} pick={pick} /><div className="prp-main"><div className="pdr-chart" style={{ height: '100%' }}><Suspense fallback={<Wait what="Loading true candles…" />}><PerpsChart asset={lev?.sym || 'BTC'} iv="1h" lines={lines} /></Suspense></div>
    <div className="prp-calls">{[['MIND A', 'LONG 3x', 'Funding is negative while price holds its range', 'long'], ['MIND B', 'SHORT 5x', 'Open interest rose 9% into a flat tape', 'short']].map(([who, call, why, side]) => <div key={who} className={`prp-call${open ? ` is-${side}` : ' is-sealed'}`}><b>{who}</b><strong>{open ? call : 'SEALED'}</strong><small>{open ? why : 'Waiting for the other mind'}</small></div>)}</div></div>
    <div className="prp-side">{POP_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
const POB_STEPS = [['🔎', 'Each mind searches its own sites', 'One reads injuries and form, one reads the odds'], ['🎯', 'Picks blind', 'A pick, a confidence, and the site its number came from'], ['🏟', 'The game plays', 'Live numbers from the scoreboard'], ['✅', 'The scoreboard grades it', 'Never the mind that made the pick']];
function PickReplay() {
  const [at, pick] = useSteps(POB_STEPS.length, 3600);
  return <div className="prp" data-testid="pdr-pick-replay"><Tag t="made-up game" /><Steps names={['READ', 'PICK', 'LIVE', 'GRADE']} at={at} pick={pick} /><div className="prp-main"><div className="prp-game"><div className="prp-teams"><b>HOME</b><em className="m-num">{at >= 2 ? (at >= 3 ? '112 – 104' : '58 – 55') : 'vs'}</em><b>AWAY</b></div>
    <div className="prp-minds">{[['MIND A · FORM', 'Home wins', 72, 'Away star out, says the injury report'], ['MIND B · ODDS', 'Home −4.5', 61, 'The line moved two points since noon']].map(([who, p, c, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{at >= 1 ? p : 'Reading…'}</strong><u><s style={{ transform: `scaleX(${at >= 1 ? c / 100 : 0})` }} /></u><small>{at >= 1 ? `${c}% · ${why}` : 'Its own sites, its own search'}</small></div>)}</div>{at === 3 ? <span className="prp-grade">BOTH RIGHT · GRADED BY THE FINAL SCORE</span> : null}</div></div>
    <div className="prp-side">{POB_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
const POC_STEPS = [['📡', 'Reads what is moving', 'Five trend sources, a picture of each'], ['💡', 'Each mind pitches an angle', 'Two different takes on the same story'], ['✍', 'Writes the finished post', 'In your voice, ready to use. It never posts by itself']];
function StoryReplay() {
  const [at, pick] = useSteps(POC_STEPS.length, 4200);
  return <div className="prp" data-testid="pdr-story-replay"><Tag t="sample topics" /><Steps names={['TRENDS', 'ANGLES', 'POST']} at={at} pick={pick} /><div className="prp-main">
    {at === 0 ? <div className="prp-trend"><h4>RISING RIGHT NOW</h4><ul>{[['New phone launch', 0.92, '+340%'], ['Playoff race', 0.71, '+120%'], ['Solana ETF', 0.55, '+64%'], ['Coffee prices', 0.3, '+22%']].map(([l, v, g]) => <li key={l}><span>{l}</span><b className="m-num">{g}</b><u><s style={{ transform: `scaleX(${v})` }} /></u></li>)}</ul></div> : null}
    {at === 1 ? <div className="prp-game"><div className="prp-minds">{[['MIND A · THE ARGUMENT', 'Nobody needs this phone, and everyone will buy it', 'Replies are 3 to 1 against'], ['MIND B · BEFORE THE PEAK', 'The one feature reviewers skipped', 'Searches for it doubled today']].map(([who, p, why]) => <div key={who} className="prp-mind"><b>{who}</b><strong>{p}</strong><small>{why}</small></div>)}</div></div> : null}
    {at === 2 ? <div className="prp-post"><article><header><i aria-hidden="true" />Your account</header><p>Every review skipped the one thing you'll use daily.{'\n'}I spent a week with it. Three things they missed 🧵</p><small>READY TO POST · ALSO A 40 SECOND SCRIPT AND A THUMBNAIL</small></article></div> : null}</div>
    <div className="prp-side">{POC_STEPS.map(([ic, b, say], i) => <div key={b} className={`prp-step${i === at ? ' is-on' : i < at ? ' is-done' : ''}`}><i aria-hidden="true"><Ic3 e={ic} /></i><b>{b}</b><small>{say}</small></div>)}</div></div>;
}
const Thumbs = () => <div className="prp-thumbs" data-testid="pdr-thumbs"><span className="prp-tag">SAMPLE · LAYERS OVER ITS OWN 3D SCENES</span>{[['long-road', 'I rode it', 'for 900 miles', '12:04'], ['night-run', 'This game', 'was built by AI', '8:31'], ['silver-hour', 'Why it costs', '$4,000', '6:47']].map(([id, a, b, len]) => <figure key={id} className="prp-thumb"><img src={`/showcase/${id}.jpg`} alt="" loading="lazy" /><figcaption>{a} <em>{b}</em></figcaption><b className="m-num">{len}</b></figure>)}</div>;
const Editor = ({ mode, cat, work }) => <div className="pdr-editor" data-testid="pdr-editor"><Suspense fallback={<Wait what="Opening the editor…" />}>{mode === 'video' ? <VideoEditor cat={cat} work={work} /> : <ImageEditor cat={cat} work={work} />}</Suspense></div>;
// 🎬 One finished piece from the engine, running for real. Only one is ever alive, so a preview never costs more than itself.
function Piece({ id, cat, work }) {
  const [page, setPage] = useState(''); const [err, setErr] = useState('');
  useEffect(() => { let on = true; setPage(''); setErr(''); Promise.resolve().then(() => work(cat.id, { op: 'tools_showcase', job: id })).then(j => on && setPage(j.preview || '')).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id, work, id]);
  return page ? <iframe className="pdr-frame" title="Finished work" srcDoc={page} sandbox="allow-scripts" data-testid="pdr-piece-frame" /> : <p className="dbt-none pdr-wait">{err || 'Opening it…'}</p>;
}
export function ProofDoors({ cat, d, work, onCommand, onMake, kindFirst = 'pos' }) {
  const [k, setK] = useState(kindFirst); const [counts, setCounts] = useState(null); const [kits, setKits] = useState([]); const [gallery, setGallery] = useState([]); const [trade, setTrade] = useState(null); const [on, setOn] = useState(''); const p = PROOFS[k];
  useEffect(() => { let live = true; Promise.resolve().then(() => Promise.all([work(cat.id, { op: 'tools_show' }).catch(() => null), work(cat.id, { op: 'kit_list' }).catch(() => null), work(cat.id, { op: 'demo_gallery' }).catch(() => null), work(cat.id, { op: 'demo_trade' }).catch(() => null)])).then(([a, b, c, t]) => { if (!live) return; setCounts(a); setKits(b?.kits || []); setGallery(c?.kinds || []); setTrade(t?.trade || null); }); return () => { live = false; }; }, [cat.id, work]);
  const pieces = k === 'pos' ? (counts?.templates || []).filter(t => t.kind !== 'film') : []; const caps = pieces.length ? pieces.map(t => [`piece:${t.id}`, null, t.name, t.what, t.thumb, t.kind]) : p.caps; const all = [...caps, ...SHARED]; const now = all.some(c => c[0] === on) ? on : all[0]?.[0];
  const best = (gallery.find(g => g.kind === p.gallery)?.cards || [])[0];
  const stage = () => {
    if (String(now).startsWith('piece:')) return <Piece key={now} id={now.slice(6)} cat={cat} work={work} />;
    if (now === 'demo') return <div className="pdr-agd" data-testid="pdr-agent"><AgentDemo kind="trading" mode="discuss" /></div>;
    if (now === 'replay') return k === 'pow' ? <PowReplay /> : k === 'pop' ? <PerpReplay kits={kits.filter(x => x.id === 'fl-liq')} /> : k === 'pob' ? <PickReplay /> : <StoryReplay />;
    if (now === 'thumbs') return <Thumbs />;
    if (now === 'chart') return k === 'pow' ? <TradeDemo t={trade} /> : <PerpDemo kits={kits.filter(x => x.id === 'fl-liq')} />;
    if (now === 'video' || now === 'image') return <Editor mode={now} cat={cat} work={work} />;
    if (now === 'tools') return <div className="pdr-panel"><ProofTools key={k} kind={k === 'pob' ? 'bids' : k === 'poc' ? 'content' : k} onCommand={onCommand} rail={false} /></div>;
    if (now === 'best') return <div className="pdr-panel">{best ? <ProofCard c={best} i={0} work={work} cat={cat} /> : <p className="dbt-none pdr-none" data-testid="pdr-no-proof">Your agents have not filed a {p.t} yet. Your best one lands here.</p>}</div>;
    if (now === 'kits') return <div className="pdr-panel"><KitPick cat={cat} work={work} kind={k} /></div>;
    return <p className="dbt-none pdr-wait">Opening it…</p>;
  };
  return <div className={`pdr is-${k}`} data-testid="pdr">
    <nav className="pdr-doors" role="tablist" aria-label="Proof types">{Object.entries(PROOFS).map(([x, v]) => <button key={x} type="button" role="tab" aria-selected={k === x} className={k === x ? 'is-on' : ''} onClick={() => { setK(x); setOn(''); }} data-tip={v.full} data-testid={`pdr-${x}`}><Ic3 e={v.ic} size="24px" /><b>{v.t}</b><small className="m-num">{(d?.[v.folders] || []).length} filed</small></button>)}</nav>
    <section className="pdr-main" key={k}>
      <div className="pdr-show"><div className="pdr-stage" data-testid="pdr-stage">{stage()}</div>
        <ul className="pdr-caps" role="tablist" aria-label={`What ${p.t} can do`}>{all.map(([id, ic, t, say, thumb, kind], i) => <li key={id} style={{ '--i': i }}><button type="button" role="tab" aria-selected={now === id} className={`${now === id ? 'is-on' : ''}${thumb ? ' has-thumb' : ''}`} onClick={() => setOn(id)} data-tip={say} data-testid={`pdr-cap-${id.replace('piece:', '')}`}>{thumb ? <img src={thumb} alt="" loading="lazy" /> : <Ic3 e={ic} size="22px" />}<b>{t}</b>{kind ? <small className={`is-${kind}`}>{kind === 'game' ? 'GAME' : 'SITE'}</small> : null}</button></li>)}</ul></div>
      <aside className="pdr-side"><small className="m-label">{p.full.toUpperCase()}</small><h3>{p.t}</h3><p>{p.line}</p>
        <button type="button" className="m-btn m-go pdr-go" onClick={() => (p.make ? onMake?.(p.make) : onCommand?.(p.cmd))} data-tip={p.make ? 'Makes its folder' : `Tells it: ${p.cmd}`} data-testid="pdr-go">{p.go}</button>
        {k === 'pos' ? <div className="pdr-nums">{[['MODELS', counts?.models], ['REAL PLACES', counts?.hdris], ['SURFACES', counts?.textures]].map(([l, n]) => <span key={l} data-tip="Free to use, counted live from the library"><b className="m-num" data-testid={`pdr-n-${l.split(' ')[0]}`}>{K(n)}</b><small>{l}</small></span>)}</div> : null}
        <p className="pdr-note">Every model gets these same tools. A stronger mind makes better work with them.</p></aside>
    </section></div>;
}
