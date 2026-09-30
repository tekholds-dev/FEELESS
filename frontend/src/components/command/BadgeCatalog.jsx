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
    setBadges(Object.values(by).sort((a, c) => c.holders - a.holders));
    setPools(p.pools || []);
    const s = {}; (p.pools || []).forEach(pl => Object.entries(pl.weights || {}).forEach(([k, v]) => { s[`${pl.id}|${k}`] = String(v); })); setShares(s);
  }).catch(e => toast.error(errorText(e))), [call]);
  useEffect(() => { load(); }, [load]);
  const saveEdit = async () => {
    try { await call(`/admin/badges/${edit.id}`, { method: 'PUT', body: JSON.stringify({ label: edit.label, icon: edit.icon, tone: edit.tone, why: edit.why }) }); toast.success('Badge updated for every holder.'); setEdit(null); load(); }
    catch (e) { toast.error(errorText(e)); }
  };
  const saveShares = async id => {
    try {
      for (const pl of pools) {
        const key = `badge:${id}`; const v = Number(shares[`${pl.id}|${key}`]) || 0;
        if ((Number(pl.weights?.[key]) || 0) === v) continue;
        const weights = { ...(pl.weights || {}), [key]: v };
        await call('/admin/badge-pools', { method: 'POST', body: JSON.stringify({ id: pl.id, name: pl.name, wallet: pl.wallet, pct: pl.pct, seasonId: pl.seasonId || '', mode: 'pct', weights }) });
      }
      toast.success('Shares saved.'); load();
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
        : <div className="bc-head"><span className={`badge-pill tone-${b.tone}`}>{b.icon} {b.label}</span><small>{b.holders} holder{b.holders === 1 ? '' : 's'} · {b.why}</small><button type="button" className="btn-outline" onClick={() => setEdit({ ...b })}>✎ Edit</button></div>}
      {pools.length > 0 ? <div className="bc-shares">{pools.map(pl => <label key={pl.id} className="bdg-cell"><span>{pl.name}</span><input inputMode="decimal" placeholder="0" aria-label={`${b.label} share of ${pl.name}`} value={shares[`${pl.id}|badge:${b.id}`] ?? ''} onChange={e => setShares(s => ({ ...s, [`${pl.id}|badge:${b.id}`]: e.target.value.replace(/[^0-9.]/g, '') }))} /><span>%</span></label>)}
        <button type="button" className="btn-primary" onClick={() => saveShares(b.id)}>Save shares</button></div> : <small className="cc-empty">Create a pool (Reserve pool tab) to give this badge a share.</small>}
    </div>)}
  </div>;
}
