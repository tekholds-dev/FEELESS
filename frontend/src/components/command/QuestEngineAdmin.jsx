import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { BadgeArt } from '../BadgeArt';
import { CHAT_THEMES } from '../ChatFx';
import { perkText } from '../QuestBoard';
import { AuraPicker } from '../cards/MetaCard';
import { QuestBadgeCard } from '../QuestBadgeCard';

// HQ › Badges › Quest engine: every badge editable (name, tier, on/off, tasks + targets), live holder
// counts, and grant / revoke for any wallet. Saves go through the signed admin session; bad task lists are refused.
export function QuestEngineAdmin({ call }) {
  const [d, setD] = useState(null);
  const [edit, setEdit] = useState(null);
  const [set, setSet] = useState('feeless');
  const [grant, setGrant] = useState({ address: '', badge: '', action: 'grant' });
  const load = () => call('/admin/quests').then(setD).catch(e => toast.error(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return <div className="cc-block"><span className="loader" /> Loading quest engine…</div>;
  const save = async (b, patch) => { try { const r = await call('/admin/quests', { method: 'POST', body: JSON.stringify({ badges: { [b.id]: patch } }) }); setD(x => ({ ...x, badges: r.badges })); setEdit(null); toast.success('Saved'); } catch (e) { toast.error(e.message); } };
  const doGrant = async () => { try { await call('/admin/quests/grant', { method: 'POST', body: JSON.stringify(grant) }); toast.success(`${grant.action} ✓`); } catch (e) { toast.error(e.message); } };
  const st = d.stats || {};
  const season = d.season || {};
  const seasonCall = async body => { try { const r = await call('/admin/quests/season', { method: 'POST', body: JSON.stringify(body) }); setD(x => ({ ...x, season: r.season })); toast.success(r.awarded?.length ? `Trophies sent to ${r.awarded.length} wallet(s)` : 'Season saved'); } catch (e) { toast.error(e.message); } };
  const perkOf = (b, kind) => (b.perks || []).find(p => p.kind === kind);
  return <div className="cc-block qe" data-testid="quest-engine">
    <div className="m-row"><h4>Quest engine</h4><span className="m-chip ok">{d.badges.length} badges</span><span className="m-chip">{st.wallets || 0} active wallets</span>
      <span className="m-dim">Daily: {d.daily.map(q => q[1]).join(' · ')} · Weekly: {d.weekly.map(q => q[1]).join(' · ')}</span></div>
    <div className="m-row qe-season" data-testid="quest-season-admin"><span className="m-label">SEASON</span>
      <input className="m-input" defaultValue={season.name} onBlur={e => e.target.value !== season.name && seasonCall({ name: e.target.value })} aria-label="Season name" />
      <span className={`m-chip ${season.paused ? 'warn' : 'ok'}`}>{season.paused ? '⏸ paused (pre-launch)' : `live since ${season.start ? new Date(season.start * 1000).toLocaleDateString() : '—'}`}</span>
      <button type="button" className="m-btn" onClick={() => seasonCall({ paused: !season.paused })}>{season.paused ? '▶ Start season (launch day)' : '⏸ Pause season'}</button>
      <button type="button" className="m-btn" disabled={season.paused} onClick={() => seasonCall({ awardWeek: true })} title="Gives this week's top 3 a trophy (once per week)">🏆 Award week's top 3</button></div>
    <div className="m-seg" role="tablist">{[['feeless', 'FEELESS'], ['frsv', 'FEE RESERVE']].map(([id, l]) => <button key={id} type="button" className={set === id ? 'active' : ''} onClick={() => setSet(id)}>{l}</button>)}</div>
    <div className="qe-list">{d.badges.filter(b => b.set === set).map(b => <div key={b.id} className={`qe-row ${b.enabled === false ? 'is-off' : ''}`}>
      <BadgeArt art={b.art} name={b.name} size="sm" /><div><b>{b.name}</b> <span className={`m-chip tier-${b.tier}`}>{b.tier}</span> <small className="m-dim">{st.holders?.[b.id] || 0} hold · {st.pct?.[b.id] || 0}%</small>
        <div className="m-dim">{b.tasks.map(t => t.label).join(' · ')}</div>{b.perks?.length > 0 && <div className="m-dim">Perks: {b.perks.map(perkText).join(' · ')}</div>}</div>
      <div className="m-row"><button type="button" className="m-btn" onClick={() => setEdit({ ...b, tasks: b.tasks.map(t => ({ metric: t.metric, target: t.target, label: t.label })) })}>Edit</button>
        <button type="button" className="m-btn" onClick={() => save(b, { enabled: b.enabled === false })}>{b.enabled === false ? 'Turn on' : 'Turn off'}</button></div></div>)}</div>
    {edit && <div className="m-card qe-edit" data-testid="quest-edit"><div className="m-row"><input className="m-input" value={edit.name} onChange={e => setEdit({ ...edit, name: e.target.value })} aria-label="Badge name" />
      <select className="m-input" value={edit.tier} onChange={e => setEdit({ ...edit, tier: e.target.value })} aria-label="Tier">{d.tiers.map(t => <option key={t}>{t}</option>)}</select></div>
      <div className="m-row"><span className="m-label">PERKS</span>
        <label className="m-field"><span>Fee discount %</span><input className="m-input" type="number" min="0" max="50" value={perkOf(edit, 'fee_discount')?.pct || 0} onChange={e => setEdit({ ...edit, perks: [...(edit.perks || []).filter(p => p.kind !== 'fee_discount'), ...(Number(e.target.value) > 0 ? [{ kind: 'fee_discount', pct: Math.min(50, Number(e.target.value)) }] : [])] })} /></label>
        <label className="m-field"><span>Chat background</span><select className="m-input" value={perkOf(edit, 'chat_bg')?.id || ''} onChange={e => setEdit({ ...edit, perks: [...(edit.perks || []).filter(p => p.kind !== 'chat_bg'), ...(e.target.value ? [{ kind: 'chat_bg', id: e.target.value }] : [])] })}><option value="">none</option>{CHAT_THEMES.filter(([, , usd]) => usd > 0).map(([id, l]) => <option key={id} value={id}>{l}</option>)}</select></label></div>
      <div className="m-field qe-aura"><span>Card aura · live effect outside the card</span><div className="qe-aura-row"><QuestBadgeCard b={{ ...edit, set: edit.set || (edit.id.startsWith('frsv') ? 'frsv' : 'feeless'), earned: true, tasks: [], perks: [] }} size="sm" />
        <AuraPicker value={edit.aura} onChange={v => setEdit({ ...edit, aura: v })} /></div></div>
      {edit.tasks.map((t, i) => <div key={i} className="m-row"><select className="m-input" value={t.metric} onChange={e => setEdit({ ...edit, tasks: edit.tasks.map((x, j) => (j === i ? { ...x, metric: e.target.value } : x)) })} aria-label="Metric">{Object.entries(d.metrics).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        <input className="m-input" type="number" min="1" value={t.target} onChange={e => setEdit({ ...edit, tasks: edit.tasks.map((x, j) => (j === i ? { ...x, target: Number(e.target.value) } : x)) })} aria-label="Target" />
        <input className="m-input" value={t.label} onChange={e => setEdit({ ...edit, tasks: edit.tasks.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)) })} aria-label="Task label" />
        <button type="button" className="m-btn danger" onClick={() => setEdit({ ...edit, tasks: edit.tasks.filter((_, j) => j !== i) })} aria-label="Remove task">✕</button></div>)}
      <div className="m-row"><button type="button" className="m-btn" onClick={() => setEdit({ ...edit, tasks: [...edit.tasks, { metric: 'trades', target: 1, label: '1 trade' }] })}>+ Task</button>
        <button type="button" className="m-btn primary" onClick={() => save(edit, { name: edit.name, tier: edit.tier, tasks: edit.tasks, perks: edit.perks || [], aura: edit.aura || '' })}>Save badge</button>
        <button type="button" className="m-btn" onClick={() => save(edit, { reset: true })}>Reset to default</button><button type="button" className="m-btn" onClick={() => setEdit(null)}>Cancel</button></div></div>}
    <div className="m-row qe-grant"><input className="m-input" placeholder="Wallet address" value={grant.address} onChange={e => setGrant({ ...grant, address: e.target.value.trim() })} aria-label="Wallet" />
      <select className="m-input" value={grant.badge} onChange={e => setGrant({ ...grant, badge: e.target.value })} aria-label="Badge"><option value="">Badge…</option>{d.badges.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
      <div className="m-seg">{['grant', 'revoke', 'clear'].map(a => <button key={a} type="button" className={grant.action === a ? 'active' : ''} onClick={() => setGrant({ ...grant, action: a })}>{a}</button>)}</div>
      <button type="button" className="m-btn primary" disabled={!grant.address || !grant.badge} onClick={doGrant}>Apply</button></div>
  </div>;
}
