import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { AnimatedNumber } from '../terminal/AnimatedNumber';

const usd = v => (v == null ? '—' : v >= 1e9 ? `$${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Number(v).toFixed(v < 1 ? 6 : 2)}`);
const pct = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

// Sparkline from the daily snapshot history — growth lines that build themselves over time.
function Trend({ rows, k, label, fmt }) {
  const pts = rows.map(r => r[k]).filter(v => v != null);
  const first = pts[0]; const last = pts[pts.length - 1];
  const min = Math.min(...pts); const max = Math.max(...pts);
  const d = pts.length > 1 ? pts.map((v, i) => `${(i / (pts.length - 1)) * 100},${30 - ((v - min) / (max - min || 1)) * 28}`).join(' ') : null;
  const change = pts.length > 1 && first ? (last / first - 1) * 100 : null;
  return <div className="nm-trend">
    <small>{label}</small><b>{fmt(last)}</b>
    {d ? <svg viewBox="0 0 100 32" preserveAspectRatio="none"><polyline points={d} className={change >= 0 ? 'up' : 'down'} /></svg> : <em>history starts today — one point per day</em>}
    {change != null && <span className={change >= 0 ? 'positive' : 'negative'}>{pct(change)} over {pts.length}d</span>}
  </div>;
}

export function NumbersPanel({ call }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => { setBusy(true); call('/admin/numbers').then(x => { setD(x); setErr(null); }).catch(e => setErr(e.message)).finally(() => setBusy(false)); };
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (err && !d) return <p className="wp-bio">{err}</p>;
  if (!d) return <p className="wp-bio">Pulling the numbers…</p>;
  const m = d.market || {}; const h = d.holders || {}; const f = d.flow || {};
  const bs = m.buys24 != null && m.sells24 != null ? m.buys24 / Math.max(1, m.buys24 + m.sells24) * 100 : null;
  const liqRatio = m.liquidity && m.marketCap ? m.liquidity / m.marketCap * 100 : null;
  const tiles = [
    ['$FEE price', usd(m.price), pct(m.change?.h24), m.change?.h24 >= 0],
    ['Market cap', usd(m.marketCap), `FDV ${usd(m.fdv)}`],
    ['Liquidity', usd(m.liquidity), liqRatio != null ? `${liqRatio.toFixed(1)}% of MC` : '—', liqRatio >= 5],
    ['24h volume', usd(m.volume?.h24), `1h ${usd(m.volume?.h1)}`],
    ['Buy pressure 24h', bs != null ? `${bs.toFixed(0)}%` : '—', `${m.buys24 ?? '—'} buys / ${m.sells24 ?? '—'} sells`, bs >= 50],
    ['Holders', h.count != null ? h.count.toLocaleString() : '—', `${h.whales ?? '—'} whales ≥1%`],
    ['Top-10 concentration', h.top10 != null ? `${h.top10}%` : '—', `top wallet ${h.top1 ?? '—'}% · ${h.lpExcluded ?? 0} pool vaults excluded`, h.top10 != null && h.top10 < 35],
    ['Treasury SOL', d.treasury?.sol != null ? Number(d.treasury.sol).toFixed(3) : '—', Object.entries(d.treasury?.holdingsUsd || {}).map(([k, v]) => `${k} ${usd(v)}`).join(' · ') || 'no token holdings'],
  ];
  return <section className="nm" data-testid="cc-numbers">
    <header className="nm-head"><div><h3 className="live-gradient-text">The numbers</h3><small>Live from DexScreener, the chain and FEELESS receipts · refreshes every 30s</small></div><button type="button" className="btn-outline" onClick={load} disabled={busy}><RefreshCw size={13} className={busy ? 'spin' : ''} /> Refresh</button></header>
    {!d.market && <p className="nm-note">$FEE isn't indexed on any DEX yet (DexScreener has no pool for <code>{String(d.feeMint || '').slice(0, 6)}…</code>) — market tiles fill in automatically the moment a pool goes live.</p>}
    <div className="nm-tiles">{tiles.map(([label, big, sub, good]) => <div key={label} className={`nm-tile ${good === true ? 'good' : good === false ? 'bad' : ''}`}><small>{label}</small><b>{big}</b><span>{sub}</span></div>)}</div>
    <h4 className="nm-sub">Swap flow through FEELESS <small>(on-chain verified receipts)</small></h4>
    <div className="nm-flow">{[['24h', f.h24], ['7d', f.d7], ['All time', f.all]].map(([k, v]) => <div key={k}><small>{k}</small><b><AnimatedNumber value={v?.swaps || 0} format={x => Math.round(x).toLocaleString()} /> swaps</b><span>{(v?.solVolume ?? 0).toLocaleString()} SOL · {v?.traders ?? 0} traders</span></div>)}</div>
    <h4 className="nm-sub">Growth <small>(daily snapshots, kept forever)</small></h4>
    <div className="nm-trends">
      <Trend rows={d.history} k="price" label="Price" fmt={usd} />
      <Trend rows={d.history} k="marketCap" label="Market cap" fmt={usd} />
      <Trend rows={d.history} k="holders" label="Holders" fmt={v => (v == null ? '—' : v.toLocaleString())} />
      <Trend rows={d.history} k="liquidity" label="Liquidity" fmt={usd} />
    </div>
    <h4 className="nm-sub">Scanner output</h4>
    <div className="nm-flow">{[['Coins scanned', 'mintsScanned'], ['Snipers caught', 'snipers'], ['Bundlers caught', 'bundlers'], ['Repeat funders', 'flaggedFunders'], ['Blocklisted', 'blocklisted'], ['Creators tracked', 'creators']].map(([l, k]) => <div key={k}><small>{l}</small><b><AnimatedNumber value={d.scanner?.[k] || 0} format={x => Math.round(x).toLocaleString()} /></b></div>)}</div>
  </section>;
}
