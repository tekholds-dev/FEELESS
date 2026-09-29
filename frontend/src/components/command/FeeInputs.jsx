import React, { useEffect, useState } from 'react';

// Number box with its live meaning pinned inside the right edge (e.g. 150 → "= 1.50%").
// Whole numbers show with commas (70,000,000) and hand back plain digits to onChange.
// suffix may be a list: clicking the chip cycles through them (e.g. SOL ↔ USD).
export function UnitInput({ suffix, value, onChange, min, max, ...props }) {
  const [view, setView] = useState(0);
  const options = (Array.isArray(suffix) ? suffix : [suffix]).filter(Boolean);
  const shown = value === '' || value == null ? '' : Number(String(value).replace(/,/g, '')).toLocaleString('en-US');
  const change = e => { const digits = e.target.value.replace(/[^0-9]/g, ''); onChange({ target: { value: digits === '' ? '' : String(Number(digits)) } }); };
  return <span className="unit-input"><input type="text" inputMode="numeric" value={shown} onChange={change} {...props} />
    {options.length > 1 ? <button type="button" className="unit-chip" title="Click to switch" onClick={() => setView(v => (v + 1) % options.length)}>{options[view % options.length]} ⇄</button> : <em aria-hidden="true">{options[0]}</em>}</span>;
}

// SOL/USD for the money previews (Jupiter price, same source as the swap boxes).
export function useSolUsd() {
  const [px, setPx] = useState(null);
  useEffect(() => {
    let alive = true;
    const SOL = 'So11111111111111111111111111111111111111112';
    fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json()).then(d => alive && setPx(Number(d?.[SOL]?.usdPrice) || null)).catch(() => {});
    return () => { alive = false; };
  }, []);
  return px;
}

export const money = v => (v >= 1 ? `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `${(v * 100).toFixed(v * 100 >= 10 ? 0 : 1)}¢`);

// What one trade looks like with these settings: what you earn vs what the trader pays in total.
export function TradePreview({ feeBps, tipLamports, solUsd }) {
  const [size, setSize] = useState(1);
  const sol = n => (solUsd ? money(n * solUsd) : `${n.toFixed(6)} SOL`);
  const yours = size * (Number(feeBps) || 0) / 10000;
  const tip = (Number(tipLamports) || 0) / 1e9;
  const network = 0.000005;
  return <div className="trade-preview" data-testid="trade-preview">
    <div className="tp-head"><b>One trade of</b>{[0.1, 1, 10].map(n => <button key={n} type="button" className={size === n ? 'active' : ''} onClick={() => setSize(n)}>{n} SOL{solUsd ? ` · ${money(n * solUsd)}` : ''}</button>)}</div>
    <div className="tp-rows">
      <span className="you"><small>You earn</small><b>{sol(yours)}</b><em>{((Number(feeBps) || 0) / 100).toFixed(2)}%</em></span>
      <span><small>Speed tip (validators)</small><b>{sol(tip)}</b><em>max</em></span>
      <span><small>Network fee</small><b>{sol(network)}</b><em>fixed</em></span>
      <span className="total"><small>Trader pays in fees</small><b>{sol(yours + tip + network)}</b><em>{size ? `${(((yours + tip + network) / size) * 100).toFixed(2)}%` : ''}</em></span>
    </div>
    <small className="cc-empty">Plus pool/DEX fees inside the route, and ~0.002 SOL one-time rent on a coin's first buy.</small>
  </div>;
}

