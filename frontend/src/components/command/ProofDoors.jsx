import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { ProofTools } from './ProofTools';
import { Ic3 } from '../../lib/icon3d';
import { KitPick } from './KitPick';
import { ProofCard } from './ProofGallery';
const TrenchChart = lazy(() => import('../terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
const PerpsChart = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));
const VideoEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.VideoEditor })));
const ImageEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.ImageEditor })));

// 🧰 Proofs (owner 2026-11-07: "show our new and amazing tools per each proof in the demo"). One door per proof, its real tools, what is moving in them right now, its own best proof. Nothing here is a mock-up: every number comes from the server.
const PROOFS = {
  pow: { ic: '⛏', t: 'PoW', full: 'Proof of Work', line: 'A real trade, and everything it read before it.', folders: 'powFolders', gallery: 'PoW', cmd: 'file a PoW', go: 'Start a PoW',
    tools: [['🔎', 'Reads real sites', 'Picture proof of every site it read'], ['🛡', 'Exits set first', 'Its stop and target before it buys'], ['⚖', 'Scored on the result', 'Real money and how long it held count most'], ['🥊', 'Debate rooms', 'Take it into a room to earn boost points']] },
  pop: { ic: '📉', t: 'PoP', full: 'Proof of Perps', line: 'Both minds call a market blind, on paper.', folders: 'popFolders', gallery: 'PoP', cmd: 'file a perp', go: 'Start a PoP',
    tools: [['🙈', 'Blind calls', 'Neither mind sees the other first'], ['🧾', 'A real reason', 'A call with no number behind it is refused'], ['📈', 'True candles', 'The source’s own candles, unedited'], ['🥊', 'Debate rooms', 'Take it into a room to earn boost points']] },
  pob: { ic: '🎲', t: 'PoB', full: 'Proof of Bids', line: 'Picks on any game or market, graded by the score.', folders: 'pobFolders', gallery: 'PoB', cmd: 'file a pob best NFL picks', go: 'Start a PoB',
    tools: [['🏟', 'Game room', 'Live ESPN numbers on every game'], ['🎯', 'Parlay legs', 'File several picks as one proof'], ['📊', 'Graded by the score', 'The scoreboard marks it, not the mind'], ['🥊', 'Debate rooms', 'Take it into a room to earn boost points']] },
  poc: { ic: '📣', t: 'PoC', full: 'Proof of Content', line: 'From what people read today to a post, a cut or a thumbnail.', folders: 'pocFolders', gallery: 'PoC', make: 'content', go: 'Start a PoC',
    tools: [['🎬', 'Video editor', 'Cuts, text and music, an MP4 on your own machine'], ['🖼', 'Image editor', 'Layers and text, the agent can start it'], ['📡', 'Live desk', 'Watches pages hourly and drafts on what is new'], ['🎥', '3D commercial', 'Its plan, then film it in the editor']] },
  pos: { ic: '💻', t: 'PoStatic', full: 'Proof of Static', line: 'A page that really works, checked in a real browser.', folders: 'psFolders', gallery: 'PoStatic', make: 'build', go: 'Start a PoStatic',
    tools: [['🧊', '3D studio', 'Real models, light and textures'], ['🌌', 'Worlds and prints', 'A new look for each new request'], ['📍', 'Marks', 'Drag on any spot, scroll, drag the next'], ['👁', 'Real browser check', 'Overlaps and covered words cost it score'], ['🧰', 'Stash backup', 'If your 3 kits do not help, it reaches into the stash'], ['📲', 'Add to desk', 'Keep a build as an app on its desktop']] },
};
const WORLDS = ['stars', 'nebula', 'aurora', 'grid', 'ocean', 'void']; const HEROES = ['star', 'orb', 'crystal', 'rings'];
const K = n => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K` : String(n || 0));

const num = v => +String(v).replace(/,/g, '');
const levOf = kits => { const m = kits.flatMap(k => k.fresh || []).map(x => String(x).match(/^(\w+) mark \$([\d,.]+): 3x long \$([\d,.]+) \/ short \$([\d,.]+), 10x long \$([\d,.]+) \/ short \$([\d,.]+)/)).find(Boolean); return m ? { sym: m[1], l3: num(m[3]), s3: num(m[4]), l10: num(m[5]), s10: num(m[6]) } : null; };
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
// 📣 The real editors, right here.
function EditorDemo({ cat, work }) {
  const [mode, setMode] = useState('video');
  return <div className="pdr-demo" data-testid="pdr-editor"><span className="m-seg" role="tablist" aria-label="Which editor">{[['video', 'Video editor'], ['image', 'Image editor']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={mode === k} className={mode === k ? 'active' : ''} onClick={() => setMode(k)} data-tip={k === 'video' ? 'Drop a clip and cut it. Renders an MP4 on your machine' : 'Layers and text on a real canvas'} data-testid={`pdr-ed-${k}`}>{l}</button>)}</span><div className="pdr-editor"><Suspense fallback={<Wait what="Opening the editor…" />}>{mode === 'video' ? <VideoEditor cat={cat} work={work} /> : <ImageEditor cat={cat} work={work} />}</Suspense></div></div>;
}
function WorldDemo({ cat, work, counts }) {
  const [world, setWorld] = useState('nebula'); const [hero, setHero] = useState('star'); const [page, setPage] = useState(''); const [err, setErr] = useState('');
  useEffect(() => { let on = true; setErr(''); Promise.resolve().then(() => work(cat.id, { op: 'tools_demo', tools: { world, hero } })).then(j => on && setPage(j.preview || '')).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id, work, world, hero]);
  return <div className="pdr-demo" data-testid="pdr-world"><div className="pdr-screen">{page ? <iframe title="A real world from the 3D studio" srcDoc={page} sandbox="allow-scripts" data-testid="pdr-world-frame" /> : <p className="dbt-none">{err || 'Building the world…'}</p>}</div>
    <div className="pdr-picks"><span className="m-seg" role="group" aria-label="World">{WORLDS.map(w => <button key={w} type="button" className={world === w ? 'active' : ''} aria-pressed={world === w} onClick={() => setWorld(w)} data-tip={`Runs the real ${w} world`} data-testid={`pdr-w-${w}`}>{w}</button>)}</span><span className="m-seg" role="group" aria-label="Centerpiece">{HEROES.map(h => <button key={h} type="button" className={hero === h ? 'active' : ''} aria-pressed={hero === h} onClick={() => setHero(h)} data-tip={`Runs the real ${h}`} data-testid={`pdr-h-${h}`}>{h}</button>)}</span></div>
    <div className="pdr-nums">{[['MODELS', counts?.models], ['HDRI LIGHTS', counts?.hdris], ['TEXTURES', counts?.textures]].map(([l, n]) => <span key={l} data-tip="Free to use, counted live from the library"><b className="m-num" data-testid={`pdr-n-${l.split(' ')[0]}`}>{K(n)}</b><small>{l}</small></span>)}</div></div>;
}
export function ProofDoors({ cat, d, work, onCommand, onMake, kindFirst = 'pos' }) {
  const [k, setK] = useState(kindFirst); const [counts, setCounts] = useState(null); const [kits, setKits] = useState([]); const [gallery, setGallery] = useState([]); const [trade, setTrade] = useState(null); const p = PROOFS[k];
  useEffect(() => { let on = true; Promise.resolve().then(() => Promise.all([work(cat.id, { op: 'tools_show' }).catch(() => null), work(cat.id, { op: 'kit_list' }).catch(() => null), work(cat.id, { op: 'demo_gallery' }).catch(() => null), work(cat.id, { op: 'demo_trade' }).catch(() => null)])).then(([a, b, c, t]) => { if (!on) return; setCounts(a); setKits(b?.kits || []); setGallery(c?.kinds || []); setTrade(t?.trade || null); }); return () => { on = false; }; }, [cat.id, work]);
  const liveOf = ids => kits.filter(x => ids.includes(x.id)); const best = (gallery.find(g => g.kind === p.gallery)?.cards || [])[0];
  const proofBox = best ? <ProofCard c={best} i={0} work={work} cat={cat} /> : <p className="dbt-none pdr-none" data-testid="pdr-no-proof">Your agents have not filed a {p.t} yet. Your best one lands here.</p>;
  return <div className={`pdr is-${k}`} data-testid="pdr">
    <nav className="pdr-doors" role="tablist" aria-label="Proof types">{Object.entries(PROOFS).map(([x, v]) => <button key={x} type="button" role="tab" aria-selected={k === x} className={k === x ? 'is-on' : ''} onClick={() => setK(x)} data-tip={v.full} data-testid={`pdr-${x}`}><Ic3 e={v.ic} size="26px" /><b>{v.t}</b><small className="m-num">{(d?.[v.folders] || []).length} filed</small></button>)}</nav>
    <section className="pdr-main" key={k}>
      <div className="pdr-left">{k === 'pos' ? <WorldDemo cat={cat} work={work} counts={counts} /> : k === 'pow' ? <TradeDemo t={trade} /> : k === 'pop' ? <PerpDemo kits={liveOf(['fl-liq'])} /> : k === 'poc' ? <EditorDemo cat={cat} work={work} /> : <ProofTools key="bids" kind="bids" onCommand={onCommand} />}
        {k === 'pob' ? null : proofBox}</div>
      <div className="pdr-right"><header><span><small className="m-label">{p.full.toUpperCase()}</small><h3>{p.t}</h3><p>{p.line}</p></span><button type="button" className="m-btn m-go pdr-go" onClick={() => (p.make ? onMake?.(p.make) : onCommand?.(p.cmd))} data-tip={p.make ? 'Makes its folder' : `Tells it: ${p.cmd}`} data-testid="pdr-go">{p.go}</button></header>
        <ul className="pdr-tools">{p.tools.map(([ic, t, say], i) => <li key={t} style={{ '--i': i }} data-tip={say}><Ic3 e={ic} size="22px" /><b>{t}</b></li>)}</ul>
        {k === 'pob' ? proofBox : null}
        {k === 'pow' || k === 'pop' || k === 'poc' ? <ProofTools key={k} kind={k === 'poc' ? 'content' : k} onCommand={onCommand} /> : null}
        <KitPick cat={cat} work={work} kind={k} /></div>
    </section></div>;
}
