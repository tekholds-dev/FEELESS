import React, { useState } from 'react';
import { useFuses } from '../lib/fuseFeed';
import { splitSol } from './FusePanel';
import { FuseGo } from './FuseGo';

// A live Fuse in chat (`/fuse`): fits a 360px chat column, live index + grade + weights from the shared poll,
// pick an amount → one-click Fuse in (one wallet approval). Never rendered for an unknown id.
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);

export function FuseChatCard({ id }) {
  const f = (useFuses() || []).find(x => x.id === id);
  const [amt, setAmt] = useState(null);
  if (!f) return null;
  const up = f.index >= 100;
  return <div className="fcc" data-testid={`fuse-chat-${id}`}>
    <div className="fcc-head"><span className="fcc-emoji">{f.emoji}</span><b>{f.name}</b><span className={`fl-grade g-${f.score.grade}`} title={f.score.parts.map(p => `${p.part}: ${p.why}`).join('\n')}>{f.score.grade}</span></div>
    <div className="fl-bar fcc-bar">{f.legs.map(l => <i key={l.pairAddress} style={{ flexGrow: l.weight }} title={`${l.symbol} ${l.weight}%`}><span>{l.symbol}</span></i>)}</div>
    <div className="fcc-kpis"><span><small>INDEX</small><b className={`m-num ${up ? 'm-pos' : 'm-neg'}`}>{f.index.toFixed(1)}</b></span><span><small>DEPTH</small><b className="m-num">{usd(f.tvlUsd)}</b></span>
      <span><small>APR EST</small><b className="m-num m-pos">{Math.round(f.aprEst)}%</b></span><span><small>BUYS</small><b className="m-num">{f.stats?.buys || 0}</b></span></div>
    {amt == null ? <div className="fcc-go"><div className="m-seg">{[0.1, 0.5, 1].map(v => <button type="button" key={v} onClick={() => setAmt(v)} data-testid={`fcc-amt-${v}`}>{v} SOL</button>)}</div><small className="m-dim">⚡ one approval</small></div>
      : <FuseGo legs={splitSol(amt, f.legs).map(l => ({ ...l, sol: l.sol }))} fuse={{ id: f.id, name: f.name }} onClose={() => setAmt(null)} />}
  </div>;
}
