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


// Live money: fee-account balances read on-chain + fees from confirmed trades. Refreshes every 30s.
export function LiveMoney({ call, solUsd }) {
  const [d, setD] = useState(null);
  const [fz, setFz] = useState(null);   // live $ from people fusing (card legs matched to the fee ledger)
  const [err, setErr] = useState('');
  useEffect(() => {
    let alive = true;
    const load = () => { call('/admin/fees/earnings').then(x => { if (alive) { setD(x); setErr(''); } }).catch(e => alive && setErr(e.message));
      call('/admin/fuses/fees').then(x => alive && setFz(x)).catch(() => {}); };
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [call]);
  const usd = v => (v == null ? '—' : v >= 1 ? `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `${(v * 100).toFixed(1)}¢`);
  const bal = label => (d?.balances || []).find(b => b.label === label);
  const sol = bal('SOL'); const usdc = bal('USDC');
  const t = d?.trades;
  return <div className="cc-block live-money" data-testid="live-money"><h4><i className="flr-dot" /> Live money</h4>
    {err && !d ? <small className="cc-empty">{err}</small> : !d ? <small className="cc-empty">Reading the chain…</small> : <>
      <div className="lm-grid">
        <span className="lm-hero"><small>In your fee accounts now</small><b>{usd((sol?.amount || 0) * (solUsd || 0) + (usdc?.amount || 0))}</b><em>{sol ? `${sol.amount.toFixed(4)} SOL` : '— SOL'} · {usdc ? `${usdc.amount.toFixed(2)} USDC` : '— USDC'}</em></span>
        <span><small>Last hour</small><b>{usd(t?.hour)}</b></span>
        <span><small>Last 24h</small><b>{usd(t?.day)}</b></span>
        <span><small>7 days</small><b>{usd(t?.week)}</b><em>{t ? `${t.trades} trades · ${usd(t.volumeUsd)} volume` : 'trade stats offline'}</em></span>
        <span className="lm-fuse" data-testid="lm-fuse" data-tip="FEELESS fees from Fuse card legs (bundle pricing). Cmd Ctr cards pay none — only network / partner fees."><small>⚛️ Fuse fees · 24h</small><b>{usd(fz?.day)}</b><em>{fz ? `1h ${usd(fz.hour)} · 7d ${usd(fz.week)} · ${fz.cards} cards / ${fz.legs} legs` : 'reading…'}</em></span>
      </div>
      {t?.coins?.length > 0 && <div className="lm-coins"><small>Top coins by fees (7d)</small>{t.coins.slice(0, 6).map(c => <div key={c.mint}><b>${c.symbol || c.mint.slice(0, 4)}</b><span>{c.trades} trades</span><em>{usd(c.feesUsd)}</em></div>)}</div>}
      <small className="cc-empty">Balances are read on-chain. Per-window fees are from confirmed trades (trade value × fee).</small></>}
  </div>;
}

// Plain-English earnings table: your cut on common trade sizes, before and after holder discounts.
export function FeeTable({ feeBps, discounts = {} }) {
  const bps = Number(feeBps) || 0;
  const tiers = [['No discount', 0], ['Fee Friend', Number(discounts['1']) || 0], ['Fee Insider', Number(discounts['2']) || 0], ['Fee Whale', Number(discounts['3']) || 0]];
  const cell = (size, off) => { const v = size * bps / 10000 * (1 - Math.min(90, off) / 100); return v >= 1 ? `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `${(v * 100).toFixed(v * 100 >= 10 ? 0 : 1)}¢`; };
  return <div className="fee-table" data-testid="fee-table">
    <p><b>You earn {(bps / 100).toFixed(2)}% of every trade.</b> Holders get a discount off your cut (never below 10% of it).</p>
    <table><thead><tr><th>Trade size</th>{tiers.map(([n, off]) => <th key={n}>{n}{off ? ` −${off}%` : ''}</th>)}</tr></thead>
      <tbody>{[1, 10, 100, 1000].map(size => <tr key={size}><td>${size.toLocaleString('en-US')}</td>{tiers.map(([n, off]) => <td key={n}>{cell(size, off)}</td>)}</tr>)}</tbody></table>
  </div>;
}
