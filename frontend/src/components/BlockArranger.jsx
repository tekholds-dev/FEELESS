import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { TOWN, STAND, MY_POOLS, ISLAND_CELLS, myPools, usd, dollarsSmall, apyTxt } from '../lib/cityPlan';
import { EarnTicker } from './EarnTicker';
import { JOB_OF, openDesk } from './MoneyDesk';
import '../styles/blockArranger.css';

// ✋ ARRANGE THE BLOCK (owner, 2026-10-23: "more islands joined by bridges, pick your own lots, MOVE buildings, add little stands, a MY POOLS
// combo building — the layout stored server-side per family"): the family's cells as drawn lots, island by island (15 a island, a bridge between
// each). DRAG a lot onto another (or tap one, tap another) → they swap (buildings move, plots get picked). Pick an OPEN lot → 🏗 BUILD HERE lists
// the city's markets: the one you choose is added on save (/familia-block/act add) and stands on THAT lot. Add an open lot, a stand, MY POOLS or a
// whole new island; the bin clears the picked land (buildings come off the block from their own card). Save = /familia-block/layout.
export const LAYOUT_MAX = 60;
export const STANDS_MAX = 16;   // beauty plots (block_markets.STANDS_MAX)
export const startCells = bl => [...(bl?.layout || []), ...(bl?.layoutSaved ? [] : Array.from({ length: Math.max(0, bl?.open ?? 3) }, () => 'open'))];
export const swap = (cells, a, b) => { const c = [...cells]; [c[a], c[b]] = [c[b], c[a]]; return c; };
export const addCell = (cells, cell) => (cells.length >= LAYOUT_MAX ? cells : [...cells, cell]);
export const newIsland = (cells, per = ISLAND_CELLS) => { const pad = (per - (cells.length % per)) % per; const out = [...cells, ...Array.from({ length: pad }, () => 'gap'), 'open', 'open', 'open'];
  return out.length > LAYOUT_MAX ? cells : out; };
export const removable = cell => cell === 'open' || cell === 'gap' || cell === 'pools' || /^(stand|new):/.test(String(cell));
// pure: the markets picked in Arrange (`new:<key>` lots) → the adds to make first, then the layout with them standing on their lots
export const pendingAdds = cells => ({ adds: cells.filter(c => String(c).startsWith('new:')).map(c => String(c).slice(4)), cells: cells.map(c => (String(c).startsWith('new:') ? `blk:${String(c).slice(4)}` : c)) });
export function cellLook(cell, bl) {
  const [kind, ...rest] = String(cell).split(':'); const id = rest.join(':');
  if (kind === 'blk') { const b = (bl?.buildings || []).find(x => x.key === id); return { icon: b?.state === 'built' ? '🏙' : '🏗', name: b?.sym || b?.name || id, tone: b?.state === 'built' ? 'built' : 'build', color: '#d4af37' }; }
  if (kind === 'town' && TOWN[id]) return { icon: '🏘', name: TOWN[id].name, tone: 'town', color: TOWN[id].color };
  if (kind === 'stand' && STAND[id]) return { icon: STAND[id].icon, name: STAND[id].name, tone: 'stand', color: STAND[id].color };
  if (kind === 'new') { const m = (bl?.catalog || []).find(x => x.key === id); return { icon: '🏗', name: m?.name || id, tone: 'new', color: '#45e486' }; }
  if (cell === 'pools') return { icon: '💧', name: MY_POOLS.name, tone: 'pools', color: MY_POOLS.color };
  if (cell === 'open') return { icon: '📍', name: 'OPEN LOT', tone: 'open', color: '#d4af37' };
  return { icon: '🌿', name: 'LAND', tone: 'gap', color: '#4f7a5a' };
}

export function BlockArranger({ bl, busy, onSave, onClose }) {
  const [cells, setCells] = useState(() => startCells(bl)); const [pick, setPick] = useState(null);
  useEffect(() => { const esc = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [onClose]);
  const per = bl?.islandCells || ISLAND_CELLS;
  const isles = useMemo(() => { const out = []; for (let i = 0; i < Math.max(1, cells.length); i += per) out.push(cells.slice(i, i + per).map((c, k) => [c, i + k])); return out; }, [cells, per]);
  const stands = cells.filter(c => String(c).startsWith('stand:')).length; const hasPools = cells.includes('pools');
  const tap = i => { if (drag.current?.moved) { drag.current = null; return; } if (pick == null) setPick(i); else { if (pick !== i) setCells(c => swap(c, pick, i)); setPick(null); } };
  // ✋ drag: the lot lifts and follows the pointer (transform only); dropped on another lot → they swap. A press that never moves stays a tap.
  const drag = useRef(null); const [dg, setDg] = useState(null);
  const cellAt = (x, y) => { const el = document.elementFromPoint?.(x, y)?.closest?.('[data-cell]'); return el ? Number(el.dataset.cell) : null; };
  const down = (e, i) => { if (e.button > 0) return; drag.current = { i, x: e.clientX, y: e.clientY, moved: false }; e.currentTarget.setPointerCapture?.(e.pointerId); };
  const move = e => { const d = drag.current; if (!d) return; const dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (!d.moved && Math.hypot(dx, dy) < 6) return; d.moved = true; setDg({ i: d.i, dx, dy, over: cellAt(e.clientX, e.clientY) }); };
  const up = e => { const d = drag.current; if (!d) return; if (d.moved) { const t = cellAt(e.clientX, e.clientY); if (t != null && t !== d.i) setCells(c => swap(c, d.i, t)); setPick(null); setDg(null); setTimeout(() => { drag.current = null; }, 0); } else drag.current = null; };
  const onLot = pick != null && cells[pick] === 'open'; const standing = new Set([...(bl?.buildings || []).map(b => b.key), ...pendingAdds(cells).adds]);
  const menu = onLot ? (bl?.catalog || []).filter(m => !standing.has(m.key)) : [];
  const add = cell => { setCells(c => addCell(c, cell)); setPick(null); };
  const tools = [['open', '📍 Open lot', 'A plot to build a market on'], ...Object.entries(STAND).map(([k, s]) => [`stand:${k}`, `${s.icon} ${s.name.toLowerCase()}`, `${s.name} — ${s.sub} (a beauty plot, never money)`])];
  return createPortal(<div className="bar-back" onClick={e => e.target === e.currentTarget && onClose()}>
    <section className="bar" role="dialog" aria-modal="true" aria-label="Arrange the block" data-testid="block-arranger">
      <header className="bar-top"><b>✋ ARRANGE THE BLOCK</b><small>drag a lot onto another — they swap · pick an open lot to build on it</small>
        <span className="bar-meters"><span data-tip={`Lots on the block (${LAYOUT_MAX} max)`}><em>LOTS</em><b key={cells.length}>{cells.length}</b><i><u style={{ transform: `scaleX(${cells.length / LAYOUT_MAX})` }} /></i></span>
          <span data-tip={`Islands — a new one (and its bridge) every 15 lots · ${bl?.islandsPaid || 1} owned`} className={isles.length > (bl?.islandsPaid || 1) && bl?.islandMp ? 'is-cost' : ''}><em>ISLANDS</em><b>{isles.length}</b>
            {isles.length > (bl?.islandsPaid || 1) && bl?.islandMp ? <small data-testid="bar-cost">−{((isles.length - (bl.islandsPaid || 1)) * bl.islandMp).toLocaleString('en-US')} MP</small> : null}</span>
          <span data-tip={`Street stands (${STANDS_MAX} max)`}><em>STANDS</em><b>{stands}/{STANDS_MAX}</b></span></span>
        <button type="button" className="bar-x" onClick={onClose} aria-label="Close" data-tip="Close without saving (Esc)">✕</button></header>
      <div className="bar-tools">
        {tools.map(([cell, word, tip]) => <button key={cell} type="button" onClick={() => add(cell)} disabled={cells.length >= LAYOUT_MAX || (cell.startsWith('stand:') && stands >= STANDS_MAX)} data-tip={tip} data-testid={`bar-add-${cell.replace(':', '-')}`}>+ {word}</button>)}
        <button type="button" onClick={() => add('pools')} disabled={hasPools || cells.length >= LAYOUT_MAX} data-tip="One building of every LP · stake · lend position on the block, live" data-testid="bar-add-pools">+ 💧 MY POOLS</button>
        <button type="button" className="is-isle" onClick={() => { setCells(c => newIsland(c, per)); setPick(null); }} disabled={cells.length + 3 > LAYOUT_MAX}
          data-tip={`A new island east, joined by a bridge, with three open lots — ${bl?.islandMp ? `${bl.islandMp.toLocaleString('en-US')} MP from the family bank when you save` : 'free for the creator wallet'}`} data-testid="bar-add-island">+ 🏝 new island <small>{bl?.islandMp ? `${(bl.islandMp / 1000).toFixed(0)}K MP` : 'FREE'}</small></button>
        <button type="button" className="is-bin" onClick={() => { setCells(c => c.filter((_, i) => i !== pick)); setPick(null); }} disabled={pick == null || !removable(cells[pick])}
          data-tip={pick != null && !removable(cells[pick]) ? 'Buildings come off the block from their own card — move it instead' : 'Clear the picked lot (open lots, land, stands, MY POOLS)'} data-testid="bar-bin">🗑 clear picked</button>
      </div>
      {onLot ? <div className="bar-build" data-testid="bar-build"><b>🏗 BUILD A MARKET ON THIS LOT</b><small>it stands here once you save · it lights up when a member opens a real position</small>
        {menu.length ? <div className="bar-build-list">{menu.map((m, k) => <button key={m.key} type="button" style={{ '--i': k }} onClick={() => { setCells(c => c.map((x, j) => (j === pick ? `new:${m.key}` : x))); setPick(null); }}
          data-tip={m.proof === 'none' ? m.why : `${m.name} — ${m.offer}`} data-testid={`bar-build-${m.key}`}><span>{m.name}</span><small>{m.offer}</small><i className={m.proof === 'none' ? 'is-none' : ''}>{m.proof === 'none' ? 'no reader yet' : 'live'}</i></button>)}</div>
          : <p className="bar-build-nil">Every market in the city already stands on your block.</p>}</div> : null}
      <div className="bar-isles">{isles.map((row, j) => <div key={j} className="bar-isle" style={{ '--j': j }}>
        <span className="bar-isle-h">🏝 ISLAND {j + 1}<small>{row.length}/{per}</small>{j ? <i className="bar-bridge" aria-hidden="true" /> : null}</span>
        <div className="bar-grid">{row.map(([c, i]) => { const l = cellLook(c, bl);
          return <button key={`${c}-${i}`} type="button" className={`bar-cell t-${l.tone} ${pick === i ? 'is-pick' : ''} ${pick != null && pick !== i ? 'is-target' : ''} ${dg?.i === i ? 'is-drag' : ''} ${dg && dg.over === i && dg.i !== i ? 'is-over' : ''}`}
            style={{ '--c': l.color, '--i': i % per, ...(dg?.i === i ? { transform: `translate(${dg.dx}px, ${dg.dy}px) scale(1.06)` } : null) }} data-cell={i}
            onPointerDown={e => down(e, i)} onPointerMove={move} onPointerUp={up} onPointerCancel={() => { drag.current = null; setDg(null); }} onClick={() => tap(i)} aria-pressed={pick === i} data-testid={`bar-cell-${i}`} data-tip={pick == null ? `${l.name} — drag it onto another lot (or tap, then tap where it goes)${c === 'open' ? ' · tap to build a market here' : ''}` : pick === i ? 'Picked — tap another lot to swap' : `Swap with ${cellLook(cells[pick], bl).name}`}>
            <i aria-hidden="true">{l.icon}</i><b>{l.name}</b></button>; })}</div></div>)}</div>
      <footer className="bar-foot"><button type="button" className="m-btn" onClick={() => { setCells(startCells(bl)); setPick(null); }} disabled={busy} data-tip="Back to the saved layout">↺ Reset</button>
        <button type="button" className="m-btn m-go" disabled={busy} onClick={() => onSave(cells)} data-testid="bar-save" data-tip="Saved on the family — every member sees it (nothing is bought or sold)">{busy ? 'Saving…' : '💾 Save the block'}</button></footer>
    </section></div>, document.body);
}

// 💧 MY POOLS — the combo building's card: every position on the block, live, biggest first, its total on top
export function MyPoolsCard({ bl, lp }) {
  const mp = myPools(bl, (lp || []).filter(p => !p.empty)); const rows = [...mp.rows].sort((a, b) => b.usd - a.usd); const top = Math.max(1, ...rows.map(r => r.usd));
  const yr = rows.reduce((t, r) => t + (r.apy > 0 ? (r.usd || 0) * r.apy / 100 : 0), 0);
  return <div className="mpc" data-testid="my-pools-card">
    <div className="mpc-head"><span className="mpc-orb" aria-hidden="true"><i /><i /><i /></span><div><b>💧 MY POOLS</b><small>every LP · stake · lend position on the block</small></div>
      <strong className="fl-tick" key={mp.usd}>{usd(mp.usd) || '$0'}</strong></div>
    <div className="mpc-kv"><span><em>POSITIONS</em><b>{mp.n}</b></span><span><em>FEES WAITING</em><b>+{dollarsSmall(mp.fees)}</b></span><span><em>IN RANGE</em><b>{mp.inRange}/{rows.filter(r => r.kind === 'lp').length}</b></span></div>
    {rows.length ? <ul className="mpc-rows">{rows.map((r, i) => <li key={r.key} className={r.kind === 'lp' ? (r.inRange ? 'is-in' : 'is-out') : 'is-mkt'} style={{ '--i': i }}
      data-tip={r.kind === 'lp' ? `${r.sym}: ${r.inRange ? 'in range, earning' : 'out of range, earning 0'} · fees +${dollarsSmall(r.fees)}` : `${r.sym}: a real position · APY ${apyTxt(r.apy)}`}>
      <b>{r.sym}</b><i><u style={{ transform: `scaleX(${Math.max(0.03, r.usd / top)})` }} /></i><em>{dollarsSmall(r.usd)}</em></li>)}</ul>
      : <p className="mpc-nil">No positions yet — open one from a building's card (or the money desk) and it lands here.</p>}
    {yr > 0 ? <EarnTicker perYear={yr} label="MY POOLS · EARNING NOW" tip="Every position on the block at its live APY — what they earn while you look (LP fees ride on top)" testid="mpc-earn" /> : null}
    <button type="button" className="m-btn m-go mpc-go" onClick={() => openDesk({ job: JOB_OF[rows[0]?.kind] || 'best', title: 'MY POOLS · PUT MORE TO WORK' })} data-tip="The money desk pops out big — add to a pool, stake or lend; your wallet signs" data-testid="mpc-go">⚡ PUT MORE TO WORK</button>
  </div>;
}
