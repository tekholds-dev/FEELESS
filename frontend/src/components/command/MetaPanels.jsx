import React, { useEffect, useRef, useState } from 'react';
import { formatUSD, shortAddress } from '../../lib/dexscreener';

const ago = ts => { const s = Math.max(0, Date.now() / 1000 - ts); return s < 60 ? `${Math.floor(s)}s` : s < 3600 ? `${Math.floor(s / 60)}m` : s < 86400 ? `${Math.floor(s / 3600)}h` : `${Math.floor(s / 86400)}d`; };
const usePoll = (url, ms) => { const [d, setD] = useState(null); useEffect(() => { let a = true; const l = () => fetch(url).then(r => r.json()).then(x => a && setD(x)).catch(() => {}); l(); const t = setInterval(l, ms); return () => { a = false; clearInterval(t); }; }, [url, ms]); return d; };

// Weekly caller league (Call Ledger).
export function CallerLeague() {
  const d = usePoll('/api/reputation/league', 60000);
  const left = d ? Math.max(0, d.weekEnd - Date.now() / 1000) : 0;
  return <section className="meta-panel league" data-testid="caller-league">
    <div className="mp-head"><h2 className="live-gradient-text">🏆 Weekly Caller League</h2><span>{d ? `ends in ${Math.floor(left / 86400)}d ${Math.floor((left % 86400) / 3600)}h` : ''}</span></div>
    <p className="wp-bio">Drop CAs in chat — every call is tracked live. Points = calls ×2 + hit-rate ×50 + peak bonus. Top 3 each week win league badges and a FEELESS airdrop.</p>
    {!d ? <p className="wp-bio">Loading…</p> : !d.rows.length ? <p className="wp-bio">No calls this week yet — be the first on the board.</p> : <div className="league-rows">{d.rows.slice(0, 20).map((r, i) => <a key={r.address} href={`/terminal/profile/${r.address}`} className={`league-row r${i + 1}`}>
      <b className="lr-rank">{['🥇', '🥈', '🥉'][i] || i + 1}</b><span className="lr-name">{r.caller}</span><span>{r.calls} calls</span><span>{Math.round((r.hitRate || 0) * 100)}% 2×</span><span>best avg {(r.avgPeakX || 1).toFixed(2)}×</span><b className="lr-pts">{r.points}</b></a>)}</div>}
  </section>;
}

// Rug radar + whale feed.
export function RadarPanel({ compact }) {
  const d = usePoll('/api/reputation/radar', 30000);
  return <section className={`meta-panel radar ${compact ? 'compact' : ''}`} data-testid="rug-radar">
    <div className="mp-head"><h2>📡 Rug radar <small>watching {d?.watching ?? '…'} coins</small></h2><span><i className="flr-dot" /> live</span></div>
    <div className="radar-cols">
      <div><h4>Alerts</h4>{!d?.events?.length ? <p className="wp-bio">No liquidity pulls or dumps detected on watched coins. 🛡️</p> : d.events.map((e, i) => <a key={i} href={`/terminal/coin/solana/${e.pair}`} className={`radar-ev k-${e.kind}`}><b>{e.kind === 'rug' ? '🚨 LIQ PULL' : '📉 DUMP'}</b><span>{e.text}</span><small>{ago(e.at)} ago</small></a>)}</div>
      <div><h4>🐋 Whale trades ($2.5K+)</h4>{!d?.whales?.length ? <p className="wp-bio">Scanning watched coins for big trades…</p> : d.whales.slice(0, compact ? 6 : 20).map(w => <a key={w.tx} href={`https://solscan.io/tx/${w.tx}`} target="_blank" rel="noopener noreferrer" className={`radar-ev k-${w.kind}`}><b>{w.kind === 'buy' ? 'BUY' : 'SELL'} {formatUSD(w.usd)}</b><span>${w.symbol || '?'} · {shortAddress(w.wallet)}</span><small>{w.at ? ago(Date.parse(w.at) / 1000) : ''}</small></a>)}</div>
    </div>
  </section>;
}

// Shareable PnL card — drawn on a canvas, downloaded as PNG.
export function PnlCard({ symbol, pnlPct, pnlSol, label = 'Fee 🐱', note }) {
  const ref = useRef(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const x = c.getContext('2d'); const W = 600, H = 315; c.width = W; c.height = H;
    const up = pnlPct >= 0; const g = x.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, '#04120b'); g.addColorStop(1, up ? '#0b3a26' : '#3a0b17'); x.fillStyle = g; x.fillRect(0, 0, W, H);
    x.strokeStyle = up ? '#00e9a0' : '#fa708c'; x.lineWidth = 3; x.strokeRect(10, 10, W - 20, H - 20);
    x.fillStyle = '#9fd3b6'; x.font = '600 18px sans-serif'; x.fillText('FEELESS', 36, 52);
    x.fillStyle = '#ffffff'; x.font = '700 34px sans-serif'; x.fillText(`$${symbol}`, 36, 110);
    x.fillStyle = up ? '#00e9a0' : '#fa708c'; x.font = '800 76px sans-serif'; x.fillText(`${up ? '+' : ''}${pnlPct.toFixed(1)}%`, 36, 200);
    x.fillStyle = '#cfe8da'; x.font = '500 18px sans-serif'; x.fillText(`${pnlSol != null ? `${pnlSol >= 0 ? '+' : ''}${pnlSol.toFixed(4)} SOL · ` : ''}${label}`, 36, 240);
    if (note) { x.fillStyle = '#7f9a8b'; x.font = '14px sans-serif'; x.fillText(note.slice(0, 70), 36, 272); }
    x.font = '64px serif'; x.fillText(up ? '🚀' : '🩸', W - 120, 110);
  }, [symbol, pnlPct, pnlSol, label, note]);
  const download = () => { const a = document.createElement('a'); a.href = ref.current.toDataURL('image/png'); a.download = `feeless-${symbol}-pnl.png`; a.click(); };
  return <div className="pnl-card"><canvas ref={ref} /><button type="button" className="btn-outline" onClick={download}>⬇ Save PnL card</button></div>;
}
