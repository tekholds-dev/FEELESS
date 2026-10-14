import React from 'react';
import '../styles/feeStamp.css';

// 🔏 THE $FEE STAMP (Home, beside the heading; owner, 2026-10-14: "FEE home needs a stamp that really looks good"): a notary seal —
// serrated edge, a ring of words that turns slowly, the FEELESS mark + $FEE in the middle, $FEE's live 24h move on the bottom arc. It
// thumps in ONCE with an ink ring when the page opens, tilts on hover. transform / opacity only; still in fx-lite / reduced motion.
const RING = '★ FEELESS ★ $FEE ★ ZERO FEE TO BUY ★ TRENCH CERTIFIED ★ FEELESS ★ $FEE ★ HOLDERS EAT FIRST ';
const num = v => (v == null || v === '' ? NaN : Number(v));
export const moveWord = v => { const n = num(v); return Number.isFinite(n) ? `${n >= 0 ? '▲ +' : '▼ '}${n.toFixed(Math.abs(n) >= 100 ? 0 : 1)}% · 24H` : 'LIVE · $FEE'; };

export function FeeStamp({ change24h }) {
  const n = num(change24h); const tone = !Number.isFinite(n) ? 'flat' : n >= 0 ? 'up' : 'dn';
  return <a className={`fstamp is-${tone}`} href="/terminal/fee" data-testid="fee-stamp" aria-label="$FEE — the FEELESS token" data-tip="$FEE — buying it is fee-free on FEELESS. Tap for its page.">
    <span className="fstamp-ink" aria-hidden="true" />
    <svg className="fstamp-svg" viewBox="0 0 200 200" aria-hidden="true">
      <defs><path id="fstamp-ring" d="M100,100 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0" /><path id="fstamp-low" d="M38,112 A64,64 0 0,0 162,112" /></defs>
      <circle className="fstamp-teeth" cx="100" cy="100" r="95" />
      <circle className="fstamp-edge" cx="100" cy="100" r="88" />
      <circle className="fstamp-edge is-in" cx="100" cy="100" r="60" />
      <g className="fstamp-turn"><text className="fstamp-words"><textPath href="#fstamp-ring">{RING}</textPath></text></g>
    </svg>
    <span className="fstamp-core"><img src="/assets/feeless-logo.png" alt="" /><b>$FEE</b><small data-testid="fee-stamp-move">{moveWord(change24h)}</small></span>
  </a>;
}
