import React from 'react';
import { createPortal } from 'react-dom';
import { useGerm, germView, germWhy } from '../lib/germ';
import { useFloatPop } from '../lib/floatPop';
import '../styles/germ.css';

const TONE = { hot: 'gm-hot', floor: 'gm-floor', near: 'gm-near', far: 'gm-far', lost: 'gm-lost' };   // literal class names (cssHygiene reads them)

// 🦠 The germ mark. GermDot = the little microbe on every coin logo (TokenAvatar, bottom-left); GermChip = the inline chip with the
// distance and a meter from the floor to the owner's germ line (seats, Best 3, Coming up, candidate rows). Both read the shared coin
// edge record — nothing renders when the agents have no germ read for the coin.
function Microbe() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="gm-svg">
    <g className="gm-cilia">{[0, 45, 90, 135, 180, 225, 270, 315].map(a => <line key={a} x1="12" y1="3" x2="12" y2="6.2" transform={`rotate(${a} 12 12)`} />)}</g>
    <circle className="gm-body" cx="12" cy="12" r="5.6" />
    <circle className="gm-nuc" cx="10.4" cy="10.8" r="1.6" /><circle className="gm-nuc" cx="13.8" cy="13.4" r="1" />
  </svg>;
}

export function GermDot({ mint, size = 34 }) {
  const v = germView(useGerm(mint));
  if (!v) return null;
  const d = Math.max(12, Math.round(size * 0.42));
  return <i className={`germ-dot ${TONE[v.tone]}`} style={{ width: d, height: d }} data-tip={v.tip} role="img" aria-label={`germ ${v.word}`} data-testid="germ-dot"><Microbe /></i>;
}

export function GermChip({ mint, germ, compact }) {
  const live = useGerm(germ ? null : mint);
  const v = germView(germ || live);
  const fp = useFloatPop(280);
  if (!v) return null;
  const why = fp.open ? germWhy(germ || live) : null;
  return <span ref={fp.ref} role="button" tabIndex={0} aria-expanded={fp.open} className={`germ-chip ${TONE[v.tone]}${compact ? ' is-compact' : ''}`} data-tip={fp.open ? undefined : `${v.tip} · tap: why the germ matters`} data-testid="germ-chip"
    onClick={e => { e.stopPropagation(); fp.setOpen(o => !o); }} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); fp.setOpen(o => !o); } }}>
    {why ? createPortal(<div ref={fp.popRef} style={fp.style} className={`germ-why ${TONE[v.tone]}`} data-testid="germ-why" onClick={e => e.stopPropagation()}>
      <header><i className="gm-ico"><Microbe /></i><b>{v.word}</b><em>{v.short}</em></header>
      <div className="gw-track" aria-hidden="true"><span className="gw-floor">floor</span><span className="gw-now" style={{ transform: `translateX(${Math.max(0, Math.min(100, (v.d + 10) / 0.6))}%)` }} /><span className="gw-gun">gun line</span></div>
      {why.lines.map(l => <p key={l}>{l}</p>)}
    </div>, document.body) : null}
    <i className="gm-ico"><Microbe /></i>
    {!compact && <b className="gm-word">{v.word}</b>}
    <em className="gm-num">{v.short}</em>
    {!compact && <span className="gm-meter" aria-hidden="true"><span style={{ transform: `scaleX(${v.fill})` }} /></span>}
  </span>;
}
