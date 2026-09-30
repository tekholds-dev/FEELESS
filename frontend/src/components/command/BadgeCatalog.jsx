import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { errorText } from '../../lib/api';

// Every badge currently out there: edit its look everywhere at once, and set its % of each pool in one row.
export function BadgeCatalog({ call }) {
  const [badges, setBadges] = useState([]);
  const [pools, setPools] = useState([]);
  const [edit, setEdit] = useState(null);
  const [shares, setShares] = useState({});   // `${poolId}|${key}` -> '12'
  const load = useCallback(() => Promise.all([call('/admin/badges'), call('/admin/badge-pools')]).then(([b, p]) => {
    const by = {};
    (b.rows || []).forEach(r => r.badges.forEach(x => { const e = by[x.id] || (by[x.id] = { ...x, holders: 0 }); e.holders += 1; }));
    const tiers = (p.pools || []).some(pl => pl.seasonId) ? ['Legend', 'Diamond', 'Gold', 'Silver', 'Bronze'].map(t => ({ id: t, key: `tier:${t}`, label: `${t} tier`, icon: { Legend: '👑', Diamond: '💎', Gold: '🥇', Silver: '🥈', Bronze: '🥉' }[t], tone: 'gold', why: 'Season rank', season: true })) : [];
    setBadges([...Object.values(by).sort((a, c) => c.holders - a.holders), ...(b.builtin || []), ...tiers]);
    setPools(p.pools || []);
    const s = {}; (p.pools || []).forEach(pl => { Object.entries(pl.weights || {}).forEach(([k, v]) => { s[`${pl.id}|${k}`] = String(v); }); Object.entries(pl.fixed || {}).forEach(([k, v]) => { s[`${pl.id}|${k}|sol`] = String(v); }); }); setShares(s);
  }).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  const saveEdit = async () => {
    try { await call(`/admin/badges/${edit.id}`, { method: 'PUT', body: JSON.stringify({ label: edit.label, icon: edit.icon, tone: edit.tone, why: edit.why }) }); toast.success('Badge updated for every holder.'); setEdit(null); load(); }
    catch (e) { toast.error(errorText(e)); }
  };
  const keyOf = b => b.key || `badge:${b.id}`;
  const saveShares = async b => {
    try {
      const key = keyOf(b);
      for (const pl of pools) {
        const v = Number(shares[`${pl.id}|${key}`]) || 0; const sol = Number(shares[`${pl.id}|${key}|sol`]) || 0;
        if ((Number(pl.weights?.[key]) || 0) === v && (Number(pl.fixed?.[key]) || 0) === sol) continue;
        await call('/admin/badge-pools', { method: 'POST', body: JSON.stringify({ id: pl.id, name: pl.name, wallet: pl.wallet, pct: pl.pct, seasonId: pl.seasonId || '', mode: 'pct', weights: { ...(pl.weights || {}), [key]: v }, fixed: { ...(pl.fixed || {}), [key]: sol } }) });
      }
      toast.success('Rewards saved.'); load();
    } catch (e) { toast.error(errorText(e)); }
  };
  if (!badges.length) return <p className="cc-empty">No badges are out yet. Award one in the Award tab.</p>;
  return <div className="bdg-catalog" data-testid="badge-catalog">
    {badges.map(b => <div key={b.id} className="bdg-card bc-row">
      {edit?.id === b.id ? <div className="bdg-form-row">
        <input aria-label="Icon" style={{ width: 60 }} maxLength={8} value={edit.icon} onChange={e => setEdit(x => ({ ...x, icon: e.target.value }))} />
        <input aria-label="Name" maxLength={32} value={edit.label} onChange={e => setEdit(x => ({ ...x, label: e.target.value }))} />
        <input aria-label="Why" maxLength={140} value={edit.why || ''} onChange={e => setEdit(x => ({ ...x, why: e.target.value }))} />
        <div className="bdg-seg">{['gold', 'mint', 'plain', 'bad'].map(t => <button key={t} type="button" className={edit.tone === t ? 'active' : ''} onClick={() => setEdit(x => ({ ...x, tone: t }))}>{t}</button>)}</div>
        <button type="button" className="btn-primary" disabled={(edit.label || '').length < 2} onClick={saveEdit}>Save</button><button type="button" className="btn-outline" onClick={() => setEdit(null)}>Cancel</button></div>
        : <div className="bc-head"><span className={`badge-pill tone-${b.tone}`}>{b.icon} {b.label}</span>{(b.builtin || b.season) && <em className="bc-auto">{b.season ? 'season tier' : 'earned automatically'}</em>}<small>{b.season ? 'Holders = wallets at this tier in the pool\'s season' : `${b.holders} holder${b.holders === 1 ? '' : 's'}${b.builtin ? ' seen in the last day' : ''} · ${b.why || ''}`}</small>{!b.builtin && !b.season && <button type="button" className="btn-outline" onClick={() => setEdit({ ...b })}>✎ Edit</button>}</div>}
      {pools.length > 0 ? <div className="bc-shares">{pools.filter(pl => !b.season || pl.seasonId).map(pl => <div key={pl.id} className="bc-pool"><span>{pl.name}</span>
        <label className="bdg-cell"><input inputMode="decimal" placeholder="0" aria-label={`${b.label} % of ${pl.name}`} value={shares[`${pl.id}|${keyOf(b)}`] ?? ''} onChange={e => setShares(s2 => ({ ...s2, [`${pl.id}|${keyOf(b)}`]: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>% of pot</span></label>
        <label className="bdg-cell"><input inputMode="decimal" placeholder="0" aria-label={`${b.label} SOL each from ${pl.name}`} value={shares[`${pl.id}|${keyOf(b)}|sol`] ?? ''} onChange={e => setShares(s2 => ({ ...s2, [`${pl.id}|${keyOf(b)}|sol`]: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>SOL each</span></label></div>)}
        <button type="button" className="btn-primary" onClick={() => saveShares(b)}>Save rewards</button></div> : <small className="cc-empty">Create a pool (Reserve pool tab) to give this badge a reward.</small>}
    </div>)}
  </div>;
}
