import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { apiUrl } from '../../lib/api';

// Command Center › ⚛️ Fuse › FUSE Vault designer. One vault = up to 3 yield pools (v2 constant-product / v3 concentrated)
// in one contract: SOL in → spread by auto-scaled weights, capped per pool, fees to the vault fee wallet (Trading & fees).
// Status stays DESIGN until the on-chain program is audited and deployed — nothing here moves funds.
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);
const sol = v => `${Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 3 })} SOL`;
const EMPTY = { name: '', emoji: '🏦', tagline: '', mgmtBps: 100, perfBps: 1000, pools: [] };

export function VaultDesigner({ call }) {
  const [d, setD] = useState(null); const [deposit, setDeposit] = useState(10);
  const [draft, setDraft] = useState(EMPTY); const [q, setQ] = useState(''); const [found, setFound] = useState([]);
  const load = () => call(`/admin/vaults?deposit=${Number(deposit) > 0 ? deposit : 10}`).then(setD).catch(e => toast.error(e.message));
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [deposit]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (q.trim().length < 2) { setFound([]); return undefined; }
    const t = setTimeout(() => fetch(apiUrl(`/api/reputation/vaults/pools?q=${encodeURIComponent(q.trim())}`)).then(r => r.json()).then(x => setFound(x.pools || [])).catch(() => {}), 300);
    return () => clearTimeout(t);
  }, [q]);
  const add = p => setDraft(x => (x.pools.some(l => l.pairAddress === p.pairAddress) || x.pools.length >= 3 ? x
    : { ...x, pools: [...x.pools, { pairAddress: p.pairAddress, chainId: 'solana', symbol: `${p.symbol}/${p.quote}`, kind: p.kind, venue: p.venue, weight: 1, capPct: 2, rangePct: p.kind === 'v3' ? 20 : null, meta: p }] }));
  const setPool = (i, patch) => setDraft(x => ({ ...x, pools: x.pools.map((p, j) => (j === i ? { ...p, ...patch } : p)) }));
  const save = async body => { try { await call('/admin/vaults', { method: 'POST', body: JSON.stringify(body) }); toast.success('Vault saved'); setDraft(EMPTY); load(); } catch (e) { toast.error(e.message); } };
  return <div className="cc-block vault-designer" data-testid="vault-designer">
    <div className="m-row"><h4>🏦 FUSE Vault designer</h4><span className="m-chip warn">DESIGN · not deployed</span>
      <span className="m-dim">3 pools · one contract · SOL in, spread + auto-scaled · fees to {d?.feeWallet ? `${d.feeWallet.slice(0, 4)}…${d.feeWallet.slice(-4)}` : 'the vault fee wallet (set it in Trading & fees)'}</span></div>
    <label className="m-field vd-dep"><span>Simulate a deposit of</span><input className="m-input" inputMode="decimal" value={deposit} onChange={e => setDeposit(e.target.value.replace(/[^0-9.]/g, ''))} /></label>
    {(d?.vaults || []).map(v => <div key={v.id} className="m-card vd-vault"><div className="m-row"><span className="fz-emoji">{v.emoji}</span><b>{v.name}</b><span className="m-chip">{v.status}</span>
      <span className="m-dim">{v.mgmtBps / 100}%/yr mgmt · {v.perfBps / 100}% performance</span>
      <button type="button" className="m-btn" onClick={() => setDraft({ id: v.id, name: v.name, emoji: v.emoji, tagline: v.tagline || '', mgmtBps: v.mgmtBps, perfBps: v.perfBps, pools: v.pools.map(p => ({ ...p, meta: p })) })}>Edit</button>
      <button type="button" className="m-btn danger" onClick={() => window.confirm(`Delete ${v.name}?`) && save({ id: v.id, delete: true })}>Delete</button></div>
      <table className="vd-table"><thead><tr><th>Pool</th><th>Type</th><th>Depth</th><th>Fee APR est.</th><th>Cap</th><th>Live weight</th><th>Gets</th></tr></thead><tbody>
        {v.pools.map(p => <tr key={p.pairAddress}><td><b>{p.symbol}</b> <small className="m-dim">{p.venue}</small></td><td><span className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`}>{p.kind}{p.kind === 'v3' ? ` ±${p.rangePct}%` : ''}</span></td>
          <td>{usd(p.liquidityUsd)}</td><td>{p.aprEst ?? '—'}%</td><td>{p.capPct}% of TVL</td><td>{Math.round((p.liveWeight || 0) * 100)}%</td><td>{sol(v.sim.allocation[p.pairAddress])}</td></tr>)}</tbody></table>
      <div className="m-row vd-sim"><div className="m-stat"><small>BUFFER (over caps)</small><b className="m-num sm">{sol(v.sim.bufferSol)}</b></div>
        <div className="m-stat"><small>CAPACITY</small><b className="m-num sm">{sol(v.sim.capacitySol)}</b></div><div className="m-stat"><small>BLENDED APR</small><b className="m-num sm">{v.sim.blendedAprPct}%</b></div>
        <div className="m-stat"><small>YIELD / YR</small><b className="m-num sm m-pos">{sol(v.sim.yearlyYieldSol)}</b></div><div className="m-stat"><small>TO FEE WALLET / YR</small><b className="m-num sm">{sol(v.sim.yearlyFeeSol)}</b></div></div></div>)}
    <div className="m-card fz-draft"><div className="m-row"><input className="m-input fz-emoji-in" value={draft.emoji} onChange={e => setDraft({ ...draft, emoji: e.target.value })} aria-label="Emoji" />
      <input className="m-input" placeholder="Vault name (e.g. FEE Yield)" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} aria-label="Vault name" />
      <label className="m-field"><span>Mgmt %/yr (≤{(d?.maxMgmtBps || 300) / 100})</span><input className="m-input" type="number" step="0.1" min="0" value={draft.mgmtBps / 100} onChange={e => setDraft({ ...draft, mgmtBps: Math.round(Number(e.target.value) * 100) })} /></label>
      <label className="m-field"><span>Performance % (≤{(d?.maxPerfBps || 3000) / 100})</span><input className="m-input" type="number" min="0" value={draft.perfBps / 100} onChange={e => setDraft({ ...draft, perfBps: Math.round(Number(e.target.value) * 100) })} /></label></div>
      {draft.pools.map((p, i) => <div key={p.pairAddress} className="m-row fz-draft-leg"><b>{p.symbol}</b><span className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`}>{p.kind}</span><small className="m-dim">{p.meta ? `${usd(p.meta.liquidityUsd)} · ${p.meta.aprEst}% APR est.` : ''}</small>
        <label className="m-field"><span>Base weight</span><input className="m-input" type="number" min="1" value={p.weight} onChange={e => setPool(i, { weight: Number(e.target.value) })} /></label>
        <label className="m-field"><span>Cap % of pool</span><input className="m-input" type="number" step="0.1" min="0.1" max="10" value={p.capPct} onChange={e => setPool(i, { capPct: Number(e.target.value) })} /></label>
        {p.kind === 'v3' && <label className="m-field"><span>Range ±%</span><input className="m-input" type="number" min="2" max="100" value={p.rangePct} onChange={e => setPool(i, { rangePct: Number(e.target.value) })} /></label>}
        <button type="button" className="m-btn danger" onClick={() => setDraft({ ...draft, pools: draft.pools.filter((_, j) => j !== i) })} aria-label="Remove pool">✕</button></div>)}
      {draft.pools.length < 3 && <input className="m-input" placeholder="Search Solana pools: SOL USDC, FEE, PAID…" value={q} onChange={e => setQ(e.target.value)} aria-label="Search pools" data-testid="vault-search" />}
      {found.length > 0 && draft.pools.length < 3 && <div className="fz-found">{found.map(p => <button type="button" key={p.pairAddress} className="qb-tile" onClick={() => add(p)}><span><b>{p.symbol}/{p.quote} <em className={`m-chip ${p.kind === 'v3' ? 'ok' : ''}`}>{p.kind}</em></b><small>{p.venue} · {usd(p.liquidityUsd)} depth · {usd(p.volume24h)} vol · {p.aprEst}% APR est.</small></span></button>)}</div>}
      <div className="m-row"><button type="button" className="m-btn primary" disabled={!draft.name || !draft.pools.length} onClick={() => save({ ...draft, pools: draft.pools.map(({ meta, ...p }) => p) })}>{draft.id ? 'Save vault' : 'Save vault design'}</button>
        {draft.id && <button type="button" className="m-btn" onClick={() => setDraft(EMPTY)}>Cancel</button>}<small className="m-dim">Live weights auto-scale with each pool's fee APR and depth (10–70% each); caps stop the vault becoming the market.</small></div></div>
  </div>;
}
