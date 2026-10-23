import React, { useState } from 'react';
import { useWallet } from '../hooks/useWallet';
import { useLpPositions, lpAction } from '../lib/lpPositions';
import { dollarsSmall as cash } from '../lib/cityPlan';   // small money keeps its cents ($12.50, not $13)
import '../styles/lpPositions.css';

// 🏗 YOUR LP POSITIONS (owner, 2026-10-23: "show my LP positions as live buildings — fees earned, in range or not — with claim / remove / close
// in place"): one card per position (the family block's pop-out, the money desk's list). Value now (both sides at the pool's own price), the fees
// it earned and hasn't claimed, IN RANGE = earning, today's pace a day; Claim · Remove (keep the position) · Close (remove + close, rent back) —
// built with Meteora's SDK, simulated first, your wallet signs.
const ACTS = [['claim', '💰 Claim fees', 'Send the fees this position earned to your wallet — the position keeps earning'],
  ['remove', '↩ Remove all', 'Take all the liquidity back to your wallet (SOL + the coin) — the position stays open, empty'],
  ['close', '✕ Close', 'Remove everything AND close the position — its rent comes back to you']];
export function LpPositionCard({ p }) {
  const { wallet, provider } = useWallet() || {}; const mine = wallet?.chain === 'solana' && wallet?.address;
  const [busy, setBusy] = useState(null); const [st, setSt] = useState(''); const [done, setDone] = useState(null); const [err, setErr] = useState('');
  const run = async act => {
    if (act !== 'claim' && !window.confirm(act === 'close' ? `Remove everything from ${p.sym} and close the position?` : `Take all your liquidity out of ${p.sym}?`)) return;
    setBusy(act); setErr(''); setDone(null);
    try { const r = await lpAction({ provider, owner: wallet.address, position: p.position, act, onStatus: setSt }); setDone({ act, ...r }); } catch (e) { setErr(e.code === 4001 ? 'Declined in the wallet — nothing was sent.' : e.message); }
    setSt(''); setBusy(null);
  };
  const day = p.feeDay != null && p.valueUsd ? p.valueUsd * p.feeDay : null;
  return <div className={`lpc ${p.inRange ? 'is-in' : 'is-out'} ${p.empty ? 'is-empty' : ''}`} data-testid={`lp-card-${p.id}`}>
    <div className="lpc-head"><span><b>{p.sym}</b><small>Meteora DAMM v2 · position {p.position.slice(0, 4)}…{p.position.slice(-4)}</small></span>
      <em className="lpc-range" data-tip={p.inRange ? 'The price sits inside the pool\'s range: every trade pays this position' : 'The price left the pool\'s range: this position earns nothing until it comes back'}>{p.empty ? 'EMPTY' : p.inRange ? '● IN RANGE' : '○ OUT OF RANGE'}</em></div>
    <div className="lpc-tiles">
      <span style={{ '--i': 0 }}><em>WORTH NOW</em><b className="m-num">{p.valueUsd != null ? cash(p.valueUsd) : `${p.valueSol.toFixed(4)} SOL`}</b><small>{p.solAmt.toFixed(4)} SOL + {p.coinAmt.toLocaleString('en-US', { maximumFractionDigits: 2 })} {p.coinSym}</small></span>
      <span style={{ '--i': 1 }} className="is-hot"><em>FEES EARNED</em><b className="m-num">+{p.feeUsd != null ? cash(p.feeUsd) : `${p.feeValueSol.toFixed(5)} SOL`}</b><small>unclaimed · yours to claim</small></span>
      <span style={{ '--i': 2 }}><em>PACE</em><b className="m-num">{p.feeDay != null ? `${(p.feeDay * 100).toFixed(1)}%/d` : '—'}</b><small>{day != null ? `≈ +${cash(day)} a day` : 'the pool\'s 24h fees'}</small></span>
    </div>
    <div className="lpc-acts">{ACTS.map(([k, w, tip]) => <button key={k} type="button" className={`m-btn ${k === 'claim' ? 'm-go' : ''}`} disabled={!mine || !!busy || (k === 'claim' && !(p.feeValueSol > 0)) || (k !== 'claim' && p.empty)}
      onClick={() => run(k)} data-tip={mine ? tip : 'Connect the wallet that holds this position'} data-testid={`lp-${k}-${p.id}`}>{busy === k ? '…' : w}</button>)}</div>
    {st ? <p className="lpc-st" aria-live="polite"><i />{st}</p> : null}
    {done ? <p className="lpc-ok" data-testid="lp-done">✅ {done.act === 'claim' ? 'Fees claimed' : done.act === 'close' ? 'Position closed — your coins + rent are back' : 'Liquidity removed'} · tx {done.signature.slice(0, 8)}…</p> : null}
    {err ? <p className="lpc-err" role="alert">{err}</p> : null}
  </div>;
}

export function LpPositions({ owner = null, compact = false }) {
  const { wallet } = useWallet() || {}; const who = owner || (wallet?.chain === 'solana' ? wallet.address : null);
  const rows = useLpPositions(who); const [open, setOpen] = useState(null);
  if (!who || !rows || !rows.length) return null;
  const total = rows.reduce((s, p) => s + (p.valueUsd || 0), 0); const fees = rows.reduce((s, p) => s + (p.feeUsd || 0), 0); const live = rows.filter(p => p.inRange && !p.empty).length;
  return <div className={`lpl ${compact ? 'is-compact' : ''}`} data-testid="lp-list">
    <div className="lpl-head"><b>🏗 YOUR POSITIONS</b><small>{rows.length} · {live} earning · {cash(total)} in pools · +{cash(fees)} fees to claim</small></div>
    <ol>{rows.map((p, i) => <li key={p.id} style={{ '--i': i }} className={p.inRange && !p.empty ? 'is-in' : 'is-out'}>
      <button type="button" className="lpl-row" aria-expanded={open === p.id} onClick={() => setOpen(x => (x === p.id ? null : p.id))} data-testid={`lp-row-${p.id}`} data-tip="Open it: claim, remove or close right here">
        <i aria-hidden="true" /><span><b>{p.sym}</b><small>{p.inRange ? 'earning' : 'out of range'}</small></span><strong className="m-num">{p.valueUsd != null ? cash(p.valueUsd) : '—'}</strong><em className="m-num">+{p.feeUsd != null ? cash(p.feeUsd) : '—'}</em></button>
      {open === p.id ? <LpPositionCard p={p} /> : null}</li>)}</ol>
  </div>;
}
