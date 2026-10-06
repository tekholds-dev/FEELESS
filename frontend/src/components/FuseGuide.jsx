import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { RISK_DIALS } from '../lib/riskDial';
import { CYCLE_OPTS, SHAPE_WORDS, CLOCK_WORDS, STOP_WORDS, STRATEGY_WORDS, COIN_WORDS, TRENCH_WORDS } from '../lib/fuseGlossary';
import '../styles/fuseGuide.css';

// 📖 "What it means": every dial, cycle, shape, clock, stop mode, strategy and coin source in plain words — and you can PICK
// a dial or a cycle right from it. Centered pop-up (portal), Esc / click outside closes, animates in ≤200ms.
export const GUIDE_TABS = [['dials', '🎚 Dials'], ['cycles', '🔄 Cycles'], ['shapes', '🧬 Shapes'], ['clocks', '⏱ Clocks & stops'], ['strats', '🧠 Strategies'], ['coins', '⚓ Coins'], ['talk', '🗣 Trench talk']];
const exit = ([tp, sl]) => `+${tp}% / −${sl}%`;

export function FuseGuide({ dial, onDial, cycle, onCycle, label = '📖 What it means', start = 'dials' }) {
  const [open, setOpen] = useState(false); const [tab, setTab] = useState(start);
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  const pick = (fn, v) => { fn?.(v); };
  const body = {
    dials: <div className="fg-dials">{Object.entries(RISK_DIALS).map(([k, d]) => <article key={k} className={`fg-dial r-${k} ${dial === k ? 'is-on' : ''}`}>
      <b>{d.label}</b><p>{d.why}</p>
      <dl className="m-kv"><dt>Pools</dt><dd className="m-num">{exit(d.pool)}</dd><dt>Runners</dt><dd className="m-num">{exit(d.runner)}</dd><dt>Profit at</dt><dd className="m-num">+{d.at}%</dd>
        <dt>On profit</dt><dd>{d.onProfit === 'collect' ? '💸 collect' : '♻ compound'}</dd><dt>Card</dt><dd>{d.mode === 'swap' ? '🤖 auto-rotate' : '🔒 hold'}</dd><dt>Max runners</dt><dd className="m-num">{d.runners}</dd></dl>
      {onDial && <button type="button" className={`m-btn ${dial === k ? 'is-on' : ''}`} onClick={() => pick(onDial, k)} data-testid={`fg-dial-${k}`}>{dial === k ? '✓ Picked' : 'Pick this dial'}</button>}</article>)}</div>,
    cycles: <ul className="fg-list">{CYCLE_OPTS.map(([k, l, w]) => <li key={k} className={cycle === k ? 'is-on' : ''}><b>{l}</b><span>{w}</span>
      {onCycle && <button type="button" className={`m-btn ${cycle === k ? 'is-on' : ''}`} onClick={() => pick(onCycle, k)} data-testid={`fg-cycle-${k}`}>{cycle === k ? '✓' : 'Use'}</button>}</li>)}
      <li><b>✎ Your own</b><span>Pick up to 3 shapes in order (e.g. degen → safest → anchor) with “OR PICK 3” in the card plan.</span></li></ul>,
    shapes: <ul className="fg-list">{SHAPE_WORDS.map(([k, l, mix, w]) => <li key={k}><b>{l}</b><span><em className="m-num">{mix}</em> — {w}</span></li>)}</ul>,
    clocks: <ul className="fg-list">{[...CLOCK_WORDS, ...STOP_WORDS.map(([l, w]) => [`Stop: ${l}`, w])].map(([l, w]) => <li key={l}><b>{l}</b><span>{w}</span></li>)}</ul>,
    strats: <ul className="fg-list">{STRATEGY_WORDS.map(([k, l, w]) => <li key={k}><b>{l}</b><span>{w}</span></li>)}<li><b>⚖ Honest numbers</b><span>Every strategy is judged on the arena’s typical $5 run (median) and an outlier-proof average — never one lucky run.</span></li></ul>,
    coins: <ul className="fg-list">{COIN_WORDS.map(([l, w]) => <li key={l}><b>{l}</b><span>{w}</span></li>)}</ul>,
    talk: <ul className="fg-list">{TRENCH_WORDS.map(([l, w]) => <li key={l}><b>{l}</b><span>{w}</span></li>)}</ul>,
  };
  return <>
    <button type="button" className="m-btn fg-open" onClick={() => setOpen(true)} data-tip="Every dial, cycle, shape and strategy in plain words — pick right from the guide" data-testid="fg-open">{label}</button>
    {open && createPortal(<div className="fg-shade" role="presentation" onClick={() => setOpen(false)} data-testid="fuse-guide">
      <aside className="fg m-card" role="dialog" aria-modal="true" aria-label="What it means" onClick={e => e.stopPropagation()}>
        <header><span className="m-label">📖 WHAT IT MEANS</span><button type="button" className="m-btn fg-x" onClick={() => setOpen(false)} aria-label="Close">✕</button></header>
        <div className="m-seg fg-tabs" role="tablist">{GUIDE_TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`fg-tab-${k}`}>{l}</button>)}</div>
        <div className="fg-body" key={tab}>{body[tab]}</div>
        <p className="m-note">Mechanics are proven on paper and real fills; profit never is. Fees are always shown apart from P&amp;L.</p>
      </aside></div>, document.body)}
  </>;
}
