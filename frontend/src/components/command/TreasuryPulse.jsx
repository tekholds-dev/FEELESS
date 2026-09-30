import React, { useEffect, useState } from 'react';
import { useSolUsd, money } from './FeeInputs';

// Command Center header ticker: fees landed today, fees waiting to be split, pools ready to pay.
// One click jumps to the right tab with the split amount filled in. Polls once a minute.
export function TreasuryPulse({ call, onOpen }) {
  const px = useSolUsd();
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => Promise.all([call('/admin/fees/earnings').catch(() => null), call('/admin/treasury/money').catch(() => null), call('/admin/badge-pools').catch(() => null)])
      .then(([earn, m, pools]) => alive && setD({ earn, m, pools }));
    load(); const t = setInterval(load, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [call]);
  if (!d) return null;
  const today = d.earn?.trades?.day;
  const wsol = d.m?.feeAccounts?.find(f => f.asset === 'wSOL')?.amount || 0;
  const usdc = d.m?.feeAccounts?.find(f => f.asset === 'USDC')?.amount || 0;
  const unsplitUsd = (px ? wsol * px : 0) + usdc;
  const pools = d.pools?.pools?.length || 0;
  return <div className="tr-pulse" data-testid="treasury-pulse">
    <button type="button" onClick={() => onOpen('fees')} title="Trading & fees"><small>FEES TODAY</small><b>{today != null ? money(today) : '—'}</b></button>
    <button type="button" className={wsol + usdc > 0 ? 'hot' : ''} onClick={() => onOpen('treasury', { asset: wsol >= usdc ? 'wSOL' : 'USDC', amount: String(wsol >= usdc ? wsol : usdc) })} title="Split now">
      <small>UNSPLIT</small><b>{wsol ? `${wsol.toFixed(3)} SOL` : ''}{wsol && usdc ? ' + ' : ''}{usdc ? `$${usdc.toFixed(2)}` : ''}{!wsol && !usdc ? '0' : ''}</b>{unsplitUsd > 0 && <em>{money(unsplitUsd)} → split</em>}</button>
    <button type="button" onClick={() => onOpen('badges')} title="Badge pools"><small>BADGE POOLS</small><b>{pools}</b></button>
  </div>;
}
