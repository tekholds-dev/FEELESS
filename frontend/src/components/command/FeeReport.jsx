import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';

// FEE REPORT: what this wallet paid in FEELESS fees over the last 7 days and in total, plus the FeeBack it has
// accrued. Numbers come from the fee ledger the trading service writes for every confirmed trade.
const usd = v => (v == null ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : v >= 1 ? `$${v.toFixed(2)}` : v > 0 ? `$${v.toFixed(3)}` : '$0');
const DAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

// Also opens as a hover card on the Fee-Back tab (FeeReportChip).
export function FeeReport({ address }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true; setD(null);
    const load = () => fetch(apiUrl(`/api/reputation/fee-report/${address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load();
    const onTrade = () => setTimeout(load, 4000);   // the fee lands in the ledger once the server confirms the trade
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => { alive = false; window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [address]);
  const days = Array.isArray(d?.days) ? d.days : Array(7).fill(0);
  const peak = Math.max(...days, 0);
  const today = new Date().getDay();
  return <div className="m-card is-hot fee-report m-pop" data-testid="fee-report">
    <div className="m-label">FEE REPORT <em>7 days</em></div>
    <div className="fr-top">
      <div className="m-stat"><small>Fees paid · 7d</small><b className="m-num">{d ? usd(d.fees7dUsd) : '…'}</b><span className="m-dim">{d ? `${d.fees7dSol ? `${d.fees7dSol.toFixed(4)} SOL · ` : ''}${d.trades7d} trade${d.trades7d === 1 ? '' : 's'} · ${usd(d.volume7dUsd)} vol` : ''}</span></div>
      <div className="m-bars" aria-label="Fees per day, last 7 days">{days.map((v, i) => <i key={i} className={v ? '' : 'zero'} style={{ transform: `scaleY(${peak ? Math.max(0.08, v / peak) : 0.08})` }} title={`${DAYS[(today - 6 + i + 7) % 7]} · ${usd(v)}`} />)}</div>
    </div>
    <div className="fr-row"><div className="m-stat"><small>All-time fees</small><b className="m-num sm">{d ? usd(d.feesTotalUsd) : '…'}</b></div>
      <div className="m-stat"><small>FeeBack accrued</small><b className="m-num sm m-pos">{d ? usd(d.feeBackUsd) : '…'}</b></div></div>
    <div className="fr-row"><div className="m-stat"><small>Paid back so far</small><b className="m-num sm">{d ? usd(d.feeBackPaidUsd) : '…'}</b></div>
      <div className="m-stat"><small>Still owed to you</small><b className="m-num sm m-pos">{d ? usd(d.feeBackOwedUsd) : '…'}</b></div>
      <div className="m-stat"><small>Of your fees back</small><b className="m-num sm">{d ? `${d.paidBackPct}%` : '…'}</b></div></div>
    {d?.earned && <div className="fr-earned" data-testid="fee-report-earned"><div className="m-label">EARNED WHILE TRADING</div>
      <div className="fr-row"><div className="m-stat"><small>XP · level</small><b className="m-num sm">{(d.earned.xp ?? 0).toLocaleString()} · {d.earned.level || 'Rookie'}</b></div>
        <div className="m-stat"><small>Rep</small><b className="m-num sm">{d.earned.rep?.score ?? '—'}{d.earned.rep?.label ? ` · ${d.earned.rep.label}` : ''}</b></div>
        <div className="m-stat"><small>Points</small><b className="m-num sm">{(d.earned.points ?? 0).toLocaleString()}</b></div></div>
      {d.earned.badgeFeeDiscountPct > 0 && <span className="m-chip ok">🏅 {d.earned.badgeFeeFrom} badge: −{d.earned.badgeFeeDiscountPct}% on every fee</span>}</div>}
    <span className="m-chip ok">🐱 {d?.feeBackPct ?? 100}% of $FEE · FEECAT · rFEE trade fees back in FEECAT · other coins earn none · paid when FeeBack goes live</span>
  </div>;
}

// Fee-Back tab: a chip that opens the full fee report on hover / focus / tap.
export function FeeReportChip({ address }) {
  const [open, setOpen] = useState(false);
  if (!address) return null;
  return <span className={`fr-chip ${open ? 'is-open' : ''}`} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)} data-testid="fee-report-chip">
    <button type="button" className="m-btn" aria-expanded={open} onClick={() => setOpen(o => !o)} onFocus={() => setOpen(true)}>📊 Your fee report</button>
    {open && <span className="fr-pop"><FeeReport address={address} /></span>}</span>;
}
