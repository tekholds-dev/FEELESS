import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiUrl } from '../lib/api';

const ago = ts => { const s = Date.now() / 1000 - ts; return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
export const tradeHref = t => `/terminal/trade?chain=${encodeURIComponent(t.chain)}&pair=${encodeURIComponent(t.pair || t.token)}`;

// A wallet's real recent swaps (Codex, every chain it trades on), each one click from the trade desk.
export function WalletSwaps({ address, title = 'Swaps', limit = 12, onMirror }) {
  const [rows, setRows] = useState(null);
  const navigate = useNavigate();
  useEffect(() => {
    if (!address) return undefined;
    let alive = true;
    fetch(apiUrl(`/api/reputation/wallet-trades/${address}`)).then(r => r.json()).then(d => alive && setRows(d.trades || [])).catch(() => alive && setRows([]));
    return () => { alive = false; };
  }, [address]);
  return <section className="wallet-swaps" data-testid="wallet-swaps">
    <h4>{title}</h4>
    {rows == null ? <p className="wp-bio">Reading swaps…</p> : !rows.length ? <p className="wp-bio">No swaps found for this wallet yet.</p> :
      rows.slice(0, limit).map(t => <div key={t.tx + t.token} className={`ws-row ${t.side}`}>
        {t.imageUrl ? <img src={t.imageUrl} alt="" /> : <span className="ws-dot" />}
        <b>{t.side === 'buy' ? 'Bought' : 'Sold'} ${t.symbol}</b>
        <span>${Number(t.usd).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        <small>{t.chain} · {ago(t.ts)}</small>
        <button type="button" className="btn-outline" disabled={onMirror && onMirror.disabled} onClick={() => (onMirror?.fn ? onMirror.fn(t) : navigate(tradeHref(t)))}>{onMirror ? 'Mirror' : 'Trade'}</button>
      </div>)}
  </section>;
}
