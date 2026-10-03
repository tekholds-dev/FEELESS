import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { BundlePricing, RoundsPricing } from './FuseAdminSettings';
import { usd, txUrl } from '../FuseMoney';
import '../../styles/fuseMoney.css';

// HQ › Fuse › 💲 Fees: the full Fuse fee layout in one place — what a trader pays (first buy per coin · round packs · card
// swaps / sells per coin), a live $ receipt, and every fee actually paid (clickable: type filter → row → its transaction).
// HQ / creator wallets never pay the FEELESS fee on cards (network only). Fees are never inside anyone's P&L.
// 💳 Prepaid swaps: a new card's first buy also pays its first rounds' swap fees (same approval); those swaps then pay no FEELESS fee.
function PrepayPricing({ call, initial }) {
  const [p, setP] = useState(initial || { on: true, perSwapUsd: 0.05, swapsPerRound: 2, rounds: 5 });
  useEffect(() => { if (initial) setP(initial); }, [initial]);
  const set = (k, v) => setP(x => ({ ...x, [k]: v }));
  const total = (Number(p.perSwapUsd) || 0) * (Number(p.swapsPerRound) || 0) * (Number(p.rounds) || 0);
  const save = () => call('/admin/fees/prepay', { method: 'POST', body: JSON.stringify(p) }).then(x => { setP(x.prepay); toast.success('Prepaid swaps saved'); }).catch(e => toast.error(e.message));
  return <div className="cc-block fee-bundle" data-testid="prepay-pricing"><h4>8 · 💳 Prepaid swaps (paid with the first buy)</h4>
    <label className="cc-check"><input type="checkbox" checked={!!p.on} onChange={e => set('on', e.target.checked)} />Add the first rounds' swap fees to a new card's first buy (HQ / creator wallets never pay it)</label>
    <div className="cc-mini-grid">
      <label>$ per swap<input type="number" step="0.01" min="0" max="1" value={p.perSwapUsd} onChange={e => set('perSwapUsd', Number(e.target.value))} data-testid="prepay-per" /></label>
      <label>Swaps per round (5-min rounds: 5–10 max)<input type="number" min="1" max="10" value={p.swapsPerRound} onChange={e => set('swapsPerRound', Number(e.target.value))} /></label>
      <label>Rounds covered<input type="number" min="1" max="20" value={p.rounds} onChange={e => set('rounds', Number(e.target.value))} /></label></div>
    <small className="cc-empty">A new card pays <b>${total.toFixed(2)}</b> up front ({(Number(p.swapsPerRound) || 0) * (Number(p.rounds) || 0)} swaps). Those card swaps then pay $0 FEELESS fee until the credit is used.</small>
    <button type="button" className="btn-primary" onClick={save} data-testid="prepay-save">Save prepaid swaps</button></div>;
}

const KINDS = [['buy', '🃏 First buys', 'Coins bought when a card opened (per-coin price)'], ['swap', '⇄ Swaps', 'Coins switched in later (rotations / buy-backs)'],
  ['sell', '✂ Sells', 'Take-profits, collects, withdraws'], ['rounds', '🔁 Round packs', '+5 rounds — paid now or by the card from profit']];

export function FuseFees({ call }) {
  const [d, setD] = useState(null);
  const [kind, setKind] = useState('all');
  const [row, setRow] = useState(null);
  const load = useCallback(() => call('/admin/fuses/fee-list').then(setD).catch(() => setD({ rows: [], totals: {} })), [call]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <section className="m-card fw"><span className="loader" /> Loading fees…</section>;
  const rows = (d.rows || []).filter(r => kind === 'all' || r.kind === kind);
  const ex = d.example;
  return <section className="fw" data-testid="fuse-fees">
    <div className="m-card m-live fw"><header className="m-row"><span className="m-label">💲 FUSE FEES · WHAT TRADERS PAY</span><small className="m-dim">HQ + creator wallets: $0 FEELESS fee on every card action (network only)</small></header>
      {ex && <div className="fw-kpis" data-testid="fee-example">
        <span data-tip="A $20 card with 3 coins"><small>FIRST BUY · $20 · 3 COINS</small><b className="m-num">{usd(ex.buyUsd)}</b><em>{((ex.buyUsd / 20) * 100).toFixed(2)}% of the card</em></span>
        <span><small>EACH ROTATION</small><b className="m-num">{usd(ex.swapUsd)}</b><em>sell + buy, out of the swap</em></span>
        <span><small>+5 ROUNDS</small><b className="m-num">{usd(ex.per5Usd)}</b><em>first 5 free · card can pay from profit</em></span>
        <span data-tip="First buy + one rotation per round for 10 rounds + one round pack"><small>10 ROUNDS ALL-IN</small><b className="m-num">{usd(ex.totalUsd)}</b><em>{ex.pct}% of $20</em></span>
        <span data-tip="All FEELESS fees paid on Fuse cards so far ÷ the $ they traded"><small>AVG FEE PAID</small><b className="m-num">{d.avgPct}%</b><em>{usd(d.allUsd)} on {usd(d.tradedUsd)} · {d.cards} cards</em></span></div>}
      <small className="m-dim">Make the first buy cheap (per-coin price) and keep rotations tiny — the card pays its packs from profit only when it's up, so a losing card never gets cut by fees.</small></div>
    <BundlePricing call={call} initial={d.bundle} swapBps={d.swapBps} />
    <RoundsPricing call={call} initial={d.rounds} />
    <PrepayPricing call={call} initial={d.prepay} />
    <div className="m-card fw"><span className="m-label">📒 EVERY FEE PAID · TAP A TYPE, THEN A ROW</span>
      <div className="ff-kinds" role="tablist">{[['all', '∑ All', 'Every Fuse fee'], ...KINDS].map(([k, l, tip]) => { const t = k === 'all' ? { n: (d.rows || []).length, usd: d.allUsd } : (d.totals || {})[k] || { n: 0, usd: 0 };
        return <button key={k} type="button" role="tab" aria-selected={kind === k} className={`ff-kind ${kind === k ? 'active' : ''}`} data-tip={tip} onClick={() => { setKind(k); setRow(null); }} data-testid={`ff-${k}`}>
          <small>{l} · {t.n}</small><b className="m-num">{usd(t.usd)}</b></button>; })}</div>
      {row && <div className="ff-detail" data-testid="ff-detail"><b>{KINDS.find(k => k[0] === row.kind)?.[1]} · {row.cardName}</b><span>{row.symbol ? `$${row.symbol} · ` : ''}trade {usd(row.tradeUsd)} · fee {usd(row.feeUsd)}{row.tradeUsd ? ` (${((row.feeUsd / row.tradeUsd) * 100).toFixed(2)}%)` : ''}{row.auto ? ' · paid by the card from profit' : row.mode ? ` · ${row.mode}` : ''}</span>
        <small className="m-dim">wallet {row.wallet?.slice(0, 4)}…{row.wallet?.slice(-4)} · {new Date(row.at * 1000).toLocaleString()}</small>{row.sig && <a href={txUrl(row.sig)} target="_blank" rel="noreferrer">Open the transaction ↗</a>}</div>}
      <div className="fw-table" role="table" data-testid="ff-list"><div className="fw-row is-head" role="row"><span>WHEN</span><span>TYPE</span><span>CARD</span><span>COIN</span><span>TRADE</span><span>FEE</span><span>TX</span></div>
        {rows.map((r, i) => <button key={i} type="button" className="fw-row" role="row" onClick={() => setRow(r)} data-testid={`ff-row-${i}`}><span className="m-dim">{new Date(r.at * 1000).toLocaleDateString()}</span><span>{r.kind}</span><span>{r.cardName}</span>
          <span>{r.symbol ? `$${r.symbol}` : '—'}</span><span className="m-num">{r.tradeUsd ? usd(r.tradeUsd) : '—'}</span><span className="m-num">{usd(r.feeUsd)}</span><span className="m-dim">{r.sig ? '↗' : '—'}</span></button>)}
        {!rows.length && <small className="m-dim">No fees of this type yet.</small>}</div></div>
  </section>;
}
