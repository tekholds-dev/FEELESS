import React, { useEffect, useState } from 'react';
import { formatUSD } from '../../lib/dexscreener';

const sol = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(4)} SOL`);
const ago = ts => { const m = Math.floor((Date.now() / 1000 - ts) / 60); return m < 60 ? `${m}m` : m < 1440 ? `${Math.floor(m / 60)}h` : `${Math.floor(m / 1440)}d`; };

// Fee the Leader cat's full profile: live book, every trade, what happened after each sell, and how it's learning.
export function FeeCatProfile({ catId = 'leader' }) {
  const [d, setD] = useState(null);
  const [tab, setTab] = useState('trades');
  useEffect(() => {
    let alive = true;
    const load = () => fetch(`/api/cats/${catId}/profile`).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 20000);
    return () => { alive = false; clearInterval(t); };
  }, [catId]);
  if (!d) return <section className="fcp" data-testid="feecat-profile"><p className="wp-bio">Loading Fee…</p></section>;
  const c = d.cat; const L = d.learning;
  return <section className="fcp" data-testid="feecat-profile">
    <header className="fcp-head">
      <div className="fcp-avatar">🐱<i className="flr-dot" /></div>
      <div className="fcp-id"><h2 className="live-gradient-text">{c.name} <small>{c.title || 'The Leader'}</small></h2><span>{c.strategyLabel} · level {c.level} · {c.status === 'running' ? 'trading live (paper)' : c.status}</span></div>
      <div className="fcp-kpis">
        <span><small>Balance</small><b>{Number(c.balanceSol).toFixed(2)} SOL</b></span>
        <span><small>Realized PnL</small><b className={c.realizedPnlSol >= 0 ? 'positive' : 'negative'}>{sol(c.realizedPnlSol)}</b></span>
        <span><small>Win rate</small><b>{c.winRate != null ? `${c.winRate}%` : '—'}</b></span>
        <span><small>Trades</small><b>{d.stats.trades}</b></span>
        <span><small>Best / worst</small><b>{sol(d.stats.best)} / {sol(d.stats.worst)}</b></span>
      </div>
    </header>
    {c.positions?.length > 0 && <div className="fcp-open"><h4>Open now</h4>{c.positions.map(p => <a key={p.pairAddress} className="fcp-pos" href={`/?coin=solana:${p.pairAddress}`} target="_blank" rel="noopener noreferrer">
      <b>${p.symbol}</b><span className={p.currentChange >= 0 ? 'positive' : 'negative'}>{p.currentChange >= 0 ? '+' : ''}{Number(p.currentChange).toFixed(1)}%</span><small>{Number(p.costSol).toFixed(2)} SOL · peak +{Number(p.peakChange || 0).toFixed(1)}%{p.scaled ? ' · runner' : ''}{p.conviction ? ` · ${p.conviction}×` : ''}</small></a>)}</div>}
    <nav className="fcp-tabs">{[['trades', 'Trades'], ['after', 'After the sell'], ['brain', 'Learning']].map(([k, l]) => <button key={k} type="button" className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{l}</button>)}</nav>
    {tab === 'trades' && <div className="fcp-list">{!d.trades.length ? <p className="wp-bio">No trades yet.</p> : d.trades.map(t => <div key={t.id} className={`fcp-trade t-${t.type.toLowerCase()}`}><em>{t.type}</em><p>{t.detail}</p><small>{ago(t.ts / 1000)} ago{t.pnlSol != null ? ` · ${sol(t.pnlSol)}` : ''}</small></div>)}</div>}
    {tab === 'after' && <div className="fcp-list">{!d.exits.length ? <p className="wp-bio">No exits yet.</p> : d.exits.map(e => <a key={`${e.pairAddress}-${e.exitAt}`} className={`fcp-exit ${e.peakAfter >= 40 ? 'missed' : ''}`} href={`/?coin=solana:${e.pairAddress}`} target="_blank" rel="noopener noreferrer">
      <b>${e.symbol}</b><span>sold {e.changeAtExit >= 0 ? '+' : ''}{e.changeAtExit}% · {e.why}</span><span>after: best <b className="positive">+{e.peakAfter}%</b> · low <b className="negative">{e.lowAfter}%</b></span><small>{ago(e.exitAt)} ago{e.peakAfter >= 40 ? ' · 🧠 lesson: sold a runner' : ''}</small></a>)}</div>}
    {tab === 'brain' && <div className="fcp-brain">
      <p className="wp-bio">Fee watches every coin for 24h after selling. Runners it cut early loosen its exits; good exits pull it back to discipline. Bounded so it never gets reckless.</p>
      <div className="fcp-params">{Object.entries(L.params).map(([k, v]) => <span key={k}><small>{({ trailGive: 'Trailing give', runnerTrailGive: 'Runner trail', takeProfit: 'Scale-out at', scaleOutFraction: 'Scale-out size' })[k] || k}</small><b>{k === 'scaleOutFraction' ? `${Math.round(v * 100)}%` : `${k === 'takeProfit' ? '+' : ''}${v}%`}</b><em>{v !== L.defaults[k] ? `default ${k === 'scaleOutFraction' ? `${Math.round(L.defaults[k] * 100)}%` : `${L.defaults[k]}%`}` : 'default'}</em></span>)}</div>
      <div className="fcp-score"><span>🧠 Runners missed: <b>{L.missed}</b></span><span>✅ Good exits: <b>{L.good}</b></span></div>
      <div className="fcp-list">{L.log.map((x, i) => <div key={i} className={`fcp-trade ${x.missed ? 't-sell' : 't-buy'}`}><em>LEARN</em><p>{x.note}</p><small>{ago(x.at)} ago</small></div>)}{!L.log.length && <p className="wp-bio">First lessons land 6h after each exit.</p>}</div>
      <p className="wp-bio">Safety rules that never loosen: stop {d.rules.stopLoss}%, break-even at +{d.rules.breakEvenArm}%, skip top-10 &gt; {d.rules.maxTop10Pct}%, insiders &gt; {d.rules.maxInsiderPct}%, &gt;{d.rules.maxSnipers} snipers, &gt;{d.rules.maxBundled} bundled, no chasing &gt; +{d.rules.maxM5Chase}% in 5m. Paper trading on live prices — not financial advice.</p>
    </div>}
  </section>;
}
