import React, { useMemo, useState } from 'react';
import { cleanShots } from './SnapStack';
import '../../styles/poiFolder.css';
import { Ic3 } from '../../lib/icon3d';

// 🧬 THE PoI FOLDER (SI21): one child folder in every PoW. It shows how THIS PoW used Proof of Intelligence: the route each mind took and why,
// what it verified, what was unavailable, and what the mind's DNA looks like. Every number comes from the folder or the owner's PoI view;
// a PoW filed before tracing says so instead of guessing. Sealed facts and route hashes never reach this page.
const STATE = { verified: 'Validated', candidate: 'Candidate', rejected: 'Nothing usable', gap: 'Unavailable' };
const PROMOTE_AFTER = 4;   // poi.evolution: four visits before a source can be promoted

function Ring({ value, label, sub, tip }) {
  const v = value == null ? null : Math.max(0, Math.min(1, value)); const C = 2 * Math.PI * 26;
  return <span className="pf-ring m-glass" data-tip={tip}><svg viewBox="0 0 64 64" aria-hidden="true"><circle className="pf-ring-bg" cx="32" cy="32" r="26" />
    {v == null ? null : <circle className="pf-ring-on" cx="32" cy="32" r="26" strokeDasharray={`${C * v} ${C}`} />}</svg>
    <b className="m-num">{v == null ? '—' : `${Math.round(v * 100)}%`}</b><em>{label}</em><small>{sub}</small></span>;
}

function Stat({ label, value, sub, tip }) {
  return <span className="pf-stat m-glass" data-tip={tip}><em>{label}</em><b className="m-num">{value}</b><small>{sub}</small></span>;
}

// A mind's fingerprint, drawn from its real source coverage: one ring per source, its arc = that source's facts per visit; promoted sources glow.
function Fingerprint({ coverage, states, mind }) {
  const rows = Object.entries(coverage || {}).sort((a, b) => a[0].localeCompare(b[0])).slice(0, 9);
  const top = Math.max(1, ...rows.map(([, s]) => Number(s.yield) || 0));
  return <svg className={`pf-print is-m${mind}`} viewBox="0 0 100 100" role="img" aria-label={`Mind ${mind ? 'B' : 'A'} source fingerprint`}>
    {rows.length ? <g className="pf-print-spin">{rows.map(([h, s], k) => { const r = 12 + k * 4.4; const C = 2 * Math.PI * r; const on = (Number(s.yield) || 0) / top;
      return <circle key={h} className={`pf-arc is-${states?.[h] || 'candidate'}`} cx="50" cy="50" r={r} strokeDasharray={`${Math.max(1.5, C * on)} ${C}`} transform={`rotate(${k * 47} 50 50)`} />; })}</g>
      : <circle className="pf-arc is-none" cx="50" cy="50" r="30" />}
  </svg>;
}

function nodesOf(f, c) {
  const m = c.mint; const t = f.poiTrace?.[m]; const facts = f.vitals?.[m] || []; const shots = cleanShots(f, m);
  const gaps = new Set([...(f.evidenceMetrics?.[m]?.gaps || []), ...(t?.walled || [])]); const first = {};
  shots.forEach(s => { first[s.site] = Math.min(first[s.site] ?? Infinity, s.at || Infinity); });
  const all = new Set([...(t?.visited || []), ...(f.usedBy?.[m] || []), ...shots.map(s => s.site), ...facts.map(x => x.site), ...gaps, ...(t?.required || [])]);
  const order = t?.order || [];
  return [...all].filter(Boolean).sort((a, b) => (first[a] ?? Infinity) - (first[b] ?? Infinity) || order.indexOf(a) - order.indexOf(b)).map((h, i) => {
    const mine = facts.filter(x => x.site === h || (x.sites || []).includes(h)); const ok = mine.filter(x => x.verified).length; const seen = (t?.visited || []).includes(h) || first[h] != null || mine.length > 0;
    const state = gaps.has(h) || (!seen && (t?.required || []).includes(h)) ? 'gap' : ok ? 'verified' : mine.length ? 'candidate' : 'rejected';
    const why = !t ? 'Route reason not recorded for this PoW' : (t.required || []).includes(h) ? 'Required verification for this coin' : (t.inherited || []).includes(h) ? "Inherited: its partner's promoted source" : (t.reused || []).includes(h) ? 'Facts reused from the archive, checked again here' : order.includes(h) ? `Ranked #${order.indexOf(h) + 1} by this mind's own evidence` : 'Opened during research';
    return { h, i, state, facts: mine, ok, why, dna: t?.states?.[h], shots: shots.filter(s => s.site === h), at: first[h] === Infinity ? null : first[h] };
  });
}

function Lane({ f, c, on, onPick, nodeKey, onNode }) {
  const nodes = useMemo(() => nodesOf(f, c), [f, c]); const t = f.poiTrace?.[c.mint]; const mind = t?.mind ?? f.owner?.[c.mint];
  return <div className={`pf-lane m-glass${on ? ' is-on' : ''}`}><button type="button" className="pf-coin" onClick={onPick} aria-pressed={on} data-tip={`Open $${c.sym}'s evidence`} data-testid={`pf-coin-${c.mint}`}>
    <b>${c.sym}</b><small>{mind == null ? 'mind not recorded' : `Mind ${mind ? 'B' : 'A'}`}{t?.generation ? ` · gen ${t.generation}` : ''}</small></button>
    <ol className="pf-path">{f.live && nodes.length ? <i className="pf-run" aria-hidden="true" /> : null}
      {nodes.map(n => <li key={n.h} style={{ '--i': n.i }}><button type="button" className={`pf-node is-${n.state}${nodeKey === `${c.mint}|${n.h}` ? ' is-open' : ''}`} onClick={() => onNode(c, n)} data-tip={`${n.h}: ${STATE[n.state]} · ${n.why}`} data-testid={`pf-node-${n.h}`}>
        <i aria-hidden="true" /><span>{n.h}</span><small className="m-num">{n.ok ? `${n.ok} ✓` : n.facts.length || '0'}</small></button></li>)}
      {!nodes.length ? <li className="pf-none">No browser route was kept for this coin</li> : null}</ol></div>;
}

// Each mind's fingerprint and DNA: the one mind view, used in every PoI folder and at the top of the PoW desk.
export function PoiMinds({ poi, f }) {
  return <div className="pf-minds">{[0, 1].map(i => { const m = (poi?.minds || []).find(x => x.mind === i); const gens = m?.generations || 0; const ev = (m?.events || []).slice(-3).reverse(); const here = f ? Object.values(f.poiTrace || {}).filter(t => t.mind === i) : null;
    return <article key={i} className={`pf-mind m-glass is-m${i}`} data-testid={`pf-mind-${i}`}><Fingerprint coverage={m?.coverage} states={m?.states} mind={i} />
      <div><b>MIND {i ? 'B' : 'A'}</b><small>{m ? `${gens} generations · ${m.verified} verified facts · ${m.uniqueRoutes} routes` : 'No Research DNA read'}</small>
        {here ? <small>{here.length ? `This PoW added ${here.length} generation${here.length === 1 ? '' : 's'}` : 'This PoW added no recorded generation'}</small> : null}
        {gens < PROMOTE_AFTER ? <span className="pf-need" data-tip="A source needs four visits before it can be promoted"><u><s style={{ transform: `scaleX(${gens / PROMOTE_AFTER})` }} /></u><small>Insufficient samples: {gens} of {PROMOTE_AFTER}</small></span> : null}
        {ev.length ? <ul className="pf-events">{ev.map(e => <li key={`${e.site}${e.generation}`} className={`is-${e.state}`}>{e.site} {e.state} · gen {e.generation}</li>)}</ul> : <small>No promotion, retirement or rollback yet</small>}</div></article>; })}</div>;
}

// The hard limits this desk runs under: read-only, the same numbers the engine enforces.
export function KernelCard({ kernel }) {
  if (!kernel) return null;
  return <details className="pf-kernel m-glass" data-testid="pf-kernel"><summary><b>🧱 KERNEL {kernel.v}</b><small className="m-num">{kernel.hash}</small></summary>
    <div>{kernel.groups.map(g => <section key={g.name}><em>{g.name}</em>{g.rows.map(([k, v]) => <span key={k}><small>{k}</small><b className="m-num">{Array.isArray(v) ? v.join(' – ') : v === false ? 'never' : String(v)}</b></span>)}</section>)}</div></details>;
}

export function PoiFolder({ f, poi, onShot }) {
  const [pick, setPick] = useState(null);
  const coins = (f.coins || []).filter(c => f.vitals?.[c.mint] || f.poiTrace?.[c.mint] || (f.shots || []).some(s => s.mint === c.mint));
  const traced = !!f.poiTrace && Object.keys(f.poiTrace).length > 0;
  const all = coins.flatMap(c => nodesOf(f, c)); const sites = new Set(all.map(n => n.h)); const useful = new Set(all.filter(n => n.facts.length).map(n => n.h));
  const facts = coins.flatMap(c => f.vitals?.[c.mint] || []); const verified = facts.filter(x => x.verified).length;
  const req = Object.values(f.poiTrace || {}).flatMap(t => t.required || []); const reqSeen = Object.values(f.poiTrace || {}).flatMap(t => (t.required || []).filter(h => (t.visited || []).includes(h) || (t.reused || []).includes(h)));
  const ms = Object.values(f.evidenceMetrics || {}); const usd = ms.reduce((a, m) => a + (m.costUsd || 0), 0); const secs = ms.length ? Math.round(ms.reduce((a, m) => a + (m.durationSec || 0), 0) / ms.length) : null; const msFacts = ms.reduce((a, m) => a + (m.verified || 0), 0);
  const spent = ms.reduce((a, m) => a + (m.durationSec || 0), 0); const modelSec = ms.reduce((a, m) => a + (m.modelSec || 0), 0); const openSec = ms.reduce((a, m) => a + (m.openSec || 0), 0); const timed = spent > 0 && ms.some(m => m.modelSec != null);
  const stateCount = s => all.filter(n => n.state === s).length;
  const openNode = pick ? (coins.find(c => c.mint === pick.mint) && nodesOf(f, coins.find(c => c.mint === pick.mint)).find(n => n.h === pick.h)) : null;
  return <section className="pf" data-testid="poi-folder" aria-label="Proof of Intelligence for this PoW">
    <header className="pf-head m-glass"><b><Ic3 e="🧬" /> PROOF OF INTELLIGENCE</b><small>{String(f.name || '').split(' · ')[0]} · owner only · sealed facts stay sealed</small></header>
    {!traced ? <p className="pf-gap" role="note" data-testid="pf-not-recorded">Not recorded: this PoW ran before PoI tracing, so route reasons and its DNA generation were not kept. Below is only what the folder saved.</p> : null}
    <div className="pf-vitals">
      <Ring value={sites.size ? useful.size / sites.size : null} label="SOURCE YIELD" sub={`${useful.size} of ${sites.size} sites gave facts`} tip="Sites that gave at least one fact, out of the sites opened for this PoW" />
      <Ring value={facts.length && traced ? verified / facts.length : null} label="VERIFIED" sub={traced ? `${verified} of ${facts.length} facts` : 'not recorded'} tip="Facts that matched the page text they came from" />
      <Ring value={req.length ? reqSeen.length / req.length : null} label="REQUIRED" sub={req.length ? `${reqSeen.length} of ${req.length} checked` : 'not recorded'} tip="Required sources such as Solscan and pump.fun that were really read" />
      <Stat label="FACTS PER $" value={usd > 0 ? (msFacts / usd).toFixed(0) : '—'} sub={usd > 0 ? `$${usd.toFixed(3)} research` : 'not recorded'} tip="Verified facts per reported research dollar" />
      <Stat label="TIME A COIN" value={secs == null ? '—' : `${secs}s`} sub={timed ? `model ${Math.round(100 * modelSec / spent)}% · open ${Math.round(100 * openSec / spent)}% · browser ${Math.max(0, Math.round(100 * (spent - modelSec - openSec) / spent))}%` : ms.length ? `${ms.length} round${ms.length === 1 ? '' : 's'}` : 'not recorded'} tip="Average research time per coin, and where that time went" />
    </div>
    <div className="pf-legend">{Object.entries(STATE).map(([k, l]) => <span key={k} className={`m-chip is-${k}`}><i aria-hidden="true" />{l} <b className="m-num">{stateCount(k)}</b></span>)}</div>
    <div className="pf-lanes">{coins.map(c => <Lane key={c.mint} f={f} c={c} on={pick?.mint === c.mint} onPick={() => setPick(p => (p?.mint === c.mint && !p.h ? null : { mint: c.mint }))} nodeKey={pick ? `${pick.mint}|${pick.h}` : ''} onNode={(cc, n) => setPick({ mint: cc.mint, h: n.h })} />)}
      {!coins.length ? <p className="pf-gap">No coin in this PoW reached browser research.</p> : null}</div>
    {openNode ? <div className="pf-claims m-glass" data-testid="pf-claims"><b>{openNode.h}</b><small>{STATE[openNode.state]} · {openNode.why}{openNode.dna ? ` · DNA: ${openNode.dna}` : ''}</small>
      {openNode.facts.length ? <ul>{openNode.facts.map((x, k) => <li key={`${x.label}${k}`}><em>{x.label}</em><b className="m-num">{x.value}</b><small>{x.verified ? 'verified' : 'candidate'}{x.at ? ` · ${new Date(x.at * 1000).toLocaleTimeString()}` : ''}</small></li>)}</ul> : <p className="pf-none">No facts came from this source in this PoW.</p>}
      {openNode.shots.length ? <span className="pf-shots">{openNode.shots.map(s => <button key={s.file} type="button" className="m-btn" onClick={() => onShot?.(s)} data-tip="Open the snapshot this came from">Snapshot {s.n}</button>)}</span> : null}</div> : null}
    {(f.shadow || []).length ? <div className="pf-shadow m-glass" data-testid="pf-shadow"><b>🌘 COINS NOT BOUGHT</b><small>Price only, no fills or fees assumed.</small><ul>{f.shadow.map(r => <li key={r.mint} className={r.priceMovePct > 0 ? 'is-up' : r.priceMovePct < 0 ? 'is-dn' : ''}><em>${r.sym}</em><b className="m-num">{r.priceMovePct == null ? 'no price' : `${r.priceMovePct >= 0 ? '+' : ''}${r.priceMovePct}%`}</b></li>)}</ul></div> : f.shadowDueAt ? <p className="pf-gap">Coins not bought are read again at {new Date(f.shadowDueAt * 1000).toLocaleTimeString()}.</p> : null}
    <PoiMinds poi={poi} f={f} />
  </section>;
}
