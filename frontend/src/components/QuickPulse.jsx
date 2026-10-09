import React, { useEffect, useState } from 'react';
import { sharedJson } from '../lib/sharedJson';
import * as candleLib from '../lib/candles';
import { chartPulse, TF_WINDOW } from '../lib/chartPulse';
import '../styles/quickPulse.css';

// 🫧 LIVE PANELS for the quick look (owner, 2026-10-08: "socials and any other live vitals to give a unique edge… the pop-out's vitals
// need to change based on the chart as we watch… actual Pump callouts"). Four small pieces, each one job:
//   Socials       — site / 𝕏 / Telegram / Pump page, or a plain "no socials" warning
//   FlowWindows   — buy pressure, organic share, net buyers, traders, holders / pool change for the window that fits the chart's timeframe
//   ChartPulse    — what the candles ON SCREEN say (place in range, off the high, green candles, streak, volume vs before)
//   PumpCall      — who on Pump is calling this coin out, at what cap, and the multiple since
//   PumpCallouts  — Pump's own top callouts strip (Open gates)
const big = v => { const n = Number(v) || 0; return !n ? '—' : n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n < 10 ? n.toFixed(2) : Math.round(n)}`; };
const sgn = (v, d = 0) => (v == null || !Number.isFinite(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(d)}%`);
const ago = ms => { if (!ms) return ''; const m = Math.max(0, Math.round((Date.now() - ms) / 60000)); return m < 1 ? 'just now' : m < 60 ? `${m}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`; };
const TONE = { good: 'is-good', warn: 'is-warn', bad: 'is-bad' };
const safeUrl = u => (typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null);

export const socialLinks = r => [['🌐', 'Site', safeUrl(r?.site)], ['𝕏', 'X', safeUrl(r?.x)], ['✈', 'Telegram', safeUrl(r?.tg)],
  ['💊', 'Pump', /pump$/.test(String(r?.mint || '')) ? `https://pump.fun/coin/${r.mint}` : null]].filter(x => x[2]);
// 🔗 the coin's socials as small clickable icons — FIRST on a trench row (owner: "trench should show socials first and clickable").
// A row inside a clickable card: each link stops the click so it opens the site, not the card. 🚫 = none set.
export function SocialIcons({ r }) {
  const links = socialLinks(r).filter(l => l[1] !== 'Pump');
  const known = [r?.site && '🌐', r?.x && '𝕏', r?.tg && '✈'].filter(Boolean);
  return <span className="qp-ico" data-testid="soc-icons">{links.length ? links.map(([ic, name, url]) => <a key={name} href={url} target="_blank" rel="noopener noreferrer nofollow" onClick={e => e.stopPropagation()}
    data-tip={`Opens its ${name} — a link the coin set itself, not checked by FEELESS`} aria-label={name}>{ic}</a>)
    : known.length ? <i data-tip="Set at launch — the link itself isn't on record here">{known.join('')}✓</i> : <i className="is-none" data-tip="No website, X or Telegram set — most coins that last set one">🚫</i>}</span>;
}

export function Socials({ r }) {
  const links = socialLinks(r); const own = links.filter(l => l[1] !== 'Pump').length;
  const known = [r?.site && 'site', r?.x && '𝕏', r?.tg && 'Telegram'].filter(Boolean);   // set at launch, but no link on record here
  return <div className="qp-soc" data-testid="qp-socials">
    {links.map(([ic, name, url]) => <a key={name} href={url} target="_blank" rel="noopener noreferrer nofollow" className="qp-link" data-tip={`Opens the coin's ${name} in a new tab — a link the coin set itself, not checked by FEELESS`} data-testid={`qp-soc-${name}`}>{ic} {name}</a>)}
    {!own && known.length > 0 && <span className="qp-link is-known" data-tip="The coin set these at launch; the link itself is not on record here — open its Pump page or the war room for them.">✓ {known.join(' + ')} set</span>}
    {!own && !known.length && <span className="qp-link is-none" data-tip="No website, X or Telegram on record for this coin. Most coins that last set at least one at launch.">🚫 no socials set</span>}
  </div>;
}

// 🫧 FLOW by window. `win` = backend jup_audit.windows (5m · 1h · 6h · 24h). The window follows the chart's timeframe until one is tapped.
export const FLOW_WINDOWS = [['5m', '5M'], ['1h', '1H'], ['6h', '6H'], ['24h', '24H']];
export const flowShift = win => { const a = win?.['5m']?.buyPct; const b = win?.['1h']?.buyPct; if (a == null || b == null) return null;
  const d = Math.round(a - b); return d >= 8 ? ['⏫', `buyers stepping in (+${d} pts vs the hour)`, 'good'] : d <= -8 ? ['⏬', `buyers backing off (${d} pts vs the hour)`, 'bad'] : ['⏸', 'buy pressure steady', 'warn']; };
export function FlowWindows({ win, tf }) {
  const [own, setOwn] = useState(null);
  useEffect(() => setOwn(null), [tf]);   // a new chart timeframe takes the lead again
  if (!win || !Object.keys(win).length) return null;
  const linked = TF_WINDOW[tf] || '1h';
  const key = own && win[own] ? own : win[linked] ? linked : Object.keys(win)[0];
  const w = win[key] || {}; const shift = flowShift(win);
  const tiles = [['🌱 ORGANIC', w.organicPct == null ? '—' : `${Math.round(w.organicPct)}%`, w.organicPct != null && w.organicPct < 5, 'Share of this window\'s volume from real traders (Jupiter) — low = bots trading with each other'],
    ['👥 NET BUYERS', w.netBuyers == null ? '—' : `${w.netBuyers >= 0 ? '+' : ''}${w.netBuyers.toLocaleString()}`, w.netBuyers != null && w.netBuyers < 0, 'Wallets that bought minus wallets that sold in this window'],
    ['🧑 TRADERS', w.traders == null ? '—' : w.traders.toLocaleString(), false, 'Different wallets that traded in this window'],
    ['💵 AVG TRADE', w.avgTrade == null ? '—' : big(w.avgTrade), false, 'Volume ÷ trades in this window: small = retail, large = a few big wallets'],
    ['🫂 HOLDERS', sgn(w.holderChg, 1), w.holderChg != null && w.holderChg < 0, 'Change in holder count over this window'],
    ['💧 POOL', sgn(w.liqChg, 1), w.liqChg != null && w.liqChg <= -15, 'Change in pool depth over this window — a big drop is money leaving'],
    ['📦 VOLUME', big(w.vol), false, 'Traded in this window'], ['📈 VS BEFORE', sgn(w.volChg), w.volChg != null && w.volChg <= -50, 'Volume vs the window before it']];
  return <div className="qp-flow" data-testid="qp-flow">
    <div className="qp-hd"><span className="m-label">🫧 FLOW · LAST {(FLOW_WINDOWS.find(x => x[0] === key) || [])[1]}{key === linked && !own ? ' · follows the chart' : ''}</span>
      <span className="qp-wins" role="radiogroup" aria-label="Flow window">{FLOW_WINDOWS.filter(([k]) => win[k]).map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={k === key} className={`qp-win ${k === key ? 'on' : ''}`} onClick={() => setOwn(k)}
        data-tip={`Buy pressure over the last ${l}: ${win[k].buyPct == null ? 'no trades' : `${Math.round(win[k].buyPct)}% of the money was buying`}`} data-testid={`qp-win-${k}`}>
        <i style={{ transform: `scaleY(${Math.max(0.08, Math.min(1, (win[k].buyPct ?? 0) / 100))})` }} className={win[k].buyPct == null ? '' : win[k].buyPct >= 55 ? 'up' : win[k].buyPct < 45 ? 'dn' : ''} />{l}</button>)}</span></div>
    <div className="qp-press" data-tip="Share of the MONEY traded in this window that was buying (by volume, not by trade count)"><small>BUY</small>
      <span><i key={`${key}-${Math.round(w.buyPct ?? 0)}`} style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, (w.buyPct ?? 0) / 100))})` }} /></span><small>SELL</small><b>{w.buyPct == null ? '—' : `${Math.round(w.buyPct)}%`}</b></div>
    {shift && <p className={`qp-shift ${TONE[shift[2]] || ''}`} data-testid="qp-shift">{shift[0]} {shift[1]}</p>}
    <div className="qp-tiles">{tiles.map(([l, v, bad, tip]) => <div key={l} className={bad ? 'bad' : ''} data-tip={tip}><small>{l}</small><b key={v} className="fl-tick">{v}</b></div>)}</div>
  </div>;
}

// 📊 the candles the chart is drawing, re-read every 20s (the chart service answers from memory)
export function useCandles(pairAddress, mint, tf) {
  const cached = () => candleLib.getCachedCandles?.('solana', pairAddress, tf)?.candles || null;
  const [cs, setCs] = useState(cached);
  useEffect(() => {
    let alive = true; setCs(cached());
    if (!pairAddress || !candleLib.fetchFeelessCandles) return undefined;
    const load = () => Promise.resolve(candleLib.fetchFeelessCandles('solana', pairAddress, tf, undefined, mint)).then(res => { candleLib.cacheCandles?.('solana', pairAddress, tf, res); if (alive && Array.isArray(res?.candles)) setCs(res.candles); }).catch(() => {});
    const first = setTimeout(load, 900);   // the chart's own load goes first (one request in flight per timeframe)
    const t = setInterval(() => { if (!document.hidden) load(); }, 20000);
    return () => { alive = false; clearTimeout(first); clearInterval(t); };
  }, [pairAddress, mint, tf]);   // eslint-disable-line react-hooks/exhaustive-deps
  return cs;
}
export function ChartPulse({ pairAddress, mint, tf }) {
  const p = chartPulse(useCandles(pairAddress, mint, tf));
  if (!p) return null;
  const [ic, word, tone] = p.call;
  const tiles = [['OFF HIGH', p.offHigh ? `−${p.offHigh}%` : 'at high', p.offHigh >= 25, 'How far the last price sits under the highest candle on screen'],
    ['GREEN', `${p.greens}/10`, p.greens <= 3, 'Green candles among the last ten'], ['STREAK', `${p.streak > 0 ? '▲' : '▼'} ${Math.abs(p.streak)}`, p.streak <= -4, 'Candles in a row closing the same way'],
    ['VOLUME', p.volX == null ? '—' : `${p.volX}×`, p.volX != null && p.volX < 0.5, 'Last five candles\' volume vs the fifteen before: above 1× = picking up'],
    ['BODY', `${p.conviction}%`, false, 'How much of each candle is body, not wick: high = one-way moves, low = fights']];
  return <div className={`qp-chart ${TONE[tone] || ''}`} data-testid="qp-chart">
    <div className="qp-hd"><span className="m-label">📊 CHART · {String(tf).toUpperCase()} CANDLES</span><span className={`qp-word ${TONE[tone] || ''}`} key={word} data-tip={`Read from the last ${p.n} ${tf} candles on the chart. It changes when you change the timeframe. A read of the picture, never a forecast.`}>{ic} {word}</span></div>
    <div className="qp-range" data-tip={`Where the price sits between the lowest and highest candle on screen: ${p.pos}% of the way up`}><small>LOW</small><span><i style={{ transform: `translateX(${Math.max(0, Math.min(100, p.pos))}%)` }}><u /></i></span><small>HIGH</small><b>{p.pos}%</b></div>
    <div className="qp-tiles is-5">{tiles.map(([l, v, bad, tip]) => <div key={l} className={bad ? 'bad' : ''} data-tip={tip}><small>{l}</small><b key={v} className="fl-tick">{v}</b></div>)}</div>
  </div>;
}

// 📣 who on Pump is calling this coin out (row `pc` = backend pump_calls.summary)
export function PumpCall({ pc }) {
  if (!pc?.calls) return null;
  const l = pc.lead || {};
  return <div className="qp-call" data-testid="qp-call" data-tip="A callout is a public call a HOLDER makes on Pump. Other people's calls, read from Pump's own feed — not advice, and callers can already be in profit.">
    <div className="qp-hd"><span className="m-label">📣 PUMP CALLOUTS · {pc.callers} CALLER{pc.callers === 1 ? '' : 'S'}{pc.verified ? ` · ${pc.verified} ✓` : ''}</span>
      <span className="qp-heat" aria-label={`Callout heat ${pc.heat} of 100`}>{Array.from({ length: 10 }, (_, i) => <i key={i} className={pc.heat >= (i + 1) * 10 - 5 ? 'on' : ''} style={{ '--i': i }} />)}<b>{pc.heat}</b></span></div>
    <p className="qp-thesis"><b>@{l.user}{l.verified ? ' ✓' : ''}</b> {l.thesis ? `“${l.thesis}”` : 'called it out'}</p>
    {pc.pro > 0 && <p className="qp-shift is-good" data-testid="qp-pro" data-tip="A proven caller: 3+ of their calls judged an hour later, typical result 1.2× or better, at least half up. Their record, never a promise.">🎯 {pc.pro} proven caller{pc.pro === 1 ? '' : 's'} on it: {(pc.pros || []).map(u => `@${u}`).join(' · ')}</p>}
    <small className="qp-callnums">{pc.firstMc ? `first called at ${big(pc.firstMc)}` : ''}{l.mult ? ` · ${l.mult}× since the lead call` : ''} · 👁 {Number(pc.views || 0).toLocaleString()} · {ago(pc.lastAt)}</small>
  </div>;
}

// 🧲 FEEDERS (row `fd` = backend feeders.board): the new Pump coins launched AGAINST this runner — each of their buys routes through its pool
export function Feeders({ r }) {
  const f = r?.fd; const pw = r?.pairedWith;
  if (!f?.n && !pw) return null;
  return <div className="qp-fd" data-testid="qp-feeders" data-tip="Pump, Oct 8: a newly launched coin paired with an existing runner routes every single buy through the runner's pool. Read from Pump's own coin records. Where buys are routed — never a promise the runner goes up.">
    {pw && <p className="qp-shift is-warn" data-testid="qp-paired">⛓ Launched paired with {pw.symbol ? `$${pw.symbol}` : 'another coin'}, not SOL — it trades through that coin and moves with it.</p>}
    {f?.n > 0 && <><div className="qp-hd"><span className="m-label">🧲 FEEDERS · {f.n} COIN{f.n === 1 ? '' : 'S'} PAIRED WITH IT</span>
      <span className="qp-heat is-fd" aria-label={`Feed ${f.score} of 100`}>{Array.from({ length: 10 }, (_, i) => <i key={i} className={f.score >= (i + 1) * 10 - 5 ? 'on' : ''} style={{ '--i': i }} />)}<b>{f.score}</b></span></div>
      <small className="qp-callnums">{f.active} trading right now · {f.fresh} launched this hour · {big(f.capUsd)} of cap riding on it — every buy of these routes through ${r.symbol}'s pool</small>
      <div className="qp-kids">{(f.kids || []).map((k, i) => <span key={k.mint} className={`qp-kid ${k.lastMin != null && k.lastMin <= 5 ? 'on' : ''}`} style={{ '--i': i }} data-tip={`$${k.symbol}: ${big(k.mcap)} cap · ${k.ageMin == null ? 'age unknown' : k.ageMin < 60 ? `${k.ageMin}m old` : `${Math.round(k.ageMin / 60)}h old`} · ${k.lastMin == null ? 'no trade yet' : `last trade ${k.lastMin < 1 ? 'seconds' : `${Math.round(k.lastMin)}m`} ago`}`}>${k.symbol}<em>{big(k.mcap)}</em></span>)}</div></>}
  </div>;
}

// 📣 Pump's own callouts strip (GET /fuses/pump-callouts, one shared read a minute): today's top call first, then the newest
export function usePumpCallouts() {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; const load = () => sharedJson('/api/reputation/fuses/pump-callouts', { maxAge: 45000 }).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 60000); return () => { alive = false; clearInterval(t); }; }, []);
  return d;
}
export function PumpCallouts({ onOpen }) {
  const d = usePumpCallouts(); const [tab, setTab] = useState('top'); const best = d?.callers || [];
  if (!d || (!(d.top || []).length && !(d.latest || []).length)) return null;
  const list = (tab === 'top' && (d.top || []).length ? d.top : d.latest || []).slice(0, 8); const [first, ...rest] = list;
  const sym = c => `$${c.symbol || `${String(c.mint).slice(0, 4)}…`}`;
  const open = c => onOpen && onOpen({ mint: c.mint, symbol: c.symbol });
  return <div className="pcl" data-testid="pump-callouts">
    <div className="qp-hd"><span className="m-label">📣 PUMP CALLOUTS · LIVE FROM PUMP</span>
      <span className="m-seg pcl-seg" role="radiogroup" aria-label="Callouts">{[['top', '🏆 Top today'], ['latest', '🆕 Newest'], ['best', '🎯 Best callers']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`pcl-${k}`}>{l}</button>)}</span></div>
    {tab === 'best' && <div className="pcl-rest pcl-best" data-testid="pcl-callers">{best.length ? best.map((c, i) => <span key={c.user} className={`pcl-chip ${c.proven ? 'is-pro' : ''}`} style={{ '--i': i }} data-tip={`@${c.user}: ${c.n} calls judged an hour later · typical ${c.medMult}× · ${c.wonPct}% up · best ${c.best}×${c.proven ? ' — proven' : ' — not proven yet (needs 3 calls, 1.2× typical, half up)'}`}>
      <b>{c.proven ? '🎯 ' : ''}@{c.user}</b><em className={c.medMult >= 1 ? 'm-pos' : 'm-neg'}>{c.medMult}×</em><small>{c.n} calls · {c.wonPct}% up</small></span>) : <small className="m-dim">The scoreboard starts now — each call is judged an hour after it is made.</small>}</div>}
    {tab !== 'best' && first && <button type="button" className="pcl-top" onClick={() => open(first)} data-testid="pcl-first" data-tip="Opens the coin. A callout is another holder's public call on Pump — read from Pump's own feed, not advice.">
      <span className="pcl-rank">{tab === 'top' ? '#1' : 'NEW'}</span>
      <span className="pcl-who"><b>{sym(first)}</b><small>@{first.user}{first.verified ? ' ✓' : ''} · {ago(first.at)}</small></span>
      <span className="pcl-say">{first.thesis ? `“${first.thesis}”` : 'called it out'}</span>
      <span className="pcl-nums"><b className={Number(first.mult) >= 1 ? 'm-pos' : 'm-neg'}>{first.mult ? `${first.mult}×` : '—'}</b><small>called at {big(first.atMc)}{first.pnlPct != null ? ` · caller ${sgn(first.pnlPct)}` : ''} · 👁 {Number(first.views || 0).toLocaleString()}</small></span></button>}
    {tab !== 'best' && rest.length > 0 && <div className="pcl-rest">{rest.map((c, i) => <button key={c.id} type="button" className="pcl-chip" style={{ '--i': i }} onClick={() => open(c)} data-tip={`@${c.user}${c.thesis ? `: “${c.thesis}”` : ''} — called at ${big(c.atMc)}, ${ago(c.at)}`}>
      <b>{sym(c)}</b><em className={Number(c.mult) >= 1 ? 'm-pos' : 'm-neg'}>{c.mult ? `${c.mult}×` : '—'}</em><small>@{c.user}</small></button>)}</div>}
    <small className="m-dim">Other people's calls, straight from Pump ({d.n} read). The multiple is price now vs the cap it was called at. A read, never advice.</small>
  </div>;
}

// 🔔 the owner's early-caller alert: 3+ different Pump callers on one coin inside 10 minutes while it is under this cap → one phone alert
export function CallAlert({ call }) {
  const d = usePumpCallouts(); const [v, setV] = useState(null); const [busy, setBusy] = useState(false);
  const cur = v ?? d?.alertCapK ?? 0; const caps = d?.alertCaps || [0, 50, 100, 250, 1000];
  const save = async capK => { setBusy(true); try { await call('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ callAlert: { capK } }) }); setV(capK); } catch { /* the select snaps back */ } finally { setBusy(false); } };
  return <label className="qp-alert" data-testid="call-alert" data-tip="A heads-up only: when 3 or more different Pump users call the same coin out inside 10 minutes and its cap is under your line, you get one inbox + phone alert (one per coin per 6 hours). Nothing is bought.">
    <span>🔔 Alert me on a call rush</span><select className="m-input" value={String(cur)} disabled={busy} onChange={e => save(Number(e.target.value))} aria-label="Call rush alert" data-testid="call-alert-cap">
      {caps.map(k => <option key={k} value={String(k)}>{k ? `coins under $${k >= 1000 ? `${k / 1000}M` : `${k}K`}` : 'off'}</option>)}</select></label>;
}

// ⚛ the animated Fuse bar on top of the swap-in pop-out: what leaves → what comes in, how many coins are flowing, the 20s refresh
export function FuseBanner({ out, count = 0, good = 0, tick = 0, lensLabel }) {
  return <div className="spx-banner" data-testid="swap-banner">
    <span className="spx-atom" aria-hidden="true"><i /><i /><i /><b>⚛</b></span>
    <span className="spx-title"><b>FUSE SWAP-IN</b><small>{out?.seat ? 'Fill the empty seat' : `Swap $${out?.symbol} for…`}</small></span>
    <span className="spx-wire" aria-hidden="true"><em className="spx-node">{out?.seat ? '🪑' : `$${out?.symbol}`}</em><span className="spx-flow"><i /></span><em className="spx-node is-in">?</em></span>
    <span className="spx-live"><b>{count}</b><small>coins · {lensLabel}</small>{good > 0 && <u>{good} good reads</u>}</span>
    <span className="spx-tick" data-tip="Every list refreshes every 20 seconds while this is open"><i key={tick} /></span>
  </div>;
}
