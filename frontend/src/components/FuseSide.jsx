import React, { Suspense, lazy, useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// The one Fuse chat, beside the Fuse Lab card. Anyone can chat; slide over to the Holders board (verified Fuse positions,
// live P&L). Two panes on one track — the switch is a transform slide, nothing re-mounts the chat.
const EcosystemChat = lazy(() => import('./EcosystemChat'));
const pct = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;

export function FuseSide() {
  const [pane, setPane] = useState('chat');
  const [h, setH] = useState(null); const [cr, setCr] = useState(null);
  useEffect(() => {
    if (pane === 'chat') return undefined;
    let alive = true; const load = () => fetch(apiUrl(`/api/reputation/fuses/${pane}`)).then(r => r.json()).then(d => alive && (pane === 'holders' ? setH : setCr)(d)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000);
    return () => { alive = false; clearInterval(t); };
  }, [pane]);
  return <aside className="m-card fside" data-testid="fuse-side">
    <div className="fside-tabs" role="tablist" data-pane={pane}><i className="fside-ink" aria-hidden="true" />
      <button type="button" role="tab" aria-selected={pane === 'chat'} onClick={() => setPane('chat')} data-testid="fside-chat">💬 Fuse chat</button>
      <button type="button" role="tab" aria-selected={pane === 'holders'} onClick={() => setPane('holders')} data-testid="fside-holders">🏆 Holders{h?.total ? ` · ${h.total}` : ''}</button>
      <button type="button" role="tab" aria-selected={pane === 'creators'} onClick={() => setPane('creators')} data-testid="fside-creators" data-tip="This week's Fuse creators, ranked by how their buyers actually did">🏅 Creators</button></div>
    <div className="fside-view"><div className={`fside-track at-${pane}`}>
      <div className="fside-pane" aria-hidden={pane !== 'chat'}><Suspense fallback={<div className="fl-row is-ghost" />}><EcosystemChat compact room="fuse-lab" ecosystem={{ id: 'fuse-lab', name: 'Fuse' }} /></Suspense></div>
      <div className="fside-pane" aria-hidden={pane !== 'holders'}>
        {!h ? <div className="fl-row is-ghost" /> : !h.holders.length ? <p className="m-dim fside-empty">No Fuse holders yet — be the first: ⚡ Fuse in, then you show up here.</p>
          : <ol className="fside-holders">{h.holders.map((x, i) => <li key={x.address}><span className="fside-rank">{i + 1}</span>
            <a href={`/terminal/profile/${x.address}`}><b>{x.handle ? `@${x.handle}` : `${x.address.slice(0, 4)}…${x.address.slice(-4)}`}</b><small className="m-dim">{x.fuses} fuse{x.fuses === 1 ? '' : 's'} · {x.names.join(' · ')}</small></a>
            <b className={`m-num ${x.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(x.pnlPct)}</b></li>)}</ol>}
      </div>
      <div className="fside-pane" aria-hidden={pane !== 'creators'}>
        {!cr ? <div className="fl-row is-ghost" /> : <>
          <p className="fside-season">🏅 CREATOR SEASON · ends {new Date(cr.endsAt * 1000).toLocaleDateString(undefined, { weekday: 'short' })} · ranked by buyers' real P&L (min {cr.minBuyers} buyers, own buys don't count)</p>
          {!cr.rows.length ? <p className="m-dim fside-empty">No creator has buyers this week yet. Publish a Fuse, share it with /fuse in chat.</p>
            : <ol className="fside-holders">{cr.rows.map((x, i) => <li key={x.creator} className={x.ranked ? '' : 'is-unranked'}><span className="fside-rank">{x.ranked ? i + 1 : '–'}</span>
              <a href={`/terminal/profile/${x.creator}`}><b>{x.handle ? `@${x.handle}` : `${x.creator.slice(0, 4)}…${x.creator.slice(-4)}`}</b><small className="m-dim">{x.buyers} buyer{x.buyers === 1 ? '' : 's'} · {x.winRate}% up · {x.fuses.join(' · ')}</small></a>
              <b className={`m-num ${x.pnlPct >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(x.pnlPct)}</b></li>)}</ol>}
        </>}
      </div>
    </div></div>
  </aside>;
}
