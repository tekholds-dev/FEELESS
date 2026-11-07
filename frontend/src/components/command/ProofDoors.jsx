import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';
import { ProofTools } from './ProofTools';
import { Ic3 } from '../../lib/icon3d';
import { KitPick } from './KitPick';
import { ProofCard } from './ProofGallery';
import { AgentDemo } from './AgentDemo';
const TrenchChart = lazy(() => import('../terminal/TrenchChart').then(m => ({ default: m.TrenchChart })));
const PerpsChart = lazy(() => import('../perps/PerpsChart').then(m => ({ default: m.PerpsChart })));
const VideoEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.VideoEditor })));
const ImageEditor = lazy(() => import('./PocEditor').then(m => ({ default: m.ImageEditor })));

// 🎬 Proofs (owner 2026-11-07: "a cool display of how complex and worthy each proof is… the user clicks the different capabilities and sees a preview of some of the best work, not play around not knowing how"). One stage that fits the window, finished work playing in it, and every capability one tap away. Every model gets the same tools; a stronger mind makes better work with them.
const PROOFS = {
  pos: { ic: '💻', t: 'PoStatic', full: 'Proof of Static', line: 'Real sites and real games, built from one sentence, checked in a real browser.', folders: 'psFolders', gallery: 'PoStatic', make: 'build', go: 'Start a PoStatic', caps: [] },
  pow: { ic: '⛏', t: 'PoW', full: 'Proof of Work', line: 'A real trade, and everything it read before it.', folders: 'powFolders', gallery: 'PoW', cmd: 'file a PoW', go: 'Start a PoW',
    caps: [['demo', '🧠', 'Two minds trade', 'How both minds work a coin together'], ['chart', '📈', 'Its real chart', 'Its best real trade on the real chart'], ['tools', '🛡', 'Live tools', 'Exit ladder and the numbers it reads']] },
  pop: { ic: '📉', t: 'PoP', full: 'Proof of Perps', line: 'Both minds call a market blind, on paper, with a number behind every call.', folders: 'popFolders', gallery: 'PoP', cmd: 'file a perp', go: 'Start a PoP',
    caps: [['demo', '🙈', 'Blind calls', 'Neither mind sees the other first'], ['chart', '💀', 'Where leverage dies', 'True candles with live liquidation lines'], ['tools', '📊', 'Live tools', 'Funding, open interest and the maths']] },
  pob: { ic: '🎲', t: 'PoB', full: 'Proof of Bids', line: 'Picks on any game or market, graded by the scoreboard and never by the mind.', folders: 'pobFolders', gallery: 'PoB', cmd: 'file a pob best NFL picks', go: 'Start a PoB',
    caps: [['tools', '🏟', 'Game room', 'Every game with live numbers. Build a parlay'], ['demo', '🔎', 'How it picks', 'Two minds read the sites and argue the pick']] },
  poc: { ic: '📣', t: 'PoC', full: 'Proof of Content', line: 'From what people read today to a post, a cut, a thumbnail or a 3D commercial.', folders: 'pocFolders', gallery: 'PoC', make: 'content', go: 'Start a PoC',
    caps: [['demo', '📡', 'Finds the story', 'Two minds read what is moving today'], ['video', '🎬', 'Video editor', 'Cuts, text and music, an MP4 on your machine'], ['image', '🖼', 'Image editor', 'Layers and text. The agent can start it'], ['tools', '🧾', 'Live tools', 'What it watches and drafts']] },
};
const SHARED = [['best', '🏆', 'Your best', 'The best one your agents have filed'], ['kits', '🧰', 'Its kits', 'Pick what it brings to this proof']];
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
  const pieces = k === 'pos' ? (counts?.templates || []) : []; const caps = pieces.length ? pieces.map(t => [`piece:${t.id}`, null, t.name, t.what, t.thumb, t.kind]) : p.caps; const all = [...caps, ...SHARED]; const now = all.some(c => c[0] === on) ? on : all[0]?.[0];
  const best = (gallery.find(g => g.kind === p.gallery)?.cards || [])[0];
  const stage = () => {
    if (String(now).startsWith('piece:')) return <Piece key={now} id={now.slice(6)} cat={cat} work={work} />;
    if (now === 'demo') return <div className="pdr-agd" data-testid="pdr-agent"><AgentDemo kind={k === 'pow' || k === 'pop' ? 'trading' : 'general'} mode={k === 'pow' || k === 'pop' ? 'discuss' : 'plan'} /></div>;
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
