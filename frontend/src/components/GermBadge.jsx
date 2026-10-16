import React from 'react';
import { useGerm, germView } from '../lib/germ';
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
  if (!v) return null;
  return <span className={`germ-chip ${TONE[v.tone]}${compact ? ' is-compact' : ''}`} data-tip={v.tip} data-testid="germ-chip">
    <i className="gm-ico"><Microbe /></i>
    {!compact && <b className="gm-word">{v.word}</b>}
    <em className="gm-num">{v.short}</em>
    {!compact && <span className="gm-meter" aria-hidden="true"><span style={{ transform: `scaleX(${v.fill})` }} /></span>}
  </span>;
}
