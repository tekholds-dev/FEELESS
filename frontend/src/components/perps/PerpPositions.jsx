import React, { useState } from 'react';
import { toast } from 'sonner';
import { useGlide } from '../../lib/useGlide';
import { liveRow, post, signRun } from '../../lib/perps';

// 📋 YOUR POSITIONS (Jupiter Perps), marked on every print of the true price: P&L before fees (fees apart), ROE on the collateral, the
// distance to ☠ liquidation as a meter, its TP / SL (edit the price · cancel · add one), and close 25 / 50 / 75 / 100 % — every action is a
// Jupiter-built transaction the wallet signs (backend/jup_perps.py verifies it first).
const px = v => (v == null || !Number.isFinite(v) ? '—' : v >= 1000 ? `$${v.toLocaleString('en-US', { maximumFractionDigits: 1 })}` : `$${Number(v).toFixed(v >= 10 ? 2 : 4)}`);
const $ = v => (v == null || !Number.isFinite(v) ? '—' : `${v < 0 ? '−' : '+'}$${Math.abs(v).toFixed(2)}`);

function Pnl({ v, pct }) { const g = useGlide(v == null ? null : Math.round(v * 100) / 100, 400);
  return <span className={`pp-pnl ${(v ?? 0) >= 0 ? 'is-up' : 'is-dn'}`}><b className="m-num" key={Math.round((v || 0) * 20)}>{$(g)}</b><small className="m-num">{pct == null ? '' : `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% ROE`}</small></span>; }

export function PerpPositions({ positions, marks, addr, provider, wallet, connect, reload, onPick }) {
  const [busy, setBusy] = useState(''); const [edit, setEdit] = useState(null); const [add, setAdd] = useState(null);
  const run = async (label, body) => {
    if (!wallet?.address || !provider) { await connect?.('solana'); return; }
    setBusy(label);
    try { const b = await post('/api/reputation/familia/perps-real', { address: addr, ...body }); await signRun(provider, addr, b); toast.success(`✅ ${label} — done`); setEdit(null); setAdd(null); reload?.(); }
    catch (e) { toast.error(e.message); } finally { setBusy(''); }
  };
  if (!positions.length) return <div className="pp-empty" data-testid="pp-empty"><b>FLAT</b><small>no open positions</small></div>;
  return <ol className="pp" data-testid="perp-positions">{positions.map((p0, i) => { const p = liveRow(p0, marks?.[p0.asset]);
    const safe = p.toLiq == null ? 0 : Math.min(1, p.toLiq / 50);
    return <li key={p.pubkey} className={`pp-row ${(p.pnl ?? 0) >= 0 ? 'is-up' : 'is-dn'}`} style={{ '--i': i }} data-testid={`pp-${i}`}>
      <button type="button" className={`pp-mkt is-${p.side}`} onClick={() => onPick?.(p.asset)} data-tip={`Show ${p.asset} on the chart`}><b>{p.side === 'long' ? '▲' : '▼'} {p.asset}</b><small>{p.lev}× · {px(p.size)}</small></button>
      <span className="pp-k"><em>ENTRY</em><b className="m-num">{px(p.entry)}</b></span>
      <span className="pp-k"><em>MARK</em><b className="m-num">{px(p.live)}</b></span>
      <Pnl v={p.pnl} pct={p.pnlPct} />
      <span className="pp-liq" data-tip={`☠ liquidation at ${px(p.liq)}`}><em>☠ {px(p.liq)}</em><u><s style={{ transform: `scaleX(${Math.max(0.03, safe)})` }} /></u><small className="m-num">{p.toLiq != null ? `${p.toLiq.toFixed(1)}% away` : ''}</small></span>
      <span className="pp-tpsl">{(p.tpsl || []).map(o => <span key={o.id} className={`pp-ord is-${o.kind}`}>
        {edit?.id === o.id ? <><input type="number" step="any" value={edit.price} onChange={e => setEdit({ ...edit, price: e.target.value })} aria-label="New trigger price" />
          <button type="button" disabled={!!busy} onClick={() => run(`${o.kind.toUpperCase()} moved`, { act: 'tpsl-edit', positionRequestPubkey: o.id, price: Number(edit.price) })} data-tip="Save the new trigger">✓</button></>
          : <button type="button" className="pp-chip" onClick={() => setEdit({ id: o.id, price: o.price || '' })} data-tip="Move this trigger"><b>{o.kind.toUpperCase()}</b> {px(o.price)}</button>}
        <button type="button" className="pp-x" disabled={!!busy} onClick={() => run(`${o.kind.toUpperCase()} cancelled`, { act: 'tpsl-cancel', positionRequestPubkey: o.id })} aria-label={`Cancel ${o.kind}`} data-tip="Cancel it">✕</button></span>)}
        {(p.tpsl || []).length < 2 ? (add === p.pubkey ? <AddTpsl p={p} busy={busy} onSave={b => run('TP / SL armed', { act: 'tpsl-add', positionPubkey: p.pubkey, side: p.side, mark: p.live, ...b })} />
          : <button type="button" className="pp-add" onClick={() => setAdd(p.pubkey)} data-tip="Arm a take profit / stop loss on this position" data-testid={`pp-add-${i}`}>+ TP/SL</button>) : null}</span>
      <span className="pp-close m-seg" role="group" aria-label="Close">{[25, 50, 75, 100].map(n => <button key={n} type="button" disabled={!!busy} onClick={() => run(n === 100 ? `${p.asset} closed` : `${n}% of ${p.asset} closed`, { act: 'close', positionPubkey: p.pubkey, pct: n, size: p.size })}
        data-tip={n === 100 ? 'Close it all — USDC back to your wallet' : `Close ${n}% — the rest stays open`} data-testid={`pp-close-${i}-${n}`}>{n === 100 ? 'CLOSE' : `${n}%`}</button>)}</span>
    </li>; })}</ol>;
}

function AddTpsl({ p, busy, onSave }) {
  const [tp, setTp] = useState(''); const [sl, setSl] = useState('');
  return <span className="pp-addf"><input type="number" step="any" placeholder="TP $" value={tp} onChange={e => setTp(e.target.value)} aria-label="Take profit price" />
    <input type="number" step="any" placeholder="SL $" value={sl} onChange={e => setSl(e.target.value)} aria-label="Stop loss price" />
    <button type="button" disabled={!!busy || !(Number(tp) || Number(sl))} onClick={() => onSave({ ...(Number(tp) ? { tp: Number(tp) } : {}), ...(Number(sl) ? { sl: Number(sl) } : {}) })} data-tip={`Arm it on ${p.asset}`}>ARM</button></span>;
}
