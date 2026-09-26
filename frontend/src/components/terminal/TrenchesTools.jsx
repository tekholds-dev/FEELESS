import React, { useCallback, useEffect, useState } from 'react';
import { Flame, Crown, Megaphone, Zap, RefreshCw } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { AnimatedNumber } from './AnimatedNumber';
import { formatUSD } from '../../lib/dexscreener';
import { LivePrice, LiveChange24 } from './LiveCells';

const fmtX = v => (v == null ? '—' : `${v >= 100 ? v.toFixed(0) : v.toFixed(2)}×`);
const ago = s => { const d = Date.now() / 1000 - s; return d < 60 ? `${Math.round(d)}s` : d < 3600 ? `${Math.round(d / 60)}m` : d < 86400 ? `${Math.round(d / 3600)}h` : `${Math.round(d / 86400)}d`; };

function usePoll(path, ms) {
  const [data, setData] = useState(null);
  const load = useCallback(() => fetch(apiUrl(path)).then(r => (r.ok ? r.json() : null)).then(d => d && setData(d)).catch(() => {}), [path]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, ms); return () => clearInterval(t); }, [load, ms]);
  return data;
}

export function TrenchHero({ ecosystemName }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const board = usePoll('/api/reputation/calls/leaderboard?days=1', 30000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600);
  const callers = new Set(lastHour.map(c => c.caller)).size;
  const best = calls.filter(c => Date.now() / 1000 - c.at < 86400).reduce((b, c) => (!b || (c.peakX || 0) > (b.peakX || 0) ? c : b), null);
  const heat = Math.min(100, lastHour.length * 8 + callers * 10);
  return <section className="trench-hero" data-testid="trench-hero">
    <div className="trench-hero-copy">
      <span className="eyebrow">{ecosystemName.toUpperCase()} · LIVE FLOOR</span>
      <h1 className="trenches-font trench-title">The Trenches</h1>
      <p>Every coin posted here is logged as a <b>call</b> — priced by the server the second it lands and tracked forever. Talk is cheap. The ledger isn't.</p>
    </div>
    <div className="trench-heat">
      <div className="heat-gauge" style={{ '--heat': `${heat}%` }}><i /><span><AnimatedNumber value={heat} format={v => Math.round(v)} /><small>HEAT</small></span></div>
      <div className="trench-stats">
        <div><small>CALLS / HR</small><b><AnimatedNumber value={lastHour.length} format={v => Math.round(v)} /></b></div>
        <div><small>ACTIVE CALLERS</small><b><AnimatedNumber value={callers} format={v => Math.round(v)} /></b></div>
        <div><small>BEST CALL 24H</small><b className="positive">{best ? `${best.symbol} ${fmtX(best.peakX)}` : '—'}</b></div>
        <div><small>TOP CALLER TODAY</small><b>{board?.rows?.[0]?.caller || '—'}</b></div>
      </div>
    </div>
  </section>;
}

export function HotCalls({ onPick }) {
  const hot = usePoll('/api/reputation/calls/hot?minutes=180', 15000);
  const rows = hot?.rows || [];
  return <section className="trench-tool" data-testid="hot-calls"><div className="trench-tool-head"><Flame size={14} /><h3 className="trenches-font">Hot CAs</h3><small>most-called · 3h</small></div>
    {!rows.length && <p className="trench-empty">No calls in the last 3 hours. Paste a CA in chat to start the ledger.</p>}
    {rows.map(r => <button type="button" key={r.pairAddress} className="hot-row" onClick={() => onPick?.(r)}>
      {r.imageUrl ? <img src={r.imageUrl} alt="" /> : <i>{(r.symbol || '?').slice(0, 2)}</i>}
      <b>{r.symbol}</b><small>{r.callers} caller{r.callers === 1 ? '' : 's'} · {r.calls} call{r.calls === 1 ? '' : 's'}</small>
      <span className={(r.x || 1) >= 1 ? 'positive' : 'negative'}><AnimatedNumber value={r.x || 1} format={fmtX} /></span>
    </button>)}
  </section>;
}

export function LiveCalls({ onPick }) {
  const data = usePoll('/api/reputation/calls/recent?limit=25', 10000);
  const calls = data?.calls || [];
  return <section className="trench-tool" data-testid="live-calls"><div className="trench-tool-head"><Megaphone size={14} /><h3 className="trenches-font">Live calls</h3><small>× since called</small></div>
    {!calls.length && <p className="trench-empty">The ledger is empty. First caller to post a CA sets the record.</p>}
    <div className="live-call-list">{calls.map(c => <button type="button" key={c.id} className="live-call" onClick={() => onPick?.(c)}>
      <span className="caller">{c.caller}</span><b>{c.symbol}</b>
      <small>@ {formatUSD(c.mcAtCall)} MC · {ago(c.at)} ago</small>
      <span className={`call-x ${(c.x || 1) >= 1 ? 'up' : 'down'}`}><AnimatedNumber value={c.x || 1} format={fmtX} /><em>peak {fmtX(c.peakX)}</em></span>
    </button>)}</div>
  </section>;
}

export function CallerBoard() {
  const [days, setDays] = useState(7);
  const data = usePoll(`/api/reputation/calls/leaderboard?days=${days}`, 30000);
  const rows = data?.rows || [];
  return <section className="trench-tool" data-testid="caller-board"><div className="trench-tool-head"><Crown size={14} /><h3 className="trenches-font">Caller board</h3>
    <div className="caller-days">{[1, 7, 30].map(d => <button type="button" key={d} className={days === d ? 'active' : ''} onClick={() => setDays(d)}>{d}d</button>)}</div></div>
    {!rows.length && <p className="trench-empty">No ranked callers yet for this window.</p>}
    {rows.slice(0, 10).map((r, i) => <div key={r.caller} className="caller-row">
      <span className="rank">{i + 1}</span><b>{r.caller}</b>
      <span title="calls that reached 2× or more"><small>HIT</small>{Math.round(r.hitRate * 100)}%</span>
      <span><small>AVG PEAK</small>{fmtX(r.avgPeakX)}</span>
      <span><small>CALLS</small>{r.calls}</span>
      {r.rugs > 0 && <span className="negative"><small>DUDS</small>{r.rugs}</span>}
    </div>)}
    <p className="trench-foot"><Zap size={11} /> Hit = a call that reached 2× from the server-recorded price. Permanent and unfakeable — nobody can edit a call after it lands.</p>
  </section>;
}

const FEATURES = [
  ['📣', 'Every call is on the record', 'Paste a CA in chat and it becomes a call — priced by the server the second it lands. No edits, no deletes, no fake entries.'],
  ['🎯', 'Callers earn a track record', 'Hit rate, average peak ×, duds. The Caller Board shows who actually finds winners — and who just talks.'],
  ['🧪', 'Every coin gets an Edge Score', 'Order flow, liquidity depth, creator reputation, snipers and bundles — one grade, every reason shown.'],
  ['⚡', 'Trade without leaving', 'Quick-buy in SOL or USD right next to the chart. Anything into $FEE is always fee-free.'],
  ['🐂', 'Bulls · Trenches · Bears', 'Every coin has three rooms. Pick your side, react, and watch your calls play out live.'],
  ['🐱', 'Fee is watching too', 'Toggle Fee\'s trades onto any chart and see exactly where the Leader cat bought and sold.'],
];

// Front page for the Trenches: what it is, live proof it's alive, and one button onto the floor.
export function TrenchLanding({ ecosystemName, onEnter }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const board = usePoll('/api/reputation/calls/leaderboard?days=7', 30000);
  const hot = usePoll('/api/reputation/calls/hot?minutes=1440', 30000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600).length;
  const callers = new Set(calls.filter(c => Date.now() / 1000 - c.at < 86400).map(c => c.caller)).size;
  const top = board?.rows?.[0];
  const hottest = hot?.rows?.[0];
  return <section className="trench-landing" data-testid="trench-landing">
    <div className="trench-landing-hero">
      <span className="eyebrow">{ecosystemName.toUpperCase()} · COMMUNITY FLOOR</span>
      <h1 className="trenches-font trench-landing-title">The Trenches</h1>
      <p>Where calls get made and receipts get kept. Chat, chart, trade and track who's actually right — all on one floor.</p>
      <div className="trench-landing-live">
        <div><small>CALLS LAST HOUR</small><b><AnimatedNumber value={lastHour} format={v => String(Math.round(v))} /></b></div>
        <div><small>CALLERS TODAY</small><b><AnimatedNumber value={callers} format={v => String(Math.round(v))} /></b></div>
        <div><small>TOP CALLER · 7D</small><b>{top ? `${top.caller} · ${Math.round(top.hitRate * 100)}%` : '—'}</b></div>
        <div><small>HOTTEST CA · 24H</small><b>{hottest ? `${hottest.symbol} ${fmtX(hottest.x)}` : '—'}</b></div>
      </div>
      <button type="button" className="lets-trench trenches-font" onClick={onEnter} data-testid="lets-trench">Let's Trench →</button>
    </div>
    <div className="trench-features">{FEATURES.map(([icon, title, text]) => <article key={title}><span>{icon}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
  </section>;
}

export function TrenchBar({ onAbout }) {
  const recent = usePoll('/api/reputation/calls/recent?limit=100', 15000);
  const calls = recent?.calls || [];
  const lastHour = calls.filter(c => Date.now() / 1000 - c.at < 3600);
  const best = calls.filter(c => Date.now() / 1000 - c.at < 86400).reduce((b, c) => (!b || (c.peakX || 0) > (b.peakX || 0) ? c : b), null);
  return <div className="trench-bar" data-testid="trench-bar">
    <button type="button" onClick={onAbout} className="trench-bar-about">← About</button>
    <b className="trenches-font">The Trenches</b>
    <span><small>CALLS/HR</small><AnimatedNumber value={lastHour.length} format={v => String(Math.round(v))} /></span>
    <span><small>CALLERS</small><AnimatedNumber value={new Set(lastHour.map(c => c.caller)).size} format={v => String(Math.round(v))} /></span>
    <span><small>BEST 24H</small>{best ? `${best.symbol} ${fmtX(best.peakX)}` : '—'}</span>
  </div>;
}

const TREND_SORTS = [
  { id: 'hot', label: '🔥 Hot', score: p => Number(p.volume?.h24) || 0 },
  { id: 'gainers', label: '🚀 Gainers', score: (p, tf) => Number(p.priceChange?.[tf]) || -1e9 },
  { id: 'losers', label: '🩸 Dips', score: (p, tf) => -(Number(p.priceChange?.[tf]) || 1e9) },
  { id: 'pressure', label: '🟢 Buy pressure', score: p => { const t = p.txns?.h1 || {}; const b = Number(t.buys) || 0; const s = Number(t.sells) || 0; return b + s >= 20 ? b / (b + s) : -1; } },
  { id: 'new', label: '✨ Newest', score: p => Number(p.pairCreatedAt) || 0 },
  { id: 'liq', label: '💧 Liquidity', score: p => Number(p.liquidity?.usd) || 0 },
];
const TFS = [['m5', '5m'], ['h1', '1h'], ['h6', '6h'], ['h24', '24h']];

export function TrendingCards({ pairs = [], onPick }) {
  const [sort, setSort] = useState('hot');
  const [tf, setTf] = useState('h24');
  const [fresh, setFresh] = useState({});
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const merged = pairs.filter(p => p?.baseToken?.symbol).map(p => fresh[p.pairAddress] || p);
  const scorer = TREND_SORTS.find(x => x.id === sort) || TREND_SORTS[0];
  const list = [...merged].sort((a, b) => scorer.score(b, tf) - scorer.score(a, tf)).slice(0, 12);
  const listKey = merged.map(p => `${p.chainId}:${p.pairAddress}`).join(',');
  // Pull fresh numbers straight from DexScreener for every coin in the grid.
  const refresh = useCallback(async () => {
    const byChain = {};
    listKey.split(',').filter(Boolean).forEach(k => { const [c, a] = k.split(':'); (byChain[c] = byChain[c] || []).push(a); });
    setRefreshing(true);
    try {
      const next = {};
      await Promise.all(Object.entries(byChain).flatMap(([chain, addrs]) => {
        const chunks = []; for (let i = 0; i < addrs.length; i += 30) chunks.push(addrs.slice(i, i + 30));
        return chunks.map(c => fetch(`https://api.dexscreener.com/latest/dex/pairs/${chain}/${c.join(',')}`).then(r => (r.ok ? r.json() : null)).then(d => (d?.pairs || []).forEach(p => { next[p.pairAddress] = p; })).catch(() => {}));
      }));
      setFresh(f => ({ ...f, ...next })); setUpdatedAt(Date.now());
    } finally { setRefreshing(false); }
  }, [listKey]);
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) refresh(); }, 30000); return () => clearInterval(t); }, [refresh]);
  if (!list.length) return null;
  const tfLabel = TFS.find(x => x[0] === tf)?.[1];
  return <section className="trend-cards" data-testid="trend-cards">
    <div className="trend-cards-head"><h2 className="trenches-font live-gradient-text">Trending right now</h2><small>Pick a coin and trench it — chart, chat and quick trade open together.</small>
      <div className="trend-controls">
        <div className="trend-sorts" role="tablist">{TREND_SORTS.map(x => <button key={x.id} type="button" role="tab" aria-selected={sort === x.id} className={sort === x.id ? 'active' : ''} onClick={() => setSort(x.id)}>{x.label}</button>)}</div>
        <div className="trend-tfs">{TFS.map(([k, l]) => <button key={k} type="button" className={tf === k ? 'active' : ''} onClick={() => setTf(k)}>{l}</button>)}</div>
        <button type="button" className={`trend-refresh ${refreshing ? 'spinning' : ''}`} onClick={refresh} disabled={refreshing} title={updatedAt ? `Updated ${new Date(updatedAt).toLocaleTimeString()}` : 'Refresh from DexScreener'} aria-label="Refresh trending"><RefreshCw size={14} />{refreshing ? 'Refreshing' : 'Refresh'}</button>
      </div>
    </div>
    <div className="trend-grid">{list.map((p, i) => {
      const tx = p.txns?.h1 || {}; const b = Number(tx.buys) || 0; const s = Number(tx.sells) || 0;
      const share = b + s ? b / (b + s) : null;
      const up = Number(p.priceChange?.h24) >= 0;
      const m5 = Number(p.priceChange?.[tf]);
      return <article key={p.pairAddress} className={`trend-card ${up ? 'is-up' : 'is-down'}`} style={{ animationDelay: `${i * 40}ms` }} onClick={() => onPick?.(p)} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && onPick?.(p)}>
        <div className="trend-top">{p.info?.imageUrl ? <img src={p.info.imageUrl} alt="" /> : <i>{p.baseToken.symbol.slice(0, 2)}</i>}<div><b>{p.baseToken.symbol}</b><small>{p.baseToken.name}</small></div><span className="trend-rank">#{i + 1}</span></div>
        <div className="trend-price"><LivePrice pair={p} precise /><LiveChange24 pair={p} /></div>
        <div className="trend-stats"><span><small>MC</small>{formatUSD(p.marketCap || p.fdv)}</span><span><small>VOL 24H</small>{formatUSD(p.volume?.h24)}</span><span><small>{tfLabel.toUpperCase()}</small><em className={Number.isFinite(m5) ? (m5 >= 0 ? 'positive' : 'negative') : ''}>{Number.isFinite(m5) ? `${m5 >= 0 ? '+' : ''}${m5.toFixed(1)}%` : '—'}</em></span></div>
        {share != null && <div className="trend-pressure" title={`${b} buys / ${s} sells in the last hour`}><i style={{ width: `${share * 100}%` }} /><small>{Math.round(share * 100)}% buys · 1h</small></div>}
        <span className="trend-go trenches-font">Trench it →</span>
      </article>;
    })}</div>
  </section>;
}
