import React, { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { useLivePrice } from '../../lib/livePriceHub';
import { useLiveTokenMarkets } from '../../lib/liveTokens';
import { Bubble } from './LaunchCat';
import '../../styles/agentDemo.css';

// 🛸 AGENT LIVE (owner, 2026-10-30: "this same ui/layout from the demo in live — when an agent is bought, when I enter My agent, and Fee's live
// desk: 2 charts with thoughts"). The demo's frame, fed REAL data: each mind a live bubble whose thoughts are its own latest words, two REAL
// coin charts (what it holds, then what it reads next), and its real activity riding over both windows. A window with no coin yet shows the
// drawn ghost, labelled as a preview. Pure helpers are exported for tests.
const PriceChart = lazy(() => import('../terminal/PriceChart').then(m => ({ default: m.PriceChart })));
// 📊 every agent window charts MARKET CAP (owner 2026-11-02: "market cap, not market price") — the coin's live cap from the shared batched read;
// price only while no cap is known. Entry / stop / take-profit lines scale with it (PriceChart's own ratio).
export function McapChart({ coin, ...rest }) {
  const [byPool, setByPool] = useState(null);   // a record with only its pool (Fee's older exits have no mint): the pool resolves the coin + its cap
  useEffect(() => { if (coin?.mint || !coin?.pair) return undefined; let on = true;
    const go = () => fetch(`/api/market/pairs/solana/${coin.pair}`).then(r => (r.ok ? r.json() : null)).then(j => { const p = (Array.isArray(j) ? j : j?.pairs || [])[0]; if (on && p) setByPool(p); }).catch(() => {});
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 20000); return () => { on = false; clearInterval(t); }; }, [coin?.mint, coin?.pair]);
  const mints = useMemo(() => [coin?.mint].filter(Boolean), [coin?.mint]); const live = useLiveTokenMarkets('solana', mints).get(coin?.mint) || byPool;
  const mint = coin?.mint || live?.baseToken?.address;
  const cap = Number(live?.marketCap || live?.fdv) || null; const px = Number(live?.priceUsd) || null;
  return <Suspense fallback={<span className="agl-load">loading ${coin.symbol}'s live chart…</span>}>
    <PriceChart key={coin.pair} pair={{ chainId: 'solana', pairAddress: coin.pair, baseToken: { address: mint, symbol: coin.symbol }, ...(px ? { priceUsd: px } : {}), ...(cap ? { marketCap: cap } : {}) }}
      interval="1m" metric={cap && px ? 'marketCap' : 'price'} showVolume={false} roomPx={200} {...rest} /></Suspense>;   // 🕯 the newest candle stays clear of the level labels
}
export const asModel = id => (id ? { id, name: String(id).split('/').pop(), provider: String(id).split('/')[0] } : null);
const ago = s => { const m = Math.max(1, Math.round((Date.now() / 1000 - s) / 60)); return m < 60 ? `${m}m` : m < 1440 ? `${(m / 60).toFixed(1)}h` : `${Math.round(m / 1440)}d`; };
const fin = v => v != null && Number.isFinite(Number(v));
// 🧾 the owner's vitals under each window (owner 2026-10-30: "has all needed vitals in this 2 window view"): held → size · P&L · held for; sold → exit · P&L · after
export function coinVitals(c) {
  if (!c) return [];
  const tone = v => (v > 0 ? 'up' : v < 0 ? 'dn' : '');
  return (c.open ? [['SIZE', fin(c.sol) ? `${c.sol.toFixed(3)} SOL` : null], ['ENTRY', fin(c.entry) ? `$${Number(c.entry).toPrecision(3)}` : null], ['P&L', fin(c.pct) ? pctWord(c.pct) : null, tone(c.pct)], ['SL', fin(c.sl) ? `−${c.sl}%` : null, 'dn'], ['TP', fin(c.tp) ? `+${c.tp}%` : null, 'up'], ['HELD', c.at ? ago(c.at) : null]]
    : [['EXIT', fin(c.pct) ? pctWord(c.pct) : null, tone(c.pct)], ['P&L', fin(c.pnl) ? `${c.pnl >= 0 ? '+' : ''}${c.pnl.toFixed(4)} SOL` : null, tone(c.pnl)], ['AFTER', fin(c.after) ? `peak ${pctWord(c.after)}` : null], ['SOLD', c.at ? `${ago(c.at)} ago` : null]])
    .filter(x => x[1]);
}
const pctWord = v => (v == null || !Number.isFinite(Number(v)) ? '' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

// pure: a trading cat's two minds — each one's own latest decisions become its thoughts; the feed is every decision, newest last
export function catMinds(cat) {
  const b = cat?.brainsCfg || {}; const brains = (b.brains || []).slice(0, 2); const dec = (b.decisions || []).slice(-24);
  const mine = id => dec.filter(x => String(x.by || '').includes(String(id).split('/').pop().split(':')[0])).slice(-4).map(x => `${x.word} $${x.sym}`);
  return { brains, thoughts: brains.map(mine), cloud: (b.cloud || []).slice(-5).reverse(), feed: dec.slice(-3).map(x => `🧠 ${x.by} · ${x.word} $${x.sym}${x.why ? ` — ${String(x.why).slice(0, 70)}` : ''}`) };
}
// pure: the coins its two windows chart — held first, then the coins it just closed (it still reads them)
export function catCoins(cat) {
  const held = (cat?.positions || []).filter(p => p.pairAddress).map(p => ({ pair: p.pairAddress, mint: p.mint, symbol: p.symbol, pct: Number(p.currentChange), entry: Number(p.entryPriceUsd) || null, open: true,
    sol: Number(p.costSol || p.notionalSol) || null, at: p.openedAt || null, why: p.reason || '' }));
  const seen = new Set(held.map(c => c.pair));
  const after = (cat?.exits || []).filter(e => e.pairAddress && !seen.has(e.pairAddress)).slice(-2).reverse().map(e => ({ pair: e.pairAddress, mint: e.mint, symbol: e.symbol, open: false,
    pct: Number(e.changeAtExit), pnl: Number(e.pnlSol), after: Number(e.peakAfter), at: e.exitAt || null, why: e.why || '' }));
  return [...held, ...after].slice(0, 2);
}

// the bubbles row alone (a general cat's desk puts it over its two cloud browsers)
// ☁ the HEAD CLOUD between the two minds: only what BOTH agreed on lands here (launch_cat.cloud_check) — drawn cloud, a count, the last calls
export function HeadCloud({ items = [] }) {
  const top = items[0];
  return <span className={`agl-cloud${items.length ? ' is-on' : ''}`} data-testid="head-cloud" data-tip="The head cloud: a call lands here only when BOTH minds said the same thing on the same coin">
    <svg viewBox="0 0 120 70" aria-hidden="true"><path d="M30 60 C12 60 8 40 24 36 C22 18 46 12 54 26 C62 8 92 12 90 32 C108 30 112 58 92 60 Z" /></svg>
    <b className="m-num" key={items.length}>{items.length}</b><em>HEAD CLOUD</em>
    <small>{top ? (top.text ? String(top.text).slice(0, 48) : `${top.word} $${top.sym} · both agree`) : 'waiting for both to agree'}</small></span>;
}
export function MindsRow({ minds = [], cloud }) {
  const mind = i => { const m = minds[i];
    return <span key={i} className={`agl-mind${m ? '' : ' is-empty'}`}><Bubble m={m?.model} i={i} kind={m?.kind} thoughts={m?.thoughts} size={64} live={!!m?.live} />
      <b>{m?.label || (i ? 'no second mind' : 'its mind')}</b><small>{m?.sub || ''}</small></span>; };
  return <div className={`agl-minds${cloud ? ' has-cloud' : ''}`} data-testid="minds-row">{mind(0)}{cloud ? <HeadCloud items={cloud} /> : null}{mind(1)}</div>;
}

// 📈 an open coin's P&L ticks on the shared 2 s price poll (owner 2026-11-02: "a live pnl"); a sold coin keeps its exit numbers
function WinVitals({ c }) {
  const lp = useLivePrice(c?.open && c.mint ? { chainId: 'solana', baseToken: { address: c.mint } } : null);
  const live = c?.open && lp.usd && c.entry > 0 ? { ...c, pct: (lp.usd / c.entry - 1) * 100 } : c;
  const rows = coinVitals(live);
  return rows.length ? <dl className={`agl-vit${c?.open ? ' is-live' : ''}`} data-tip={c.why || undefined}>{rows.map(([k, v, t]) => <div key={k}><dt>{k === 'P&L' && c?.open ? <><i className="agl-live-dot" aria-hidden="true" />P&L LIVE</> : k}</dt><dd className={`m-num ${t ? `is-${t}` : ''}`} key={v}>{v}</dd></div>)}</dl> : null;
}
// 🗂 its decisions as TOASTS (owner 2026-11-02: "stuff overflowing at the bottom — it should stack for seconds then disappear off into the folder"):
// each new line rides over the bottom of the windows for TOAST_MS, then drops into the folder (no growing list under the charts)
export const TOAST_MS = 6000;
export function FeedToasts({ feed = [] }) {
  const [items, setItems] = useState([]); const seen = useRef(null);
  useEffect(() => { const prev = seen.current; seen.current = new Set(feed);
    if (!prev) { setItems(feed.slice(-1).map(t => ({ t, at: Date.now() }))); return; }
    const fresh = feed.filter(t => !prev.has(t)); if (fresh.length) setItems(x => [...x, ...fresh.map(t => ({ t, at: Date.now() }))].slice(-3)); }, [feed]);
  useEffect(() => { if (!items.length) return undefined; const t = setInterval(() => setItems(x => x.map(i => (Date.now() - i.at > TOAST_MS && !i.out ? { ...i, out: true } : i)).filter(i => !(i.out && Date.now() - i.at > TOAST_MS + 700))), 350);
    return () => clearInterval(t); }, [items.length]);
  const [turn, setTurn] = useState(0); const n = items.length;
  useEffect(() => { if (n < 2) return undefined; const t = setInterval(() => setTurn(x => x + 1), 2200); return () => clearInterval(t); }, [n]);
  return <ol className="agd-feed agd-toasts" aria-live="polite" data-testid="agd-toasts">{items.map((i, k) => <li key={`${i.at}-${i.t}`} className={`${i.out ? 'is-out' : ''}${k === turn % n ? ' is-turn' : ''}`}>{i.t}</li>)}</ol>;
}
export function AgentLive({ title = 'LIVE', minds = [], coins = [], feed = [], callouts, testId = 'agent-live', cloud, locked = false }) {   // locked: a visitor watches, never drives (no zoom / pan on its charts)
  return <section className={`agd agl is-trading${locked ? ' is-locked' : ''}`} data-testid={testId}>
    <i className="agd-hex" aria-hidden="true" /><i className="agd-scan" aria-hidden="true" />
    <span className="agd-tag">◈ {title}</span>
    {minds.length ? <MindsRow minds={minds} cloud={cloud} /> : null}
    <div className="agd-wins">{[0, 1].map(i => { const c = coins[i];
      return <div key={i} className={`agd-win w${i}`} style={{ '--i': i }}>
        <span className={`agd-bar ${c ? 'is-go' : 'is-stop'}`}><i /><i /><i /><b>{c ? `$${c.symbol}` : `WINDOW ${'AB'[i]}`}</b><small>{c ? (c.open ? `holding ${pctWord(c.pct)}` : c.note || 'reading next') : 'waiting for a coin'}</small>
          <em className="agd-live">{c ? '● LIVE' : '◌ IDLE'}</em></span>
        {c ? <div className="agl-plot"><McapChart coin={c} userEntry={c.entry || null} callouts={callouts ? callouts(c.pair) : undefined} /></div> : <div className="agl-ghost"><span>◌ watching the trenches — its next coin opens here, live</span></div>}
        <WinVitals c={c} />
      </div>; })}</div>
    <FeedToasts feed={feed} />
  </section>;
}
