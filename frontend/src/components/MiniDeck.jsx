import { sharedJson } from '../lib/sharedJson';
import React, { useEffect, useState } from 'react';
import { CardFx } from './CardFx';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { useHeldList } from '../lib/myHoldings';
import { TokenAvatar } from './terminal/MarketPrimitives';
import { openCoin } from './CoinDrawer';
import '../styles/miniDeck.css';

// 🧰 The bottom-right mini box's own panes: 💼 Mine (coins you hold + your Fuse cards) and 🔥 Top 10 (the busiest Solana launch
// coins under 12 hours old, by the last hour's volume). One fetch each, only while the pane is open; rows open the coin drawer.
const usd = v => { const n = Number(v) || 0; return n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(2)}`; };
const pct = v => { const n = Number(v); if (!Number.isFinite(n)) return '—'; if (n >= 1000) return `${(n / 100 + 1).toFixed(n >= 9900 ? 0 : 1)}x`; return `${n >= 0 ? '+' : ''}${n.toFixed(Math.abs(n) >= 100 ? 0 : 1)}%`; };   // huge moves read as 12.4x
const TOP_MAX_AGE_H = 12;

export function topTen(pairs, nowMs = Date.now()) {
  const seen = new Set();
  return (pairs || []).filter(p => { const m = p?.baseToken?.address; const made = Number(p?.pairCreatedAt) || 0;
    if (!m || seen.has(m) || !made || nowMs - made > TOP_MAX_AGE_H * 3.6e6 || !(Number(p.priceUsd) > 0)) return false; seen.add(m); return true; })
    .sort((a, b) => (Number(b.volume?.h1) || 0) - (Number(a.volume?.h1) || 0)).slice(0, 10);
}

export function MiniTop() {
  const [rows, setRows] = useState(null);
  useEffect(() => { let alive = true;
    const load = first => { if (document.hidden && !first) return; Promise.all(['trending', 'new'].map(k => fetch(apiUrl(`/api/market/feed?kind=${k}&chain=solana&page=1&scope=launchpads`)).then(r => r.json()).catch(() => ({}))))
      .then(a => alive && setRows(topTen(a.flatMap(x => x.pairs || [])))); };
    load(true); const t = setInterval(() => load(false), 30000); return () => { alive = false; clearInterval(t); }; }, []);
  if (!rows) return <div className="md is-ghost" />;
  return <div className="md cfx-host" data-testid="mini-top"><CardFx kind="embers" /><span className="m-label">🔥 TOP 10 · SOLANA · UNDER 12H · BY 1H VOLUME</span>
    {rows.length ? <ol className="md-list">{rows.map((p, i) => <li key={p.baseToken.address} style={{ '--i': i }}>
      <button type="button" onClick={() => openCoin(p)} data-testid={`mini-top-${i}`}><i>{i + 1}</i><TokenAvatar pair={p} size={22} />
        <b>{p.baseToken.symbol}</b><span className="m-num">{usd(p.volume?.h1)}<small>/h</small></span>
        <em className={`m-num ${(Number(p.priceChange?.h1) || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(p.priceChange?.h1)}</em></button></li>)}</ol>
      : <p className="m-note">No launch coin under 12h is trading right now.</p>}
    <small className="m-dim">Newest coins move most and fail most. Tap a coin for its chart and checks.</small></div>;
}

export function MiniMine() {
  const { wallet } = useWallet() || {};
  const addr = wallet?.chain === 'solana' ? wallet.address : null;
  const held = useHeldList();
  const [fuse, setFuse] = useState(null);
  useEffect(() => { if (!addr) return undefined; let alive = true;
    const load = first => { if (first || !document.hidden) fetch(apiUrl(`/api/reputation/fuses/pnl/${addr}`)).then(r => (r.ok ? r.json() : null)).then(d => alive && d && setFuse(d)).catch(() => {}); };
    load(true); const t = setInterval(() => load(false), 30000); return () => { alive = false; clearInterval(t); }; }, [addr]);
  // 💵 the owner's real-money tier cards live in /fuses/prime (not in the trader positions) — shown to the owner / staff wallet only
  const [real, setReal] = useState([]);
  useEffect(() => { if (!addr) return undefined; let alive = true; let t;
    sharedJson(`/api/reputation/admin/is-admin/${addr}`, { maxAge: 60000 }).then(d => { if (!alive || !(d?.owner || d?.admin)) return;
      const load = first => { if (first || !document.hidden) sharedJson('/api/reputation/fuses/prime').then(x => alive && x && setReal((x.cards || []).filter(c => c.real))).catch(() => {}); };
      load(true); t = setInterval(() => load(false), 15000); }).catch(() => {});
    return () => { alive = false; clearInterval(t); }; }, [addr]);
  if (!addr) return <div className="md" data-testid="mini-mine"><p className="m-note">Connect a Solana wallet to see what you hold.</p></div>;
  const cards = fuse?.held?.cards || fuse?.positions || 0;
  return <div className="md" data-testid="mini-mine"><span className="m-label">⚛️ MY FUSE CARDS</span>
    {(cards > 0 || !real.length) && <a className="md-fuse" href="/terminal/fuse?tab=cards" data-testid="mini-fuse">{cards ? <><b>{cards} card{cards === 1 ? '' : 's'}</b><span className="m-num">{usd(fuse.valueUsd)}</span>
      <em className={`m-num ${(fuse.pnlUsd || 0) >= 0 ? 'm-pos' : 'm-neg'}`}>{(fuse.pnlUsd || 0) >= 0 ? '+' : '−'}{usd(Math.abs(fuse.pnlUsd || 0))} · {pct(fuse.pnlPct)}</em></> : <b>No open cards — open My cards →</b>}</a>}
    {real.map(c => { const put = c.realBook?.fundedUsd || c.startUsd || 0; const pnl = (c.math?.pnlUsd != null ? c.math.pnlUsd : (c.valueUsd || 0) - put);
      return <a key={c.tpl} className="md-fuse" href="/terminal/fuse?tab=cards" data-testid={`mini-real-${c.tpl}`}><b>💵 {c.label}</b><span className="m-num">{usd(c.valueUsd)}</span>
        <em className={`m-num ${pnl >= 0 ? 'm-pos' : 'm-neg'}`}>{pnl >= 0 ? '+' : '−'}{usd(Math.abs(pnl))} all-time · {pct(c.pnlPct)} this run</em></a>; })}
    <span className="m-label">💼 COINS I HOLD</span>
    {held.length ? <ol className="md-list is-plain">{held.slice(0, 12).map((t, i) => <li key={t.mint} style={{ '--i': i }}>
      <button type="button" onClick={() => openCoin({ mint: t.mint, symbol: t.symbol, pairAddress: t.pairAddress })}><i>{i + 1}</i>
        <b>{t.symbol || `${String(t.mint).slice(0, 4)}…`}</b><span className="m-num">{Number(t.holding).toLocaleString('en-US', { maximumFractionDigits: 2 })}</span>
        {Number.isFinite(Number(t.pnlPct)) ? <em className={`m-num ${Number(t.pnlPct) >= 0 ? 'm-pos' : 'm-neg'}`}>{pct(t.pnlPct)}</em> : <em className="m-num">—</em>}</button></li>)}</ol>
      : <p className="m-note">Nothing from your FEELESS trades is held right now.</p>}</div>;
}
