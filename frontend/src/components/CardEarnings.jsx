import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ShareGifButton } from './ShareGif';

// 📜 Where the profit went: a slide-in window for ONE card — profit taken out (sits in the wallet as SOL), profit compounded back
// in (and into which coins), fees paid (shown apart, never inside P&L) and every automation step with its reason.
// Real cards get one button: 💸 Collect (sell just the gain, one approval). Click outside / Esc closes.
// 🪟 Card window: the same slide-in also carries the card's actions (＋ Top up · ⇄ Switch · ↩ Withdraw …), its coins with ❄ freeze
// (a frozen coin is never touched by the engine — only you switch it) and every auto the engine fired in the last 24h.
const $ = v => `$${Math.abs(v || 0).toFixed(2)}`;
const px = v => (v >= 1 ? v.toFixed(2) : v >= 0.001 ? v.toFixed(5) : Number(v).toPrecision(3));
const ago = t => { const s = Date.now() / 1000 - t; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };

export function CardEarnings({ title, events = [], taken = 0, compounded = 0, fees, gainNow, onCollect, onClose, paper, actions, legs, onFreeze, autos, extra }) {
  useEffect(() => { const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  // centered pop-up over a blurred page; page animations pause while it's open so the blur costs nothing
  useEffect(() => { document.body.classList.add('ce-open'); return () => document.body.classList.remove('ce-open'); }, []);
  const share = { mascot: 'feecat', tone: (gainNow || taken) > 0 ? 'up' : 'down', kicker: `FEELESS · PROFIT TRAIL${paper ? ' · ARENA' : ''}`, title: String(title).slice(0, 34), big: $(taken + compounded),
    lines: [`${$(taken)} taken out · ${$(compounded)} compounded`, ...events.slice(0, 2).map(e => `${e.label || e.kind}${e.symbol ? ` $${e.symbol}` : ''}${e.usd != null ? ` ${$(e.usd)}` : ''}`.slice(0, 62))], footer: 'feeless · fuse 🧬' };
  return createPortal(<div className="ce-shade is-pop" role="presentation" onClick={onClose} data-testid="card-earnings">
    <aside className="ce is-pop m-live" role="dialog" aria-modal="true" aria-label={`${title} earnings`} onClick={e => e.stopPropagation()}>
      <header><span className="m-label">📜 WHERE THE PROFIT WENT{paper ? ' · PAPER' : ''}</span><h3>{title}</h3><button type="button" className="cx-x" onClick={onClose} aria-label="Close">×</button>
        <ShareGifButton className="m-btn ce-share" label="🎞 Share" card={share} /></header>
      <div className="ce-sum">
        <div data-tip="Taken out by take-profits / collects — it's SOL in the wallet now"><small>TAKEN OUT</small><b className="m-num m-pos">{$(taken)}</b><em>{paper ? 'to cash' : 'in your wallet'}</em></div>
        <div data-tip="Gains rolled back into the card's coins"><small>COMPOUNDED</small><b className="m-num">{$(compounded)}</b><em>back into the card</em></div>
        {fees != null && <div data-tip="FEELESS + network fees on every buy / sell — tracked apart, never mixed into P&L"><small>FEES (APART)</small><b className="m-num m-dim">{$(fees)}</b><em>not in P&L</em></div>}
      </div>
      {onCollect && <button type="button" className="m-btn primary m-go ce-collect" disabled={!(gainNow > 0.01)} onClick={onCollect} data-testid="ce-collect">
        {gainNow > 0.01 ? `💸 Collect ${$(gainNow)} gain — one approval` : 'Nothing to collect yet (card is not up)'}</button>}
      {actions?.length > 0 && <div className="ce-acts" role="toolbar" aria-label="Card actions">{actions.map(a => <button key={a.label} type="button" className={`m-btn ${a.cls || ''}`} disabled={a.disabled} data-tip={a.tip} onClick={a.onClick} data-testid={a.testid}>{a.label}</button>)}</div>}
      {extra}
      {legs?.length > 0 && <section className="ce-legs"><span className="m-label">{onFreeze ? '❄ COINS · FREEZE = ENGINE HANDS OFF' : 'COINS'}</span>{legs.map(l => <div key={l.pairAddress} className={`ce-leg ${l.frozen ? 'is-frozen' : ''}`}>
        <b>${l.symbol}</b><small className="m-dim">{l.role === 'anchor' ? '⚓ anchor' : l.role === 'runner' ? 'runner' : 'pool'}{l.stars ? ` · ${'★'.repeat(l.stars)}` : ''}{l.firstEntry ? ` · in @ $${px(l.firstEntry)}${l.at ? ` · ${ago(l.at)} ago` : ''}` : ''}</small>{l.rundown && <i className="ce-why">{l.rundown}</i>}<em className={`m-num ${(l.pnlPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{l.pnlPct == null ? '—' : `${l.pnlPct >= 0 ? '+' : ''}${Number(l.pnlPct).toFixed(1)}%`}</em>
        {onFreeze && <button type="button" className={`m-btn ce-frz ${l.frozen ? 'is-on' : ''}`} aria-pressed={!!l.frozen} onClick={() => onFreeze(l, !l.frozen)} data-testid={`freeze-${l.pairAddress}`}
          data-tip={l.frozen ? 'Frozen: auto-rotate / swap suggestions skip it. Tap to let the engine manage it again.' : 'Freeze: the engine never switches this coin — only you can.'}>{l.frozen ? '❄ Frozen' : '❄ Freeze'}</button>}</div>)}</section>}
      {autos && <section className="ce-autos"><span className="m-label">⚡ LAST 24H · AUTOS</span>{autos.length ? autos.map((a, i) => <a key={i} href={a.url} className="ce-auto" style={{ '--i': i }}><span>{a.text}</span><time className="m-dim">{ago(a.at)} ago</time></a>)
        : <small className="m-dim">No autos fired in the last 24h — your levels haven't been hit.</small>}</section>}
      <ol className="ce-tl">{events.length ? events.map((e, i) => <li key={i} className={`k-${e.kind}`} style={{ '--i': i }}>
        <b>{e.label || e.kind}</b>{e.symbol && <span>${e.symbol}</span>}{e.usd != null && <em className="m-num">{$(e.usd)}</em>}
        {e.to?.length > 0 && <small>→ {e.to.map(t => (t === 'cash' ? (paper ? 'cash' : 'your wallet') : `$${t}`)).join(', ')}</small>}
        {e.why && <small className="m-dim">{e.why}</small>}<time className="m-dim">{ago(e.at)} ago</time></li>) : <li className="m-dim">No moves yet.</li>}</ol>
    </aside></div>, document.body);
}
