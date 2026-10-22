import React from 'react';
import '../../styles/poolPreview.css';

// 🏊 POOL PREVIEW (owner P4: "vault / pool pair builder needs a live visual of the user's picks"): what the pool in PoolCreator WILL be, drawn
// from the inputs as you type — the two piles (your tokens vs SOL), the opening price between them, how far a 1 SOL buy moves the price
// (x · y = k), the anti-snipe fee falling to the swap fee over its window, and the lock. Pure math, nothing is sent.
// pure: the pool's numbers from the form (null when the piles are empty)
export function poolMath({ tokens, sol, feeBps, launchFeeBps, launchMinutes, supply }) {
  const T = Number(tokens) || 0; const S = Number(sol) || 0;
  if (T <= 0 || S <= 0) return null;
  const fee = (Number(feeBps) || 0) / 100; const start = Math.max(fee, (Number(launchFeeBps) || 0) / 100); const mins = Number(launchMinutes) || 0;
  return { price: S / T, share: supply ? Math.min(100, (T / supply) * 100) : null, impact1: (1 / (S + 1)) * 100, fee, start, mins, snipe: start > fee && mins > 0 };
}
// pure: the anti-snipe fee curve as SVG points (linear decay from `start` % to `fee` % over the window)
export const decayPath = (start, fee, w = 140, h = 44) => {
  const top = Math.max(start, fee, 1);
  const y = v => h - 4 - (v / top) * (h - 10);
  return `M4 ${y(start).toFixed(1)} L${(w * 0.72).toFixed(1)} ${y(fee).toFixed(1)} L${w - 4} ${y(fee).toFixed(1)}`;
};

export function PoolPreview({ form, supply, solPx }) {
  const m = poolMath({ ...form, supply });
  if (!m) return <div className="ppv is-empty" data-testid="pool-preview"><span className="ppv-pile t" /><span className="ppv-pile s" /><p>Type the tokens + SOL — the pool draws itself here.</p></div>;
  const lt = Math.log10(1 + Number(form.tokens)); const ls = Math.log10(1 + Number(form.sol) * 1e6);   // both piles on one log scale (SOL counted in lamports-ish units)
  const hi = Math.max(lt, ls, 1);
  const depth = Math.max(0.04, Math.min(1, 1 - m.impact1 / 50));
  return <div className="ppv" data-testid="pool-preview">
    <div className="ppv-piles" aria-hidden="true">
      <span className="ppv-pile t" style={{ transform: `scaleY(${Math.max(0.08, lt / hi)})` }}><b>TOKENS</b></span>
      <span className="ppv-price"><em>OPENS AT</em><b>{m.price < 0.001 ? m.price.toExponential(2) : m.price.toFixed(6)}</b><small>SOL / token{solPx ? ` · $${(m.price * solPx).toPrecision(3)}` : ''}</small><i className="ppv-dot" /></span>
      <span className="ppv-pile s" style={{ transform: `scaleY(${Math.max(0.08, ls / hi)})` }}><b>SOL</b></span>
    </div>
    <div className="ppv-meters">
      <p data-tip="How far ONE 1-SOL buy moves the opening price (x · y = k). Deeper pool = smaller move."><em>1 SOL BUY MOVES IT</em><u><s style={{ transform: `scaleX(${depth})` }} /></u><b>{m.impact1 >= 10 ? m.impact1.toFixed(0) : m.impact1.toFixed(1)}%</b></p>
      {m.share != null ? <p data-tip="Share of the token supply you put in the pool"><em>SUPPLY IN POOL</em><u><s style={{ transform: `scaleX(${Math.max(0.02, m.share / 100)})` }} /></u><b>{m.share.toFixed(1)}%</b></p> : null}
      <p data-tip="Charged on every swap, paid to your position"><em>SWAP FEE</em><u><s style={{ transform: `scaleX(${Math.min(1, m.fee / 5)})` }} /></u><b>{m.fee.toFixed(2)}%</b></p>
    </div>
    <div className="ppv-row">
      <span className="ppv-snipe" data-tip={m.snipe ? `Anti-snipe: ${m.start}% at open, falling to ${m.fee}% over ${m.mins} min` : 'Anti-snipe off'}><em>ANTI-SNIPE</em>
        <svg viewBox="0 0 140 44" aria-hidden="true"><path className="ppv-axis" d="M4 40 H136" /><path className={`ppv-curve ${m.snipe ? '' : 'is-off'}`} d={decayPath(m.start, m.fee)} /></svg>
        <b>{m.snipe ? `${m.start}% → ${m.fee}% · ${m.mins}m` : 'off'}</b></span>
      <span className={`ppv-lock ${form.lock ? 'is-on' : ''}`} data-tip={form.lock ? 'Locked forever: nobody can pull the liquidity — the rug-proof badge' : 'Not locked: the liquidity can be withdrawn'}>
        <svg viewBox="0 0 40 44" aria-hidden="true"><path className="ppv-shackle" d={form.lock ? 'M12 20v-6a8 8 0 0116 0v6' : 'M12 20v-6a8 8 0 0116 0v-2'} /><rect x="8" y="20" width="24" height="20" rx="4" /></svg>
        <b>{form.lock ? 'LOCKED · RUG-PROOF' : 'UNLOCKED'}</b></span>
    </div>
  </div>;
}
