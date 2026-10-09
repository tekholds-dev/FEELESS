import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLivePrices } from '../lib/livePrices';
import { prefetchInterval } from '../lib/candles';
import { CoinVital, TrenchVital } from './CoinVital';
import { openWarRoom } from './WarRoomHost';
import { openMiniChart } from './MiniChart';
import { investigate } from './CaseFile';
import { addToCard } from './CoinDrawer';
import { price as fmtPx } from '../lib/num';
import { useCoinRead } from './terminal/ChartVitals';
import { Socials, FlowWindows, ChartPulse, PumpCall, Feeders } from './QuickPulse';
import '../styles/trenchSplit.css';

// ⚡ QUICK LOOK (owner, 2026-10-08: "a click to a hover chart, swap in etc with MAD TRENCH VITALS instead of the side panel"): one floating
// panel over the list — live chart on the left, every vital on the right, the actions in one row. ← / → step through the same list, Esc closes.
// Everything comes from the row the list already has (no extra fetch) + the shared live-price poller; the chart is the war room's PriceChart.
const PriceChart = React.lazy(() => import('./terminal/PriceChart').then(m => ({ default: m.PriceChart })));
let warmT = null;
export const warmCoin = r => {   // hover / focus a row: its 1m candles + the chart's code start loading before the click (after 140ms on the row — a pass-over starts nothing)
  if (!r?.pairAddress) return;
  clearTimeout(warmT);
  warmT = setTimeout(() => { try { prefetchInterval('solana', r.pairAddress, r.mint, '1m'); import('./terminal/PriceChart'); } catch { /* never block a hover */ } }, 140);
};
const big = v => { const n = Number(v) || 0; return !n ? '—' : n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${Math.round(n)}`; };
const sg = v => (v == null || !Number.isFinite(Number(v)) ? '—' : Math.abs(v) >= 1000 ? `${(v / 100 + 1).toFixed(1)}x` : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const age = h => (h == null ? '—' : h < 1 ? `${Math.max(1, Math.round(h * 60))}m` : h < 48 ? `${h.toFixed(h < 10 ? 1 : 0)}h` : `${Math.round(h / 24)}d`);
const pc = v => (v == null ? '—' : `${Number(v).toFixed(0)}%`);
const TFS = ['1m', '5m', '15m'];
const SCAN_KEYS = ['top10', 'dev', 'insiders', 'bundledN', 'snipersN', 'bundledPct', 'scanned'];   // what OUR holder scan reads (Jupiter's audit has only top-10 + dev)

export const WAIT = 'reading…';   // our holder scan for this coin is running right now
// the facts tiles: [label, value, bad?, tip]
// 🧮 three numbers no list shows: who is trading it (average trade), how hard it turns over (hour volume vs its cap) and how much
// of its cap you could actually sell into (pool vs cap)
export function edgeTiles(r) {
  const v = Number(r.vol1h) || 0; const t = Number(r.txns1h) || 0; const mc = Number(r.mcap) || 0; const liq = Number(r.liq) || 0;
  const avg = v > 0 && t > 0 ? v / t : null; const turn = v > 0 && mc > 0 ? (v / mc) * 100 : null; const depth = liq > 0 && mc > 0 ? (liq / mc) * 100 : null;
  return [
    ['AVG TRADE', avg == null ? '—' : `$${avg >= 100 ? Math.round(avg) : avg.toFixed(1)}`, avg != null && avg < 8, 'Hour volume ÷ trades: under ~$8 a trade is usually bots pinging each other'],
    ['TURNOVER', turn == null ? '—' : `${turn >= 100 ? Math.round(turn) : turn.toFixed(1)}%/h`, turn != null && turn < 2, 'Share of its whole market cap traded in the last hour — the higher, the more it is in play'],
    ['EXIT DEPTH', depth == null ? '—' : `${depth.toFixed(1)}%`, depth != null && depth < 3, 'Pool ÷ market cap: how much of the cap there is real money to sell into. Thin = hard to get out'],
    ['CALLERS', r.pc?.callers ? String(r.pc.callers) : '—', false, 'Pump users calling this coin out right now (Pump\'s own callouts feed)'],
    ['FEEDERS', r.fd?.n ? `${r.fd.n}${r.fd.active ? ` · ${r.fd.active} live` : ''}` : '—', false, 'New Pump coins paired with this coin — each of their buys routes through its pool'],
    ['HOLDERS 1H', r.win?.['1h']?.holderChg == null ? '—' : `${r.win['1h'].holderChg >= 0 ? '+' : ''}${Number(r.win['1h'].holderChg).toFixed(1)}%`, r.win?.['1h']?.holderChg < 0, 'Change in holder count this hour'],
  ];
}
export function factTiles(r) {
  const pace = Number(r.vol1h) > 0 && Number(r.vol5m) > 0 ? (r.vol5m * 12) / r.vol1h : null;
  const org = r.vital?.organicPct;
  return [
    ['TOP 10', pc(r.top10), r.top10 > 30, 'Share of supply the 10 biggest wallets hold'],
    ['DEV', pc(r.dev), r.dev > 10, 'What the creator still holds'],
    ['INSIDERS', r.insiders == null && r.scanning ? WAIT : pc(r.insiders), r.insiders > 8, 'Wallets linked to the launch'],
    ['BUNDLED', r.bundledN == null ? (r.scanning ? WAIT : '—') : String(r.bundledN), r.bundledN > 1, 'Wallets that bought in the launch bundle'],
    ['SNIPERS', r.snipersN == null ? (r.scanning ? WAIT : '—') : String(r.snipersN), r.snipersN > 5, 'Wallets that sniped the first blocks'],
    ['BUYERS', r.buyShare == null ? '—' : `${Math.round(r.buyShare)}%`, r.buyShare != null && r.buyShare < 45, 'Share of trades this hour that were buys'],
    ['HOLDERS', Number(r.holders) > 0 ? Number(r.holders).toLocaleString() : '—', false, 'Wallets holding it now'],
    ['ORGANIC', org == null ? '—' : `${Math.round(org)}%`, org != null && org < 5, 'Share of volume from real traders (Jupiter) — low = bots'],
    ['5M PACE', pace == null ? '—' : `${pace.toFixed(1)}×`, pace != null && pace < 0.5, '5-minute volume × 12 vs the hour: above 1× = speeding up'],
    ['TRADES/H', r.txns1h ? Number(r.txns1h).toLocaleString() : '—', r.txns1h != null && r.txns1h < 60, 'Trades in the last hour'],
    ...edgeTiles(r),
  ];
}

// ⏱ "updated 3s ago" beside LIVE (ticks every second; the read's own server time)
function Ago({ at }) {
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(x => x + 1), 1000); return () => clearInterval(t); }, []);
  if (!at) return null;
  const s = Math.max(0, Math.round(Date.now() / 1000 - Number(at)));
  return <small className="tql-ago"> · {s < 2 ? 'now' : `${s}s ago`}</small>;
}

export function TrenchQuick({ row, list = [], onClose, onPick, busy }) {
  const [r0, setR] = useState(row);
  useEffect(() => setR(row), [row]);
  // 🔴 LIVE while it is open: the list's own row is re-read every 20s (its read + meters move), the coin's FEELESS read every 20s
  // (vital, holder facts, socials, per-window flow, Pump callouts) and the price / 5m / 1h every 10s from the shared poller
  const live = useLivePrices(r0?.pairAddress ? [r0.pairAddress] : []).get(r0?.pairAddress);
  const read = useCoinRead(r0?.mint, live?.price);   // ⏱ re-read at the coin's own pace + whenever its price moves (a trade)
  const r = useMemo(() => { if (!r0) return r0; const fresh = list.find(x => x.mint === r0.mint) || r0; const rr = read?.mint === r0.mint ? read : null;
    const fill = {}; Object.entries(rr?.row || {}).forEach(([k, v]) => { if (v != null && k !== 'symbol' && k !== 'mint' && (fresh[k] == null || (rr.row.scanned === true && SCAN_KEYS.includes(k)))) fill[k] = v; });
    const f = rr?.facts || {};
    return { ...fresh, ...fill, scanning: !!rr?.scanning && rr?.row?.scanned !== true, vital: rr?.vital || fresh.vital, tv: fresh.tv || rr?.tv, pc: fresh.pc || rr?.pc || null, fd: fresh.fd || rr?.row?.fd || null, pairedWith: fresh.pairedWith || rr?.row?.pairedWith || null, win: f.win || null, site: fresh.site || fill.site || f.site, x: fresh.x || fill.x || f.x, tg: fresh.tg || fill.tg || f.tg }; }, [r0, list, read]);
  const [tf, setTf] = useState('1m');
  const [copied, setCopied] = useState(false);
  const idx = list.findIndex(x => x.mint === r?.mint);
  useEffect(() => {
    const k = e => { if (e.key === 'Escape') onClose();
      if ((e.key === 'ArrowRight' || e.key === 'ArrowLeft') && idx >= 0 && list.length > 1) { e.preventDefault(); setR(list[(idx + (e.key === 'ArrowRight' ? 1 : list.length - 1)) % list.length]); } };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [idx, list, onClose]);
  useEffect(() => { if (list[idx + 1]) warmCoin(list[idx + 1]); }, [idx, list]);   // the next coin is ready before → is pressed
  const pair = useMemo(() => (r ? { chainId: 'solana', pairAddress: r.pairAddress, baseToken: { address: r.mint, symbol: r.symbol }, info: { imageUrl: r.logo } } : null), [r?.pairAddress, r?.mint, r?.symbol, r?.logo]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (!r) return null;
  const price = live?.price ?? r.price; const mc = live?.mc || r.mcap;
  const useMc = mc > 0 && price > 0;
  const tone = r.tv?.call?.[2] || 'warn';
  const copy = () => { try { navigator.clipboard?.writeText(r.mint); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { /* no clipboard */ } };
  const safe = r.safe === true ? ['✅ safe', 'is-safe'] : r.safe === false ? ['⚠ failed', 'is-bad'] : ['❔ unscanned', 'is-unk'];
  return createPortal(<div className="tql-shade" role="presentation" onClick={onClose} data-testid="trench-quick">
    <section className={`tql tql-${tone}`} role="dialog" aria-modal="true" aria-label={`$${r.symbol} quick look`} onClick={e => e.stopPropagation()}>
      <header className="tql-head">
        <span className="tsp-av is-big" aria-hidden="true">{String(r.symbol || '?').slice(0, 1)}{r.logo && <img src={r.logo} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} />}</span>
        <div className="tql-title"><b>${r.symbol} <span className={`tql-live is-${read?.pace?.key || 'quiet'}`} data-tip={`Price every 10 seconds · vitals re-read at this coin's pace (${{ hot: 'hot: every 5s', busy: 'busy: every 10s', quiet: 'quiet: every 20s' }[read?.pace?.key || 'quiet']}) and the moment its price moves`}><i />LIVE{read?.pace?.key === 'hot' ? ' · HOT' : ''}<Ago at={read?.at} /></span></b>
          <small>{age(r.ageH)} old · {big(mc)} cap · pool {r.liq ? big(r.liq) : r.curve || r.curvePct != null ? 'on curve' : '—'} · {big(r.vol1h)}/h</small></div>
        {'safe' in r && <span className={`tql-safe ${safe[1]}`} data-tip={r.safe === false ? `Did not pass: ${(r.fails || []).join(' · ')}` : r.safe ? 'Passed every safety check' : 'Holders not scanned yet — unknown, not safe'}>{safe[0]}</span>}
        <span className="tql-px"><b>{useMc ? big(mc) : fmtPx(price)}</b>
          <em className={(live?.m5 ?? r.chg5m) >= 0 ? 'm-pos' : 'm-neg'}>{sg(live?.m5 ?? r.chg5m)} 5m</em><em className={(live?.h1 ?? r.chg1h) >= 0 ? 'm-pos' : 'm-neg'}>{sg(live?.h1 ?? r.chg1h)} 1h</em></span>
        {list.length > 1 && idx >= 0 && <span className="tql-nav"><button type="button" onClick={() => setR(list[(idx + list.length - 1) % list.length])} aria-label="Previous coin" data-testid="tql-prev">‹</button>
          <small>{idx + 1}/{list.length}</small><button type="button" onClick={() => setR(list[(idx + 1) % list.length])} aria-label="Next coin" data-testid="tql-next">›</button></span>}
        <button type="button" className="tql-x" onClick={onClose} aria-label="Close">×</button>
      </header>
      <div className="tql-body">
        <div className="tql-chart">
          <div className="tql-bar"><span className="m-label">📈 LIVE · {useMc ? 'MARKET CAP' : 'PRICE'}</span>
            <span className="m-seg" role="radiogroup" aria-label="Chart timeframe">{TFS.map(t => <button key={t} type="button" role="radio" aria-checked={tf === t} className={tf === t ? 'active' : ''} onClick={() => setTf(t)} data-testid={`tql-tf-${t}`}>{t.toUpperCase()}</button>)}</span></div>
          {r.pairAddress ? <React.Suspense fallback={<p className="m-dim tql-wait">Loading chart…</p>}>
            <PriceChart key={`${r.pairAddress}-${tf}-${useMc ? 'mc' : 'px'}`} pair={{ ...pair, priceUsd: price ?? null, marketCap: mc || null }} interval={tf} metric={useMc ? 'marketCap' : 'price'} showVolume={false} />
          </React.Suspense> : <p className="m-dim tql-wait">No pool for this coin yet.</p>}
        </div>
        <div className="tql-vitals" data-testid="tql-vitals">
          <Socials r={r} />
          {r.tv && <TrenchVital r={r} />}
          <PumpCall pc={r.pc} />
          <Feeders r={r} />
          {r.curvePct != null && <div className="tql-bond" data-tip="How far along its launch curve: at 100% it graduates to a pool"><small>🔔 BOND</small><span><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, r.curvePct / 100))})` }} /></span><b>{Math.round(r.curvePct)}%</b></div>}
          {r.buyShare != null && <div className="tql-press" data-tip="Buys vs sells this hour"><small>BUY</small><span><i style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, r.buyShare / 100))})` }} /></span><small>SELL</small><b>{Math.round(r.buyShare)}%</b></div>}
          {r.vital && <CoinVital r={r} only="vital" />}
          <ChartPulse pairAddress={r.pairAddress} mint={r.mint} tf={tf} />
          <FlowWindows win={r.win} tf={tf} />
          <div className="tql-facts">{factTiles({ ...r, chg5m: live?.m5 ?? r.chg5m, chg1h: live?.h1 ?? r.chg1h, mcap: mc || r.mcap }).map(([l, x, bad, tip]) => <div key={l} className={bad ? 'bad' : ''} data-tip={x === WAIT ? `${tip} — FEELESS is reading this coin's holders on-chain right now; it fills in within about half a minute.` : x === '—' ? `${tip} — not read for this coin (unknown, never a clean zero).` : tip}><small>{l}</small><b key={String(x)} className={x === WAIT ? 'is-wait' : 'tql-flip'}>{x}</b></div>)}</div>
          {r.safe === false && (r.fails || []).length > 0 && <p className="tql-fails">⚠ {(r.fails || []).join(' · ')}</p>}
        </div>
      </div>
      <footer className="tql-acts">
        {onPick && <button type="button" className="m-btn primary m-go" disabled={!!busy} onClick={() => { onPick(r); onClose(); }} data-testid="tql-pick">⚡ Pick for the card</button>}
        {!onPick && <button type="button" className="m-btn primary m-go" onClick={() => { onClose(); addToCard({ mint: r.mint, pairAddress: r.pairAddress, symbol: r.symbol, runner: true }); }} data-testid="tql-add">＋ Add to card</button>}
        <button type="button" className="m-btn" onClick={() => { onClose(); openWarRoom(pair); }} data-testid="tql-war">⚔ War room</button>
        <button type="button" className="m-btn" onClick={() => { onClose(); openMiniChart(pair); }} data-testid="tql-mini">📌 Mini chart</button>
        <button type="button" className="m-btn" onClick={() => { onClose(); investigate(r.mint); }} data-testid="tql-case">🔎 Case file</button>
        <button type="button" className="m-btn" onClick={copy} data-testid="tql-ca">{copied ? '✓ Copied' : '⧉ Copy CA'}</button>
        <small className="m-dim tql-note">← → next coin · Esc closes · a read, never a promise</small>
      </footer>
    </section></div>, document.body);
}

export default TrenchQuick;
