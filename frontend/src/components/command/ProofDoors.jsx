import React, { useEffect, useMemo, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { KitPick } from './KitPick';
import { ProofCard } from './ProofGallery';
import { ContentCut, FundingSea, ScoreBoard, TradeFlight } from './ProofVisuals';

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

function WorldDemo({ cat, work, counts }) {
  const [world, setWorld] = useState('nebula'); const [hero, setHero] = useState('star'); const [page, setPage] = useState(''); const [err, setErr] = useState('');
  useEffect(() => { let on = true; setErr(''); Promise.resolve().then(() => work(cat.id, { op: 'tools_demo', tools: { world, hero } })).then(j => on && setPage(j.preview || '')).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id, work, world, hero]);
  return <div className="ptl-demo" data-testid="ptl-world"><div className="ptl-screen">{page ? <iframe title="A real world from the 3D studio" srcDoc={page} sandbox="allow-scripts" data-testid="ptl-world-frame" /> : <p className="dbt-none">{err || 'Building the world…'}</p>}</div>
    <div className="ptl-picks"><span className="m-seg" role="group" aria-label="World">{WORLDS.map(w => <button key={w} type="button" className={world === w ? 'active' : ''} aria-pressed={world === w} onClick={() => setWorld(w)} data-tip={`Runs the real ${w} world`} data-testid={`ptl-w-${w}`}>{w}</button>)}</span><span className="m-seg" role="group" aria-label="Centerpiece">{HEROES.map(h => <button key={h} type="button" className={hero === h ? 'active' : ''} aria-pressed={hero === h} onClick={() => setHero(h)} data-tip={`Runs the real ${h}`} data-testid={`ptl-h-${h}`}>{h}</button>)}</span></div>
    <div className="ptl-nums">{[['MODELS', counts?.models], ['HDRI LIGHTS', counts?.hdris], ['TEXTURES', counts?.textures]].map(([l, n]) => <span key={l} data-tip="Free to use, counted live from the library"><b className="m-num" data-testid={`ptl-n-${l.split(' ')[0]}`}>{K(n)}</b><small>{l}</small></span>)}</div></div>;
}
export function ProofDoors({ cat, d, work, onCommand, onMake, kindFirst = 'pos' }) {
  const [k, setK] = useState(kindFirst); const [counts, setCounts] = useState(null); const [kits, setKits] = useState([]); const [gallery, setGallery] = useState([]); const [trade, setTrade] = useState(null); const p = PROOFS[k];
  useEffect(() => { let on = true; Promise.resolve().then(() => Promise.all([work(cat.id, { op: 'tools_show' }).catch(() => null), work(cat.id, { op: 'kit_list' }).catch(() => null), work(cat.id, { op: 'demo_gallery' }).catch(() => null), work(cat.id, { op: 'demo_trade' }).catch(() => null)])).then(([a, b, c, t]) => { if (!on) return; setCounts(a); setKits(b?.kits || []); setGallery(c?.kinds || []); setTrade(t?.trade || null); }); return () => { on = false; }; }, [cat.id, work]);
  const mine = useMemo(() => kits.filter(x => x.by === 'FEELESS' && x.id !== 'feeless' && (x.kinds || []).includes(k)), [kits, k]); const liveOf = ids => kits.filter(x => ids.includes(x.id)); const best = (gallery.find(g => g.kind === p.gallery)?.cards || [])[0];
  return <div className={`ptl is-${k}`} data-testid="ptl">
    <nav className="ptl-doors" role="tablist" aria-label="Proof types">{Object.entries(PROOFS).map(([x, v]) => <button key={x} type="button" role="tab" aria-selected={k === x} className={k === x ? 'is-on' : ''} onClick={() => setK(x)} data-tip={v.full} data-testid={`ptl-${x}`}><Ic3 e={v.ic} size="26px" /><b>{v.t}</b><small className="m-num">{(d?.[v.folders] || []).length} filed</small></button>)}</nav>
    <section className="ptl-main" key={k}>
      <div className="ptl-left">{k === 'pos' ? <WorldDemo cat={cat} work={work} counts={counts} /> : k === 'pow' ? <TradeFlight t={trade} catId={trade?.cat} /> : k === 'pop' ? <FundingSea kits={liveOf(['fl-funding', 'fl-liq'])} /> : k === 'pob' ? <ScoreBoard kits={liveOf(['fl-source-check', 'fl-value'])} /> : <ContentCut kits={liveOf(['fl-trend'])} />}
        {best ? <ProofCard c={best} i={0} work={work} cat={cat} /> : <p className="dbt-none ptl-none" data-testid="ptl-no-proof">Your agents have not filed a {p.t} yet. Your best one lands here.</p>}</div>
      <div className="ptl-right"><header><span><small className="m-label">{p.full.toUpperCase()}</small><h3>{p.t}</h3><p>{p.line}</p></span><button type="button" className="m-btn m-go ptl-go" onClick={() => (p.make ? onMake?.(p.make) : onCommand?.(p.cmd))} data-tip={p.make ? 'Makes its folder' : `Tells it: ${p.cmd}`} data-testid="ptl-go">{p.go}</button></header>
        <ul className="ptl-tools">{p.tools.map(([ic, t, say], i) => <li key={t} style={{ '--i': i }} data-tip={say}><Ic3 e={ic} size="26px" /><span><b>{t}</b><small>{say}</small></span></li>)}</ul>
        {mine.length ? <div className="ptl-kits"><small className="m-label">{p.t} KITS</small><ul>{mine.map(x => <li key={x.id} data-tip={x.what}><b>{x.name}</b><small>{(x.skills || []).slice(0, 3).join(' · ')}</small></li>)}</ul></div> : null}
        <KitPick cat={cat} work={work} kind={k} /></div>
    </section></div>;
}
