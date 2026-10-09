import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useFloatPop } from '../lib/floatPop';
import { useCoinEdge } from '../lib/coinEdge';
import '../styles/bsBar.css';

// 🌊 BUYS vs SELLS bar (owner, 2026-10-08: "show the buys-vs-sells bar all the time, 5m / 1h — click the time to switch; clicking the bar is a
// dropdown for the flow exit; on swap-in coins and every chart"). Data = the coin edge record's `bs` (Jupiter window stats + the live 90s
// tape for held coins) — the ONE shared coin poller, no poller of its own. The 5m / 1h choice is one for the whole site (remembered).
const TFS = ['5m', '1h'];
const KEY = 'feeless.bsTf';
const tfSubs = new Set();
let tfNow = (() => { try { return localStorage.getItem(KEY) === '1h' ? '1h' : '5m'; } catch { return '5m'; } })();
export function useBsTf() {
  const [tf, setTf] = useState(tfNow);
  useEffect(() => { tfSubs.add(setTf); return () => { tfSubs.delete(setTf); }; }, []);
  const toggle = () => { tfNow = tfNow === '5m' ? '1h' : '5m'; try { localStorage.setItem(KEY, tfNow); } catch { /* private window */ } tfSubs.forEach(f => f(tfNow)); };
  return [tf, toggle];
}
const m$ = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${Math.round(v || 0)}`);
export const FLOW_MODES = [['', '🌊 card'], ['normal', '🌊 normal'], ['tight', '🌊 tight'], ['off', '🌊 off']];

export function BsBar({ mint, row = null, flowMode, onFlow, compact = false }) {
  const edge = useCoinEdge(row ? null : mint);
  const bs = row || edge?.bs || null;
  const [tf, toggle] = useBsTf();
  const fp = useFloatPop(150); const { open, setOpen } = fp;
  const w = bs?.[tf] || bs?.[tf === '5m' ? '1h' : '5m'] || null;
  const shown = bs?.[tf] ? tf : w ? (tf === '5m' ? '1h' : '5m') : tf;
  const tot = w ? (w.buyUsd || 0) + (w.sellUsd || 0) : 0;
  const b = tot > 0 ? w.buyUsd / tot : 0.5;
  const lead = !tot ? 'is-none' : w.sellUsd > 1.3 * w.buyUsd ? 'is-sell' : w.buyUsd > 1.3 * w.sellUsd ? 'is-buy' : '';
  const live = bs?.['90s'];
  const tip = `${tot ? `${shown}: ${m$(w.buyUsd)} bought · ${m$(w.sellUsd)} sold${w.n ? ` · ${w.n} trades` : ''}${w.pxChg != null ? ` · price ${w.pxChg >= 0 ? '+' : ''}${w.pxChg}%` : ''}` : 'No trades read yet'}`
    + `${live ? ` · live 90s: ${m$(live.buyUsd)} ⇄ ${m$(live.sellUsd)}` : ''}. Tap ${tf} to switch to ${tf === '5m' ? '1h' : '5m'}${onFlow ? ' · tap the bar for this coin\'s flow exit' : ''}.`;
  return <span className={`bsb ${lead} ${compact ? 'is-compact' : ''}`} data-testid={`bs-${mint || 'row'}`}>
    <button type="button" className="bsb-tf" onClick={e => { e.stopPropagation(); toggle(); }} aria-label={`Show ${tf === '5m' ? '1 hour' : '5 minutes'}`} data-testid="bs-tf">{shown}</button>
    <button type="button" ref={fp.ref} className="bsb-bar" data-tip={tip} aria-haspopup={onFlow ? 'menu' : undefined} aria-expanded={onFlow ? open : undefined}
      onClick={e => { e.stopPropagation(); if (onFlow) setOpen(o => !o); }} data-testid="bs-bar">
      <i className="bsb-b" style={{ transform: `scaleX(${Math.max(0.03, b)})` }} /><i className="bsb-s" style={{ transform: `scaleX(${Math.max(0.03, 1 - b)})` }} />
      <small>{tot ? `${m$(w.buyUsd)} ⇄ ${m$(w.sellUsd)}` : '—'}</small>{flowMode && flowMode !== 'off' && <u className="bsb-fx" aria-hidden>🌊</u>}</button>
    {open && onFlow && createPortal(<span ref={fp.popRef} className="bsb-pop" style={fp.style} role="menu" data-testid="bs-flow-pop">{FLOW_MODES.map(([v, l]) => <button key={v || 'card'} type="button" role="menuitem" className={(flowMode || '') === v ? 'active' : ''}
      onClick={e => { e.stopPropagation(); setOpen(false); onFlow(v); }} data-testid={`bs-flow-${v || 'card'}`}>{l}</button>)}</span>, document.body)}
  </span>;
}

export default BsBar;
