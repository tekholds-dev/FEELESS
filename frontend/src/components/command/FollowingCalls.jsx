import React, { useEffect, useState } from 'react';
import { Users } from 'lucide-react';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';

const ago = ts => { const s = Math.max(0, Date.now() / 1000 - ts); return s < 3600 ? `${Math.max(1, Math.floor(s / 60))}m` : `${Math.floor(s / 3600)}h`; };

// Copy callers: every call from a wallet you follow, with its record, one tap from a pre-quoted buy.
export function FollowingCalls() {
  const { wallet } = useWallet() || {};
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!wallet?.address) { setD(null); return undefined; }
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/calls/following/${wallet.address}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [wallet?.address]);
  if (!wallet?.address) return null;
  return <aside className="top-pump following-calls" data-testid="following-calls">
    <header><span><Users size={15} /> Calls you follow</span><small>{d ? `${d.following} callers` : '…'}</small></header>
    {!d ? <p className="top-pump-empty">Loading…</p>
      : !d.following ? <p className="top-pump-empty">Follow top callers from the league to copy their calls here.</p>
        : !d.calls.length ? <p className="top-pump-empty">No calls from them in the last 24h.</p>
          : <ol>{d.calls.slice(0, 8).map(c => { const url = `/terminal/chat?chain=${c.chain}&pair=${c.pairAddress}&room=bulls`; return <li key={c.id} className="fc-row">
            <a href={url} className="fc-coin"><b>${c.symbol}</b><small>{c.caller}{c.callerHitRate != null ? ` · ${Math.round(c.callerHitRate * 100)}% hits` : ''} · {ago(c.at)}</small></a>
            <span className={`fc-x ${(c.x || 1) >= 1 ? 'up' : 'down'}`}>{c.x ? `${c.x.toFixed(2)}x` : '—'}</span>
            <a className="fc-buy" href={`${url}&buy=1`}>Buy</a></li>; })}</ol>}
  </aside>;
}
