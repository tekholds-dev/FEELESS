import React, { useEffect, useRef, useState } from 'react';
import { useSolUsd, money } from './FeeInputs';
import { useMoneyPulse, refreshPulse } from '../../lib/moneyPulse';

// Header strip, fed by the ONE money pulse (lib/moneyPulse): fees today, unsplit fees, money ready to pay out,
// and the preflight (everything a real-money trade depends on). Click READY for every check + its fix.
export function TreasuryPulse({ call, onOpen }) {
  const px = useSolUsd();
  const { data: d, error, at } = useMoneyPulse(call);
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const close = e => { if (!box.current?.contains(e.target)) setOpen(false); };
    const esc = e => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);
  if (!d) return error ? <div className="tr-pulse"><button type="button" onClick={() => refreshPulse(true)}><small>MONEY PULSE</small><b className="m-neg">retry</b></button></div> : null;
  const fee = k => d.feeAccounts?.find(f => f.asset === k)?.amount || 0;
  const wsol = fee('wSOL'); const usdc = fee('USDC');
  const unsplitUsd = (px ? wsol * px : 0) + usdc;
  const checks = (d.checks || []).filter(c => !c.info);
  const good = checks.filter(c => c.ok).length;
  const ready = (d.alerts || []).filter(a => a.tone === 'ok').length;
  const needs = (d.alerts || []).filter(a => a.tone !== 'ok').length;
  const ago = Math.max(0, Math.round((Date.now() - at) / 1000));
  return <div className="tr-pulse" data-testid="treasury-pulse" ref={box}>
    <button type="button" onClick={() => onOpen('fees')} title="Trading & fees"><small>FEES TODAY</small><b>{money(d.feesTodayUsd || 0)}</b><em>{money(d.fees7dUsd || 0)} · 7d</em></button>
    <button type="button" className={wsol + usdc > 0 ? 'hot' : ''} onClick={() => onOpen('treasury', { asset: wsol >= usdc ? 'wSOL' : 'USDC', amount: String(wsol >= usdc ? wsol : usdc) })} title="Split now">
      <small>UNSPLIT</small><b>{wsol ? `${wsol.toFixed(3)} SOL` : ''}{wsol && usdc ? ' + ' : ''}{usdc ? `$${usdc.toFixed(2)}` : ''}{!wsol && !usdc ? '0' : ''}</b>{unsplitUsd > 0 && <em>{money(unsplitUsd)} → split</em>}</button>
    <button type="button" className={ready ? 'hot' : ''} onClick={() => onOpen('reserve')} title="Reserve & badge pools"><small>PAYOUTS</small><b>{ready ? `${ready} ready` : 'none due'}</b>{needs > 0 && <em className="m-neg">{needs} need you</em>}</button>
    <button type="button" className={`tr-ready ${good === checks.length ? 'ok' : 'bad'}`} aria-expanded={open} onClick={() => setOpen(v => !v)} data-testid="pulse-ready"><small>READY</small><b>{good}/{checks.length}</b><em>{ago < 5 ? 'live' : `${ago}s ago`}</em></button>
    {open && <div className="m-card m-pop pulse-panel" role="dialog" aria-label="Money preflight">
      <div className="m-row"><span className="m-label">MONEY PREFLIGHT <em>everything a real trade depends on</em></span><button type="button" className="m-btn" onClick={() => refreshPulse(true)}>↻ Re-check</button></div>
      <ul className="pulse-checks">{(d.checks || []).map(c => <li key={c.key} className={c.info ? 'info' : c.ok ? 'ok' : 'bad'}><i>{c.info ? '·' : c.ok ? '✓' : '!'}</i><span><b>{c.label}</b>{c.detail && <small>{c.detail}</small>}{!c.ok && c.fix && <small>{c.fix}</small>}</span></li>)}</ul>
      {(d.alerts || []).length > 0 && <><span className="m-label">NUDGES</span>
        <div className="m-stack">{d.alerts.map((a, i) => <button key={i} type="button" className={`m-note ${a.tone === 'ok' ? '' : a.tone}`} onClick={() => { setOpen(false); onOpen(a.tab); }}>{a.text} →</button>)}</div></>}
    </div>}
  </div>;
}
