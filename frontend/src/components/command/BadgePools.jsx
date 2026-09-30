import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { errorText } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { useSolUsd, money } from './FeeInputs';

// Badge pools: a pool is a wallet you control + how much of it goes to badge holders. The matrix sets, for every
// badge, the exact % of each pool's pot it earns (split equally between that badge's holders). Unassigned % stays put.
// The pool wallet signs its own payout; the server records only SOL that moved on-chain.
const EMPTY = { id: '', name: '', wallet: '', pct: '', seasonId: '', weights: {}, mode: 'pct' };
const TIER_ROWS = ['Legend', 'Diamond', 'Gold', 'Silver', 'Bronze'];
const TIER_ICON = { Legend: '👑', Diamond: '💎', Gold: '🥇', Silver: '🥈', Bronze: '🥉' };
const num = v => Number(v) || 0;

export function BadgePools({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const px = useSolUsd();
  const [meta, setMeta] = useState({ pools: [], badges: [], tiers: [], seasons: [] });
  const [form, setForm] = useState(null);
  const [grid, setGrid] = useState({});            // poolId -> { key: '12' }
  const [plans, setPlans] = useState({});
  const [busy, setBusy] = useState('');
  const load = useCallback(() => call('/admin/badge-pools').then(d => {
    setMeta(d);
    setGrid(Object.fromEntries((d.pools || []).map(p => [p.id, Object.fromEntries(Object.entries(p.weights || {}).map(([k, v]) => [k, String(v)]))])));
  }).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  const loadPlans = useCallback(() => meta.pools.forEach(p => call(`/admin/badge-pools/${p.id}/plan`).then(pl => setPlans(x => ({ ...x, [p.id]: pl }))).catch(() => {})), [meta.pools, call]);
  useEffect(() => { loadPlans(); }, [loadPlans]);
  const usd = v => (px && v ? money(v * px) : '');
  const rows = useMemo(() => [
    ...meta.badges.map(b => ({ key: `badge:${b.id}`, label: `${b.icon || '🎖'} ${b.label}`, sub: `${b.count} holder${b.count === 1 ? '' : 's'}` })),
    ...(meta.pools.some(p => p.seasonId) ? TIER_ROWS.map(t => ({ key: `tier:${t}`, label: `${TIER_ICON[t]} ${t} tier`, sub: 'season rank' })) : []),
  ], [meta.badges, meta.pools]);
  const total = id => Object.values(grid[id] || {}).reduce((a, v) => a + num(v), 0);
  const dirty = id => { const p = meta.pools.find(x => x.id === id); return JSON.stringify(Object.fromEntries(Object.entries(grid[id] || {}).filter(([, v]) => num(v)).map(([k, v]) => [k, num(v)]))) !== JSON.stringify(Object.fromEntries(Object.entries(p?.weights || {}).map(([k, v]) => [k, num(v)]))); };
  const savePool = async (p, weights) => {
    await call('/admin/badge-pools', { method: 'POST', body: JSON.stringify({ id: p.id, name: p.name, wallet: p.wallet, pct: num(p.pct), seasonId: p.seasonId || '', mode: 'pct', weights }) });
  };
  const saveForm = async () => {
    try { setBusy('Saving…'); await savePool(form, Object.fromEntries(Object.entries(grid[form.id] || form.weights || {}).map(([k, v]) => [k, num(v)]))); toast.success('Pool saved.'); setForm(null); load(); }
    catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const saveMatrix = async () => {
    try {
      setBusy('Saving shares…');
      for (const p of meta.pools.filter(x => dirty(x.id))) await savePool(p, Object.fromEntries(Object.entries(grid[p.id] || {}).map(([k, v]) => [k, num(v)])));
      toast.success('Badge shares saved.'); load();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const remove = async id => { if (!window.confirm('Delete this pool? Past payouts stay on-chain.')) return; try { await call(`/admin/badge-pools/${id}`, { method: 'DELETE' }); load(); } catch (e) { toast.error(errorText(e)); } };
  const pay = async p => {
    const plan = plans[p.id];
    try {
      if (wallet?.chain !== 'solana' || wallet?.address !== p.wallet) { toast.message?.(`Connect ${shortAddress(p.wallet)} (the pool wallet) to pay.`); await connect?.('solana'); return; }
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, recipients: plan.rows.map(r => ({ address: r.address, amount: r.sol })), kind: 'badge-pool', onStatus: setBusy });
      const r = await call(`/admin/badge-pools/${p.id}/paid`, { method: 'POST', body: JSON.stringify({ sigs }) });
      toast.success(`Paid ${r.paidSol} SOL to ${r.wallets} wallets.`); load();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const anyDirty = meta.pools.some(p => dirty(p.id));
  return <div className="bdg-pools" data-testid="badge-pools">
    <div className="bdg-pools-head"><div><small>BADGE POOLS</small><p>Pick a wallet, choose how much of it is up for grabs, then give each badge its own % of that pot.</p></div>
      <button type="button" className="btn-primary" onClick={() => setForm({ ...EMPTY })}>+ New pool</button></div>
    <details className="bdg-explain"><summary>How pool payouts work</summary>
      <ol>
        <li><b>Pool</b> = any Solana wallet you control (treasury, sponsor, buy-back) + the % of its SOL that badge holders share. 0.01 SOL always stays for fees.</li>
        <li><b>Badge share</b> = the % of that pot one badge earns. Its slice is split equally between everyone holding it. A wallet with two badges stacks both slices.</li>
        <li>Shares in a pool can't pass 100%. Anything unassigned, or assigned to a badge nobody holds yet, stays in the wallet.</li>
        <li><b>Paying</b>: connect the pool wallet, press Pay. It's simulated first, you approve once, and the server records only what landed on-chain (never the same tx twice, 1h cooldown).</li>
        <li>Blocklisted and FEELESS wallets never receive a share.</li>
      </ol></details>
    {form && <div className="bdg-card bdg-pool-form">
      <div className="bdg-form-row"><input placeholder="Pool name (e.g. OG holders)" maxLength={40} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        <input placeholder="Pool wallet (any Solana address you control)" value={form.wallet} onChange={e => setForm(f => ({ ...f, wallet: e.target.value.trim() }))} />
        <label className="bdg-pct"><input inputMode="decimal" placeholder="0" value={form.pct} onChange={e => setForm(f => ({ ...f, pct: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>% of wallet is the pot</span></label>
        <select value={form.seasonId} onChange={e => setForm(f => ({ ...f, seasonId: e.target.value }))} aria-label="Season for tier rows"><option value="">No season tiers</option>{meta.seasons.map(s => <option key={s.id} value={s.id}>Tiers from {s.name}</option>)}</select></div>
      <div className="bdg-form-row"><button type="button" className="btn-primary" disabled={!!busy || form.name.length < 2 || !form.wallet} onClick={saveForm}>{busy || (form.id ? 'Save pool' : 'Create pool')}</button><button type="button" className="btn-outline" onClick={() => setForm(null)}>Cancel</button><small className="cc-empty">Then set each badge's % in the matrix below.</small></div>
    </div>}
    {!meta.pools.length && !form && <p className="cc-empty">No pools yet. Create one, then give badges their % in the matrix.</p>}
    {meta.pools.length > 0 && <div className="bdg-matrix-wrap"><table className="bdg-matrix" data-testid="badge-matrix">
      <thead><tr><th>Badge</th>{meta.pools.map(p => { const pl = plans[p.id]; return <th key={p.id}><b>{p.name}</b><small>{p.pct}% of {shortAddress(p.wallet)}</small><em>{pl ? `pot ${pl.potSol} SOL${usd(pl.potSol) ? ` · ${usd(pl.potSol)}` : ''}` : '…'}</em></th>; })}</tr></thead>
      <tbody>{!rows.length ? <tr><td colSpan={meta.pools.length + 1} className="cc-empty">Award a badge first (Award tab); it shows up here.</td></tr> : rows.map(r => <tr key={r.key}><td><b>{r.label}</b><small>{r.sub}</small></td>
        {meta.pools.map(p => <td key={p.id}><label className="bdg-cell"><input inputMode="decimal" aria-label={`${r.label} share of ${p.name}`} placeholder="0" disabled={r.key.startsWith('tier:') && !p.seasonId}
          value={grid[p.id]?.[r.key] ?? ''} onChange={e => setGrid(g => ({ ...g, [p.id]: { ...(g[p.id] || {}), [r.key]: e.target.value.replace(/[^0-9.]/g, '') } }))} /><span>%</span></label></td>)}</tr>)}</tbody>
      <tfoot><tr><td>Assigned</td>{meta.pools.map(p => <td key={p.id} className={total(p.id) > 100 ? 'bad' : total(p.id) === 100 ? 'ok' : ''}>{Math.round(total(p.id) * 100) / 100}%</td>)}</tr>
        <tr><td />{meta.pools.map(p => { const pl = plans[p.id]; const mine = wallet?.address === p.wallet; return <td key={p.id} className="bdg-actions-cell">
          <button type="button" className="btn-outline" onClick={() => setForm({ ...EMPTY, ...p, pct: String(p.pct) })}>Edit</button>
          <button type="button" className="btn-outline" onClick={() => remove(p.id)}>✕</button>
          <button type="button" className="btn-primary" disabled={!!busy || dirty(p.id) || !pl?.rows.length || pl?.cooldownLeft > 0} title={dirty(p.id) ? 'Save shares first' : pl?.cooldownLeft ? 'Paid within the last hour' : ''} onClick={() => pay(p)}>{mine ? `Pay ${pl?.paidSol ?? ''} SOL` : 'Connect to pay'}</button>
          {pl?.lastPayout && <small>last {pl.lastPayout.totalSol} SOL · {new Date(pl.lastPayout.at * 1000).toLocaleDateString()}</small>}</td>; })}</tr></tfoot>
    </table></div>}
    {anyDirty && <div className="bdg-payrow"><span>Unsaved badge shares</span><button type="button" className="btn-primary" disabled={!!busy || meta.pools.some(p => total(p.id) > 100)} onClick={saveMatrix}>{busy || 'Save shares'}</button></div>}
  </div>;
}
