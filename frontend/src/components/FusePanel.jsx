import React, { useEffect, useState } from 'react';
import NumInput from './NumInput';
import { apiUrl } from '../lib/api';
import { resolveCoin } from '../lib/resolveCoin';
import { readChatSession } from '../lib/chatSession';
import { useWallet } from '../hooks/useWallet';
import { QuickTrade } from './terminal/QuickTrade';
import { FuseLab } from './FuseLab';
import { FuseSide } from './FuseSide';

// ⚛️ FUSE: fused pools. Each card is a basket of live pools with weights — one grade, one index, combined depth.
// "Fuse in" splits your SOL by weight; each leg is a normal Quick trade your wallet signs. Confirmed legs are
// reported so the Fuse's creator earns their share of the FEELESS fee (the server checks the trade is yours).
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);
export function splitSol(amount, legs) {
  const a = Number(amount); if (!(a > 0) || !legs?.length) return [];
  const parts = legs.map(l => ({ ...l, sol: Math.round(a * l.weight / 100 * 1e6) / 1e6 }));
  const diff = Math.round((a - parts.reduce((s, p) => s + p.sol, 0)) * 1e6) / 1e6;
  if (diff) { const big = parts.reduce((x, y) => (y.sol > x.sol ? y : x)); big.sol = Math.round((big.sol + diff) * 1e6) / 1e6; }
  return parts;
}

export function FuseLeg({ leg, sol, fuseId }) {
  const [pair, setPair] = useState(null); const [open, setOpen] = useState(false);
  const { wallet } = useWallet() || {};
  useEffect(() => { if (open && !pair) resolveCoin(leg.chainId, leg.pairAddress).then(setPair).catch(() => {}); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open || !pair || !fuseId) return undefined;
    // A confirmed buy of this leg's coin while it's open counts toward the Fuse (retried: the fill is read from chain first).
    const onTrade = e => { const d = e.detail || {}; const s = wallet?.address && readChatSession(wallet.address);
      if (!s || !d.signature || d.side === 'sell' || d.mint !== pair.baseToken?.address) return;
      [6000, 25000].forEach(ms => setTimeout(() => fetch(apiUrl(`/api/reputation/fuses/${fuseId}/buy`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ address: wallet.address, session: s, signature: d.signature }) }).catch(() => {}), ms)); };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => window.removeEventListener('feeless:trade-confirmed', onTrade);
  }, [open, pair, fuseId, wallet?.address]);
  return <div className="fz-leg-buy"><button type="button" className={`m-btn ${open ? '' : 'primary m-go'}`} onClick={() => setOpen(o => !o)} data-testid={`fuse-leg-${leg.pairAddress}`}>{open ? 'Close' : `Buy ${leg.symbol || 'leg'} · ${sol} SOL`}</button>
    {open && (pair ? <QuickTrade pair={pair} /> : <span className="loader" />)}</div>;
}

export function FuseCard({ f }) {
  const [amount, setAmount] = useState('');
  const [going, setGoing] = useState(false);
  const parts = splitSol(amount, f.legs);
  return <article className={`m-card fz-card grade-${f.score.grade}`} data-testid={`fuse-${f.id}`}>
    <header className="fz-head"><span className="fz-emoji">{f.emoji}</span><div><b>{f.name}</b><small>{f.tagline || `${f.legs.length} pools fused`}</small></div>
      <span className="fz-grade" title={f.score.parts.map(p => `${p.part}: ${p.why}`).join('\n')}>{f.score.grade}</span></header>
    <div className="fz-bar">{f.legs.map(l => <i key={l.pairAddress} style={{ flexGrow: l.weight }} title={`${l.symbol} ${l.weight}%`}><span>{l.symbol} {Math.round(l.weight)}%</span></i>)}</div>
    <div className="m-row fz-kpis"><div className="m-stat"><small>INDEX</small><b className={`m-num sm ${f.index >= 100 ? 'm-pos' : 'm-neg'}`}>{f.index.toFixed(1)}</b></div>
      <div className="m-stat"><small>DEPTH</small><b className="m-num sm">{usd(f.tvlUsd)}</b></div><div className="m-stat"><small>VOL 24H</small><b className="m-num sm">{usd(f.volume24h)}</b></div>
      <div className="m-stat"><small>FEE APR EST.</small><b className="m-num sm">{f.aprEst}%</b></div></div>
    <ul className="fz-legs">{f.legs.map(l => <li key={l.pairAddress}><b>{l.symbol}/{l.quote}</b><span>{usd(l.liquidityUsd)} liq</span><span>{l.turnover}× turnover</span><span className={l.change24h >= 0 ? 'm-pos' : 'm-neg'}>{l.change24h >= 0 ? '+' : ''}{(l.change24h || 0).toFixed(1)}%</span></li>)}</ul>
    {!going ? <button type="button" className="m-btn primary m-go wide" onClick={() => setGoing(true)} data-testid={`fuse-in-${f.id}`}>⚡ Fuse in</button>
      : <div className="fz-in"><label className="m-field"><span>SOL to fuse</span><NumInput className="m-input" inputMode="decimal" value={amount} onChange={e => setAmount(e.target.value.replace(/[^0-9.]/g, ''))} placeholder="0.5" /></label>
        {parts.map(p => <div key={p.pairAddress} className="fz-split"><span>{p.symbol} · {p.weight}%</span><FuseLeg leg={p} sol={p.sol} fuseId={f.id} /></div>)}
        <small className="m-dim">Each leg is its own swap you sign · normal FEELESS fees · {f.creatorBps ? `${f.creatorBps / 100}% of the fee goes to the Fuse's creator` : 'no creator cut'}</small></div>}
  </article>;
}

export function FusePanel() {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 60000); return () => { alive = false; clearInterval(t); }; }, []);
  return <><div className="fz-split-view"><FuseLab /><FuseSide /></div>{d?.fuses?.length > 0 && <section className="fz-panel" data-testid="fuse-panel"><div className="m-row"><span className="m-label">⚛️ FUSE · FUSED POOLS</span><small className="m-dim">baskets of live pools — one grade, one index, one tap in</small></div>
    <div className="fz-grid">{d.fuses.map(f => <FuseCard key={f.id} f={f} />)}</div></section>}</>;
}
