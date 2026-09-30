import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { useWallet } from '../../hooks/useWallet';
import { errorText } from '../../lib/api';
import { shortAddress } from '../../lib/dexscreener';
import { useSolUsd, money } from './FeeInputs';

// Badge pools: any badge (season tier or custom award) earns a weighted cut of any wallet the owner picks.
// The pool wallet signs its own payout; the server records only what moved on-chain.
const EMPTY = { id: '', name: '', wallet: '', pct: '', seasonId: '', weights: {} };

export function BadgePools({ call }) {
  const { wallet, provider, connect } = useWallet() || {};
  const px = useSolUsd();
  const [meta, setMeta] = useState({ pools: [], badges: [], tiers: [], seasons: [] });
  const [form, setForm] = useState(null);
  const [plans, setPlans] = useState({});
  const [busy, setBusy] = useState('');
  const load = useCallback(() => call('/admin/badge-pools').then(setMeta).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { meta.pools.forEach(p => call(`/admin/badge-pools/${p.id}/plan`).then(pl => setPlans(x => ({ ...x, [p.id]: pl }))).catch(() => {})); }, [meta.pools, call]);
  const usd = v => (px && v ? ` · ${money(v * px)}` : '');
  const setW = (k, v) => setForm(f => ({ ...f, weights: { ...f.weights, [k]: v.replace(/[^0-9.]/g, '') } }));
  const save = async () => {
    try {
      setBusy('Saving…');
      await call('/admin/badge-pools', { method: 'POST', body: JSON.stringify({ ...form, pct: Number(form.pct) || 0, weights: Object.fromEntries(Object.entries(form.weights).map(([k, v]) => [k, Number(v) || 0])) }) });
      toast.success('Pool saved.'); setForm(null); load();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  const remove = async id => { try { await call(`/admin/badge-pools/${id}`, { method: 'DELETE' }); load(); } catch (e) { toast.error(errorText(e)); } };
  const pay = async p => {
    const plan = plans[p.id];
    try {
      if (wallet?.chain !== 'solana' || wallet?.address !== p.wallet) { toast.message?.(`Connect ${shortAddress(p.wallet)} to pay this pool.`); await connect?.('solana'); return; }
      const { batchSend } = await import('../../lib/batchSend');
      const sigs = await batchSend({ provider, owner: wallet.address, recipients: plan.rows.map(r => ({ address: r.address, amount: r.sol })), kind: 'badge-pool', onStatus: setBusy });
      const r = await call(`/admin/badge-pools/${p.id}/paid`, { method: 'POST', body: JSON.stringify({ sigs }) });
      toast.success(`Paid ${r.paidSol} SOL to ${r.wallets} wallets.`); load();
    } catch (e) { toast.error(errorText(e)); } finally { setBusy(''); }
  };
  return <div className="bdg-pools" data-testid="badge-pools">
    <div className="bdg-pools-head"><div><small>BADGE POOLS</small><p>Any badge earns a cut of any wallet you choose — treasury, a sponsor, a buy-back wallet.</p></div>
      <button type="button" className="btn-primary" onClick={() => setForm({ ...EMPTY })}>+ New pool</button></div>
    {form && <div className="bdg-card bdg-pool-form">
      <div className="bdg-form-row"><input placeholder="Pool name (e.g. OG holders)" maxLength={40} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        <input placeholder="Pool wallet (any Solana address you control)" value={form.wallet} onChange={e => setForm(f => ({ ...f, wallet: e.target.value.trim() }))} />
        <label className="bdg-pct"><input inputMode="decimal" placeholder="0" value={form.pct} onChange={e => setForm(f => ({ ...f, pct: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>% of wallet</span></label></div>
      <small>SEASON TIERS EARN</small>
      <div className="bdg-weights-edit"><select value={form.seasonId} onChange={e => setForm(f => ({ ...f, seasonId: e.target.value }))}><option value="">No season</option>{meta.seasons.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
        {form.seasonId && meta.tiers.filter(t => t !== 'Recruit').map(t => <label key={t}><span>{t}</span><input inputMode="decimal" placeholder="0" value={form.weights[`tier:${t}`] ?? ''} onChange={e => setW(`tier:${t}`, e.target.value)} />×</label>)}</div>
      <small>CUSTOM BADGES EARN</small>
      <div className="bdg-weights-edit">{!meta.badges.length ? <span className="cc-empty">Award a badge first.</span> : meta.badges.map(b => <label key={b.id}><span>{b.icon} {b.label} <em>{b.count}</em></span><input inputMode="decimal" placeholder="0" value={form.weights[`badge:${b.id}`] ?? ''} onChange={e => setW(`badge:${b.id}`, e.target.value)} />×</label>)}</div>
      <div className="bdg-form-row"><button type="button" className="btn-primary" disabled={!!busy || form.name.length < 2 || !form.wallet} onClick={save}>{busy || 'Save pool'}</button><button type="button" className="btn-outline" onClick={() => setForm(null)}>Cancel</button></div>
    </div>}
    {!meta.pools.length && !form && <p className="cc-empty">No badge pools yet. Season reserve above covers tiers; pools add any badge + any wallet.</p>}
    {meta.pools.map(p => { const pl = plans[p.id]; const mine = wallet?.address === p.wallet; return <div key={p.id} className="bdg-card bdg-pool-item">
      <div className="bdg-pool-top"><b>{p.name}</b><code>{shortAddress(p.wallet)}</code><span className="bdg-pill">{p.pct}%</span>
        <span className="bdg-earns">{Object.entries(p.weights || {}).map(([k, w]) => <i key={k}>{k.split(':')[1]} {w}×</i>)}</span></div>
      <div className="bdg-pool-top"><span>Pot <b className="bdg-gold">{pl ? pl.potSol : '…'} SOL</b>{pl && usd(pl.potSol)}</span><span>{pl ? `${pl.rows.length} wallets` : ''}</span>
        {pl?.lastPayout && <span>last paid {new Date(pl.lastPayout.at * 1000).toLocaleDateString()} · {pl.lastPayout.totalSol} SOL</span>}
        <span className="bdg-actions"><button type="button" className="btn-outline" onClick={() => setForm({ ...EMPTY, ...p, pct: String(p.pct) })}>Edit</button>
          <button type="button" className="btn-outline" onClick={() => remove(p.id)}>Delete</button>
          <button type="button" className="btn-primary" disabled={!!busy || !pl?.rows.length || pl?.cooldownLeft > 0} title={pl?.cooldownLeft ? 'Paid within the last hour' : ''} onClick={() => pay(p)}>{mine ? `Pay ${pl?.paidSol ?? ''} SOL` : 'Connect pool wallet'}</button></span></div>
    </div>; })}
  </div>;
}
