import React, { useEffect, useState } from 'react';

// Fee's brain, read live: her setup memory (which kinds of entries win), what she vetoed, how her exits
// and entries are tuned right now, and her scoreboard. Everything here comes from her own closed trades.
const NICE = { h1: '1h move', flow: 'Buy/sell flow', depth: 'Liquidity depth', age: 'Pool age', m5: '5m heat', mc: 'Market cap', lane: 'Lane', gap: 'Fair value gap' };
const label = s => { const [f, b] = s.split('='); return `${NICE[f] || f}: ${b}`; };

export function FeeBrain({ catId = 'leader' }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(`/api/cats/${catId}/profile`).then(r => r.json()).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [catId]);
  if (!d?.cat) return <p className="cc-empty">Reading Fee's brain…</p>;
  const c = d.cat, L = d.learning || {}, pb = L.playbook || { best: [], worst: [] };
  const Row = ({ r }) => <div className={`fb-row ${r.edge >= 0 ? 'up' : 'down'}`}><span>{label(r.setup)}</span><i style={{ width: `${Math.min(100, Math.abs(r.edge) * 100)}%` }} /><b>{r.winRate}% · {r.avgRet >= 0 ? '+' : ''}{r.avgRet}%</b><small>{r.n} trades</small></div>;
  return <div className="fee-brain" data-testid="fee-brain">
    <div className="fb-kpis">{[['Realized', `${Number(c.realizedPnlSol || 0) >= 0 ? '+' : ''}${Number(c.realizedPnlSol || 0).toFixed(3)} SOL`, Number(c.realizedPnlSol || 0) >= 0 ? 'up' : 'down'], ['Win rate', c.winRate != null ? `${c.winRate}%` : '—', ''], ['Trades remembered', L.memory ?? 0, ''], ['Mode', L.mode || 'warming', ''], ['Runners missed / good exits', `${L.missed ?? 0} / ${L.good ?? 0}`, '']].map(([k, v, t]) => <span key={k} className={t}><small>{k}</small><b>{v}</b></span>)}</div>
    <div className="fb-grid">
      <div className="cc-block"><h4>✅ Setups that pay her</h4>{!pb.best.length ? <p className="cc-empty">Needs 4+ closed trades per setup. She sizes these up (up to 1.5×).</p> : pb.best.map(r => <Row key={r.setup} r={r} />)}</div>
      <div className="cc-block"><h4>⛔ Setups that cost her</h4>{!pb.worst.length ? <p className="cc-empty">Nothing proven bad yet. Losers get sized down; 6+ trades at ≤20% wins and −8% avg are vetoed.</p> : pb.worst.map(r => <Row key={r.setup} r={r} />)}</div>
    </div>
    {L.vetoes?.length > 0 && <div className="cc-block"><h4>🧠 Trades she refused (setup memory)</h4>{L.vetoes.map((v, i) => <div key={i} className="fb-veto"><b>${v.symbol}</b><span>{v.why}</span></div>)}</div>}
    <div className="cc-block"><h4>Exit tuning (learned after every sell)</h4><div className="fb-params">{Object.entries(L.params || {}).map(([k, v]) => <span key={k}><small>{k === 'runnerTrail' ? 'Runner trail' : k === 'takeProfit1' ? 'First profit at' : k}</small><b>{k === 'takeProfit1' ? '+' : ''}{v}%</b><em>{v !== L.defaults?.[k] ? `default ${L.defaults?.[k]}%` : 'default'}</em></span>)}</div>
      <div className="fb-log">{(L.log || []).slice(0, 6).map((x, i) => <p key={i} className={x.missed ? 'miss' : ''}>{x.note}</p>)}</div></div>
  </div>;
}
