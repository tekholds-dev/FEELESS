import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

// 📜 Where the profit went: a slide-in window for ONE card — profit taken out (sits in the wallet as SOL), profit compounded back
// in (and into which coins), fees paid (shown apart, never inside P&L) and every automation step with its reason.
// Real cards get one button: 💸 Collect (sell just the gain, one approval). Click outside / Esc closes.
const $ = v => `$${Math.abs(v || 0).toFixed(2)}`;
const ago = t => { const s = Date.now() / 1000 - t; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

export function CardEarnings({ title, events = [], taken = 0, compounded = 0, fees, gainNow, onCollect, onClose, paper }) {
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  return createPortal(<div className="ce-shade" role="presentation" onClick={onClose} data-testid="card-earnings">
    <aside className="ce" role="dialog" aria-modal="true" aria-label={`${title} earnings`} onClick={e => e.stopPropagation()}>
      <header><span className="m-label">📜 WHERE THE PROFIT WENT{paper ? ' · PAPER' : ''}</span><h3>{title}</h3><button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button></header>
      <div className="ce-sum">
        <div data-tip="Taken out by take-profits / collects — it's SOL in the wallet now"><small>TAKEN OUT</small><b className="m-num m-pos">{$(taken)}</b><em>{paper ? 'to cash' : 'in your wallet'}</em></div>
        <div data-tip="Gains rolled back into the card's coins"><small>COMPOUNDED</small><b className="m-num">{$(compounded)}</b><em>back into the card</em></div>
        {fees != null && <div data-tip="FEELESS + network fees on every buy / sell — tracked apart, never mixed into P&L"><small>FEES (APART)</small><b className="m-num m-dim">{$(fees)}</b><em>not in P&L</em></div>}
      </div>
      {onCollect && <button type="button" className="m-btn primary m-go ce-collect" disabled={!(gainNow > 0.01)} onClick={onCollect} data-testid="ce-collect">
        {gainNow > 0.01 ? `💸 Collect ${$(gainNow)} gain — one approval` : 'Nothing to collect yet (card is not up)'}</button>}
      <ol className="ce-tl">{events.length ? events.map((e, i) => <li key={i} className={`k-${e.kind}`} style={{ '--i': i }}>
        <b>{e.label || e.kind}</b>{e.symbol && <span>${e.symbol}</span>}{e.usd != null && <em className="m-num">{$(e.usd)}</em>}
        {e.to?.length > 0 && <small>→ {e.to.map(t => (t === 'cash' ? (paper ? 'cash' : 'your wallet') : `$${t}`)).join(', ')}</small>}
        {e.why && <small className="m-dim">{e.why}</small>}<time className="m-dim">{ago(e.at)} ago</time></li>) : <li className="m-dim">No moves yet.</li>}</ol>
    </aside></div>, document.body);
}
