import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiUrl } from '../lib/api';
import { RepMark } from './RepMark';

// Live feed of coins launched through FEELESS: creator Rep, Shield, first-block snipers and, for
// FEELESS-rail coins, how close the curve is to graduating.
async function curveProgress(rows) {
  const need = rows.filter(r => r.rail === 'feeless' && r.config).slice(0, 8);
  if (!need.length) return {};
  const [{ relayConnection }, dbc, web3] = await Promise.all([import('../lib/launchRail'), import('@meteora-ag/dynamic-bonding-curve-sdk'), import('@solana/web3.js')]);
  const { connection } = await relayConnection();
  const client = new dbc.DynamicBondingCurveClient(connection, 'confirmed');
  const out = {};
  await Promise.all(need.map(async r => {
    try {
      const pool = dbc.deriveDbcPoolAddress(web3.NATIVE_MINT, new web3.PublicKey(r.mint), new web3.PublicKey(r.config));
      out[r.mint] = await client.state.getPoolQuoteTokenCurveProgress(pool);
    } catch { /* graduated or not indexed yet */ }
  }));
  return out;
}

export function LaunchRadar() {
  const [rows, setRows] = useState(null);
  const [prog, setProg] = useState({});
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl('/api/reputation/launch-radar?limit=20')).then(r => r.json()).then(d => {
      if (!alive) return;
      setRows(d.launches || []);
      curveProgress(d.launches || []).then(p => alive && setProg(p)).catch(() => {});
    }).catch(() => alive && setRows([]));
    load(); const t = setInterval(load, 45000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return <section className="launch-radar" data-testid="launch-radar">
    <header><h3>🚀 Launch radar</h3><small>Every coin launched through FEELESS, with the evidence.</small></header>
    {!rows ? <p className="lr-empty">Loading launches…</p> : !rows.length ? <p className="lr-empty">No FEELESS launches yet — the first one lands here live.</p>
      : <div className="lr-list">{rows.map(r => {
        const p = prog[r.mint];
        return <Link key={r.mint} to={`/terminal/chat?chain=solana&pair=${r.mint}&room=bulls`} className="lr-row">
          <b>${r.symbol || r.mint.slice(0, 4)}</b>
          <span className={`lr-rail ${r.rail}`}>{r.rail === 'pump' ? 'pump.fun' : 'FEELESS'}</span>
          <RepMark compact address={r.creator} />
          <span className={`lr-chip ${r.snipers == null ? '' : r.snipers === 0 ? 'good' : r.snipers > 5 ? 'bad' : 'warn'}`}>{r.snipers == null ? 'scanning…' : `${r.snipers} snipers`}</span>
          {r.shield && <span className={`lr-chip ${r.shield === 'active' ? 'good' : 'bad'}`}>{r.shield === 'active' ? '🛡 Shield' : '💔 Shield broken'}</span>}
          {p != null && <span className={`lr-grad ${p >= 0.8 ? 'hot' : ''}`} title="Progress to graduation"><i style={{ width: `${Math.min(100, p * 100)}%` }} />{p >= 0.8 ? '🔥 ' : ''}{Math.round(p * 100)}%</span>}
          <small>{ago(r.at)}</small>
        </Link>;
      })}</div>}
  </section>;
}
const ago = t => { const s = Date.now() / 1000 - (t || 0); return s < 3600 ? `${Math.max(1, Math.round(s / 60))}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
