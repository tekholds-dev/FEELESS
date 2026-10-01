import React, { Suspense, lazy, useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// The one Fuse chat, beside the Fuse Lab card. Anyone can chat; slide over to the Holders board (verified Fuse positions,
// live P&L). Two panes on one track — the switch is a transform slide, nothing re-mounts the chat.
const EcosystemChat = lazy(() => import('./EcosystemChat'));
const pct = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;

export function FuseSide() {
  const [pane, setPane] = useState('chat');
  const [h, setH] = useState(null);
  useEffect(() => {
    if (pane !== 'holders') return undefined;
    let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/holders')).then(r => r.json()).then(d => alive && setH(d)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000);
    return () => { alive = false; clearInterval(t); };
  }, [pane]);
  return <aside className="m-card fside" data-testid="fuse-side">
    <div className="fside-tabs" role="tablist" data-pane={pane}><i className="fside-ink" aria-hidden="true" />
      <button type="button" role="tab" aria-selected={pane === 'chat'} onClick={() => setPane('chat')} data-testid="fside-chat">💬 Fuse chat</button>
      <button type="button" role="tab" aria-selected={pane === 'holders'} onClick={() => setPane('holders')} data-testid="fside-holders">🏆 Holders{h?.total ? ` · ${h.total}` : ''}</button></div>
    <div className="fside-view"><div className={`fside-track at-${pane}`}>
      <div className="fside-pane" aria-hidden={pane !== 'chat'}><Suspense fallback={<div className="fl-row is-ghost" />}><EcosystemChat compact room="fuse-lab" ecosystem={{ id: 'fuse-lab', name: 'Fuse' }} /></Suspense></div>
      <div className="fside-pane" aria-hidden={pane !== 'holders'}>
        {!h ? <div className="fl-row is-ghost" /> : !h.holders.length ? <p className="m-dim fside-empty">No Fuse holders yet — be the first: ⚡ Fuse in, then you show up here.</p>
          : <ol className="fside-holders">{h.holders.map((x, i) => <li key={x.address}><span className="fside-rank">{i + 1}</span>
            <a href={`/terminal/profile/${x.address}`}><b>{x.handle ? `@${x.handle}` : `${x.address.slice(0, 4)}…${x.address.slice(-4)}`}</b><small className="m-dim">{x.fuses} fuse{x.fuses === 1 ? '' : 's'} · {x.names.join(' · ')}</small></a>
            <b className={`m-num ${x.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(x.pnlPct)}</b></li>)}</ol>}
      </div>
    </div></div>
  </aside>;
}
