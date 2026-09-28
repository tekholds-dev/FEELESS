import React from 'react';
import { units } from './SwapWorkspace';

// What this swap's receipt will say once it lands on-chain — shown the moment a quote exists.
export function ReceiptPreview({ order, amount, inputAsset, outputAsset, wallet }) {
  const q = order?.quote;
  if (!q) return null;
  const dec = order.output_metadata?.decimals;
  const fees = [['Network', q.signatureFeeLamports], ['Priority', q.prioritizationFeeLamports], ['Rent', q.rentFeeLamports]].filter(([, v]) => v != null);
  const feeSol = fees.reduce((n, [, v]) => n + Number(v) / 1e9, 0);
  return <aside className="receipt-preview" data-testid="receipt-preview">
    <header><b>Receipt preview</b><small>becomes a verified receipt after you sign</small></header>
    <dl>
      <div><dt>Wallet</dt><dd>{wallet ? `${wallet.slice(0, 4)}…${wallet.slice(-4)}` : 'connect to sign'}</dd></div>
      <div><dt>You pay</dt><dd>{amount} {inputAsset.symbol}</dd></div>
      <div><dt>You get ≈</dt><dd>{units(q.outAmount, dec)} {outputAsset.symbol}</dd></div>
      <div><dt>Minimum</dt><dd>{units(q.otherAmountThreshold, dec)} {outputAsset.symbol}</dd></div>
      <div><dt>Price impact</dt><dd>{(Number(q.priceImpactPct || 0) * 100).toFixed(2)}%</dd></div>
      <div><dt>Chain fees</dt><dd>{fees.length ? `${feeSol.toFixed(6)} SOL` : '—'}</dd></div>
      <div><dt>Route</dt><dd>Jupiter · Solana</dd></div>
    </dl>
    <p>After confirmation it's stored in your Receipts, counted in your totals and tax CSV, and shown in your profile activity.</p>
  </aside>;
}
