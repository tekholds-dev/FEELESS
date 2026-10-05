import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useLivePrices } from '../lib/livePrices';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { openWarRoom } from './WarRoomHost';
import '../styles/contenders.css';

// 🏁 Arena contenders: every pick list is a division. Coins are ranked on live facts and the best one not on a card is ⏭ next up
// for a seat. Prices tick live (shared 10s poller); ranks, scores and seats come from the league (rebuilt every 30s server-side).
const big = v => (v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);
const px = v => (!v ? '—' : v >= 1 ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : `$${Number(v).toPrecision(3)}`);
const pct = v => (v == null ? '—' : Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`);
const MOVE = { up: ['▲', 'm-pos', 'Climbed since the last ranking'], down: ['▼', 'm-neg', 'Dropped since the last ranking'], new: ['NEW', 'cn-new', 'Just entered this division'], same: ['·', 'm-dim', 'Holding its rank'] };
const fast = k => k === 'fresh' || k === 'proven';

export function liveRow(r, live, key) {
  const l = live?.get?.(r.pairAddress);
  const move = fast(key) ? (l ? l.h1 : r.chg1h) : r.chg24h;   // runners are judged on the hour, everything else on the day
  return { ...r, price: l?.price || r.price, move, moveLabel: fast(key) ? '1H' : '24H', m5: l ? l.m5 : null };
}

export function ArenaContenders({ onPick }) {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('');
  useEffect(() => { let alive = true; const load = () => fetch(apiUrl('/api/reputation/fuses/contenders')).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 30000); return () => { alive = false; clearInterval(t); }; }, []);
  const divs = (d?.divisions || []).filter(x => x.rows.length);
  const cur = divs.find(x => x.key === tab) || divs[0];
  const live = useLivePrices((cur?.rows || []).map(r => r.pairAddress));
  if (!d) return <section className="m-card cn" data-testid="arena-contenders"><span className="loader" /> Ranking the contenders…</section>;
  if (!cur) return null;
  return <section className="m-card m-live cn" data-testid="arena-contenders">
    <header className="cn-head"><span className="m-label">🏁 CONTENDERS · {divs.length} DIVISIONS FIGHTING FOR THE NEXT CARD SEAT</span>
      <small className="m-dim">Ranked on live volume, depth, momentum and buyers. ⏭ = first in line for a seat — the card engine still runs every gate.</small></header>
    <div className="m-seg cn-tabs" role="tablist">{divs.map(x => <button key={x.key} type="button" role="tab" aria-selected={x.key === cur.key} className={x.key === cur.key ? 'active' : ''} data-tip={x.rule} onClick={() => setTab(x.key)} data-testid={`cn-tab-${x.key}`}>{x.label}<i className="m-num">{x.rows.length}</i></button>)}</div>
    <p className="m-dim cn-rule">{cur.rule} · the seat feeds a card's {cur.role} slot</p>
    <ol className="cn-rows">{cur.rows.map((r0, i) => { const r = liveRow(r0, live, cur.key); const mv = MOVE[r.move] || MOVE.same; const why = r.parts.map(p => `${p.part} +${p.points} (${p.why})`).join(' · ');
      return <li key={r.mint} className={`cn-row ${r.seat === 'next' ? 'is-next' : ''} ${r.seat === 'card' ? 'is-card' : ''}`} style={{ '--i': i }} data-testid={`cn-row-${r.symbol}`}>
        <b className="cn-rank m-num">{r.rank}</b><span className={`cn-move ${mv[1]}`} data-tip={mv[2]}>{mv[0]}</span>
        <button type="button" className="cn-coin" data-tip="Open its chart" onClick={() => openWarRoom({ chainId: 'solana', pairAddress: r.pairAddress, baseToken: { address: r.mint, symbol: r.symbol } })}>
          <TokenAvatar pair={{ chainId: 'solana', pairAddress: r.pairAddress, baseToken: { address: r.mint, symbol: r.symbol }, info: r.logo ? { imageUrl: r.logo } : undefined }} size={30} />
          <span><b>${r.symbol}</b>{r.streak > 1 && <small className="cn-streak" data-tip={`#1 for ${r.streak} rankings in a row`}>🔥 ×{r.streak}</small>}</span></button>
        <span className="cn-stat"><small>PRICE</small><b key={px(r.price)} className="m-num fl-tick">{px(r.price)}</b></span>
        <span className="cn-stat"><small>{r.moveLabel}</small><b key={pct(r.move)} className={`m-num fl-tick ${r.move >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(r.move)}</b></span>
        <span className="cn-stat cn-wide"><small>{fast(cur.key) ? 'VOL 1H' : 'VOL 24H'}</small><b className="m-num">{big(fast(cur.key) ? r.vol1h : r.vol24h)}</b></span>
        <span className="cn-stat cn-wide"><small>POOL</small><b className="m-num">{r.liq > 0 ? big(r.liq) : 'curve'}</b></span>
        <span className="cn-score" data-tip={why}><i style={{ transform: `scaleX(${Math.max(0.04, r.score / 100)})` }} /><b className="m-num">{r.score.toFixed(0)}</b></span>
        {r.watch ? <span className="m-chip cn-seat cn-watch" data-tip="Nothing passes this list's rule right now — this is one of the closest live coins. It never takes a seat until it qualifies.">👀 WATCH</span>
          : r.seat === 'next' ? <span className="m-chip ok cn-seat" data-tip="First in line: the card engine picks next-up coins first when a seat opens (gates, pool floor and runner weather still apply)">⏭ NEXT UP</span>
          : r.seat === 'card' ? <span className="m-chip cn-seat" data-tip="Already on a tier or Arena card">🃏 ON A CARD</span>
          : <span className="m-chip cn-seat cn-chase" data-tip="Needs to out-score the coin above to take the seat">CHASING</span>}
        {onPick && <button type="button" className="m-btn cn-add" data-tip="Add this coin to your card in the Lab" onClick={() => onPick(r, cur.role)} aria-label={`Add ${r.symbol} to the Lab`}>＋</button>}</li>; })}</ol>
  </section>;
}
