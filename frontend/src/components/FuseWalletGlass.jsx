import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { useGlide } from '../lib/useGlide';
import '../styles/fuseGlass.css';

// 🧬 YOUR FUSE WALLET, in the family building (owner 2026-10-26: "Fuse wallet should show in family building … glass styled vital P&L, live").
// The wallet's real Fuse cards (/fuses/pnl: on-chain balances × live prices, fees never in P&L): the total ticking + flashing on every read,
// one bar per card split by coin (width = $ in it, color = up / down), the best + worst coin, one tap into the Fuse page.
const $ = v => (v == null ? '—' : `${v < 0 ? '−' : ''}$${Math.abs(v) >= 1000 ? `${(Math.abs(v) / 1000).toFixed(2)}K` : Math.abs(v).toFixed(2)}`);
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`);

export function FuseWalletGlass() {
  const { wallet } = useWallet() || {}; const a = wallet?.address; const [d, setD] = useState(null);
  useEffect(() => { if (!a) { setD(null); return undefined; } let on = true;
    const load = () => { if (document.hidden) return; fetch(apiUrl(`/api/reputation/fuses/pnl/${a}`)).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {}); };
    load(); const t = setInterval(load, 20000); return () => { on = false; clearInterval(t); }; }, [a]);
  const h = d?.held || {}; const val = useGlide(h.valueUsd ?? null, 600); const pnl = h.pnlUsd ?? 0;
  const prev = useRef(h.valueUsd); const [flash, setFlash] = useState('');
  useEffect(() => { if (h.valueUsd != null && prev.current != null && h.valueUsd !== prev.current) { setFlash(h.valueUsd > prev.current ? 'is-up' : 'is-dn'); const t = setTimeout(() => setFlash(''), 700); prev.current = h.valueUsd; return () => clearTimeout(t); } prev.current = h.valueUsd; return undefined; }, [h.valueUsd]);
  if (!a) return null;
  const cards = (d?.rows || []).filter(r => !r.closed).slice(0, 3);
  const legs = cards.flatMap(c => (c.legs || []).filter(l => l.soldUsd == null));
  const best = legs.reduce((m, l) => (m == null || (l.pnlPct ?? -1e9) > (m.pnlPct ?? -1e9) ? l : m), null); const worst = legs.reduce((m, l) => (m == null || (l.pnlPct ?? 1e9) < (m.pnlPct ?? 1e9) ? l : m), null);
  return <section className={`fwg ${pnl >= 0 ? 'is-up' : 'is-dn'}`} data-testid="fuse-wallet-glass">
    <header><i className="fwg-dot" aria-hidden="true" /><span><b>🧬 YOUR FUSE WALLET</b><small>{d ? `${h.cards || 0} live card${h.cards === 1 ? '' : 's'} · on-chain × live price` : 'reading…'}</small></span></header>
    {d && !h.cards ? <div className="fwg-empty"><p>No live Fuse card yet — a card trades 3–5 coins for you on the desk's rules.</p>
      <a className="m-btn m-go" href="/terminal/fuse" data-tip="Open the Fuse page and make a card">🧬 MAKE A CARD</a></div> : null}
    {h.cards ? <>
      <div className="fwg-hero"><span><em>WORTH NOW</em><b className={`m-num ${flash}`}>{$(val)}</b></span>
        <span className={pnl >= 0 ? 'is-up' : 'is-dn'} data-tip="Live P&L on what reached the pools — fees are on the receipt, never in P&L"><em>P&L</em><b className="m-num">{$(pnl)}</b><small className="m-num">{pc(h.pnlPct)}</small></span></div>
      <u className="fwg-meter" aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, Math.min(1, 0.5 + (h.pnlPct || 0) / 100))})` }} /></u>
      <ol className="fwg-cards">{cards.map((c, i) => { const tot = (c.legs || []).filter(l => l.soldUsd == null).reduce((s, l) => s + (l.valueUsd || 0), 0) || 1;
        return <li key={c.id} style={{ '--i': i }}><span className="fwg-ch"><b>{c.name || 'Fuse card'}</b><small className={`m-num ${c.pnlUsd >= 0 ? 'is-up' : 'is-dn'}`}>{$(c.pnlUsd)} · {pc(c.pnlPct)}</small></span>
          <span className="fwg-legs">{(c.legs || []).filter(l => l.soldUsd == null).map(l => <i key={l.pairAddress || l.symbol} className={(l.pnlPct ?? 0) >= 0 ? 'is-up' : 'is-dn'} style={{ flexGrow: Math.max(0.02, (l.valueUsd || 0) / tot) }} data-tip={`$${l.symbol} · ${$(l.valueUsd)} · ${pc(l.pnlPct)}`} />)}</span></li>; })}</ol>
      {best && worst ? <p className="fwg-mv"><span className="is-up">▲ ${best.symbol} {pc(best.pnlPct)}</span><span className="is-dn">▼ ${worst.symbol} {pc(worst.pnlPct)}</span></p> : null}
      <a className="m-btn fwg-go" href="/terminal/fuse" data-tip="Your cards, every coin, every move">OPEN MY CARDS →</a></> : null}
  </section>;
}
