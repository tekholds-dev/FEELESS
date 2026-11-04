import React, { useEffect, useRef, useState } from 'react';
import { Hint } from '../Hint';
import { Glyph } from '../Glyph';
import { formatUSD, shortAddress } from '../../lib/dexscreener';

const ago = ts => { const s = Math.max(0, Date.now() / 1000 - ts); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };
const usePoll = (url, ms) => { const [d, setD] = useState(null); useEffect(() => { let a = true; const l = () => fetch(url).then(r => r.json()).then(x => a && setD(x)).catch(() => {}); l(); const t = setInterval(l, ms); return () => { a = false; clearInterval(t); }; }, [url, ms]); return d; };

// Weekly caller league (Call Ledger).
export function CallerLeague() {
  const d = usePoll('/api/reputation/league', 60000);
  const left = d ? Math.max(0, d.weekEnd - Date.now() / 1000) : 0;
  return <section className="meta-panel league" data-testid="caller-league">
    <div className="mp-head"><h2><Glyph name="trophy" tone="gold" size={24} /> <span className="live-gradient-text">Weekly Caller League</span> <Hint text="Points = calls ×2 + hit-rate ×50 + peak bonus. Resets every Monday 00:00 UTC." /></h2><span>{d ? `ends in ${Math.floor(left / 86400)}d ${Math.floor((left % 86400) / 3600)}h` : ''}</span></div>
    <p className="wp-bio">Drop CAs in chat — every call is tracked live. Points = calls ×2 + hit-rate ×50 + peak bonus. Top 3 each week win league badges and a FEELESS airdrop.</p>
    {!d ? <p className="wp-bio">Loading…</p> : !(d.rows || []).length ? <p className="wp-bio">No calls this week yet — be the first on the board.</p> : <div className="league-rows">{(d.rows || []).slice(0, 20).map((r, i) => <a key={r.address} href={`/terminal/profile/${r.address}`} className={`league-row r${i + 1}`}>
      <b className="lr-rank">{['🥇', '🥈', '🥉'][i] || i + 1}</b><span className="lr-name">{r.caller}</span><span>{r.calls} calls</span><span>{Math.round((r.hitRate || 0) * 100)}% 2×</span><span>best avg {(r.avgPeakX || 1).toFixed(2)}×</span><b className="lr-pts">{r.points}</b></a>)}</div>}
  </section>;
}

// Rug radar + whale feed.
export function RadarPanel({ compact }) {
  const d = usePoll('/api/reputation/radar', 30000);
  return <section className={`meta-panel radar ${compact ? 'compact' : ''}`} data-testid="rug-radar">
    <div className="mp-head"><h2><Hint text="Watches coins people called or starred. Alerts when liquidity drops 30%+ or price halves within 15 minutes, and lists trades over $2.5K." /> <Glyph name="radar" tone="rose" size={20} /> Rug radar <small>watching {d?.watching ?? '…'} coins</small></h2><span><i className="flr-dot" /> live</span></div>
    <div className="radar-cols">
      <div><h4>Alerts</h4>{!d?.events?.length ? <p className="wp-bio">No liquidity pulls or dumps detected on watched coins. 🛡️</p> : d.events.map((e, i) => <a key={i} href={`/terminal/chat?chain=solana&pair=${e.pair}&room=bulls${e.kind === 'snipers-out' ? '&buy=1' : ''}`} className={`radar-ev k-${e.kind}`}><b>{e.kind === 'rug' ? '🚨 LIQ PULL' : e.kind === 'snipers-out' ? '🎯 SNIPERS OUT' : '📉 DUMP'}</b><span>{e.symbol && <strong className="radar-coin">${e.symbol}</strong>}{e.mcap > 0 && <em className="radar-mc">MC ${e.mcap >= 1e6 ? `${(e.mcap / 1e6).toFixed(2)}M` : `${(e.mcap / 1e3).toFixed(1)}K`}</em>} {e.text}</span><small>{ago(e.at)} ago</small>{e.kind === 'snipers-out' && <em className="radar-buy">Buy →</em>}</a>)}</div>
      <div><h4>Whale trades ($2.5K+)</h4>{!d?.whales?.length ? <p className="wp-bio">Scanning watched coins for big trades…</p> : d.whales.slice(0, compact ? 6 : 20).map(w => <a key={w.tx} href={`https://solscan.io/tx/${w.tx}`} target="_blank" rel="noopener noreferrer" className={`radar-ev k-${w.kind}`}><b>{w.kind === 'buy' ? 'BUY' : 'SELL'} {formatUSD(w.usd)}</b><span>${w.symbol || '?'} · {shortAddress(w.wallet)}</span><small>{w.at ? ago(Date.parse(w.at) / 1000) : ''}</small></a>)}</div>
    </div>
  </section>;
}

// Shareable PnL card — drawn on a canvas, downloaded as PNG.
