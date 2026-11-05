import React, { useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { useWallet } from '../hooks/useWallet';
import { getChatSession } from '../lib/chatSession';
import { useAdmin } from '../lib/adminCall';
import '../styles/alliances.css';

// 🤝 ALLIANCES (C12): everything about alliances and unions lives here in Support. Start one from a reply in chat or right here; at most 10 members; after the days the owner set, its founder can found a Union.
const daysLeft = at => Math.max(0, Math.ceil((at - Date.now() / 1000) / 86400));
export function AllianceBoard({ start = '' }) {
  const { wallet, signMessage } = useWallet() || {}; const address = wallet?.address;
  const { isAdmin, call } = useAdmin(); const [days, setDaysText] = useState('');
  const [d, setD] = useState(null); const [name, setName] = useState(start); const [uni, setUni] = useState(''); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const load = useCallback(() => fetch(apiUrl(`/api/reputation/alliances${address ? `?wallet=${encodeURIComponent(address)}` : ''}`)).then(r => (r.ok ? r.json() : null)).then(j => j && setD(j)).catch(() => setErr('Could not read alliances.')), [address]);
  useEffect(() => { load(); }, [load]);
  const act = async (op, extra) => { if (!address) { setErr('Connect a wallet first.'); return; } setBusy(op); setErr(''); try { const session = await getChatSession(address, signMessage); const r = await fetch(apiUrl('/api/reputation/alliances'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ op, wallet: address, session, ...extra }) }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); setD(j); setName(''); setUni(''); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  if (!d) return <p className="aly-note">{err || 'Reading alliances…'}</p>;
  const me = d.rows.find(a => a.mine);
  const setDays = async e => { e.preventDefault(); setBusy('days'); setErr(''); try { setD(await call('/admin/alliance-days', { method: 'POST', body: JSON.stringify({ days: Number(days) }) })); } catch (er) { setErr(er.message); } finally { setBusy(''); } };
  return <section className="aly" data-testid="alliance-board"><header><span><small>ALLIANCES</small><b className="m-num">{d.rows.length}</b></span><em>Up to 10 members. After {d.days} days together, its founder can found a Union.</em></header>
    {me ? <article className="aly-me" data-testid="aly-mine"><div><small>{me.union ? 'YOUR UNION' : 'YOUR ALLIANCE'}</small><b>{me.union?.name || me.name}</b></div><span className="aly-meter" data-tip={`${me.n} of ${me.max} members`}><i style={{ transform: `scaleX(${me.n / me.max})` }} /></span><small className="m-num">{me.n}/{me.max} · {me.members.join(' · ')}</small>
      {me.founder && !me.union ? (me.ready ? <form onSubmit={e => { e.preventDefault(); act('union', { name: uni }); }}><input className="m-input" value={uni} onChange={e => setUni(e.target.value)} placeholder="Name your Union" aria-label="Union name" data-testid="aly-union-name" /><button type="submit" className="m-btn m-go" disabled={!!busy || uni.trim().length < 3} data-tip="Founds a FEELESS Union" data-testid="aly-union">Found a Union</button></form> : <small data-testid="aly-wait">A Union opens in {daysLeft(me.unionAt)} days.</small>) : null}
      <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('leave')} data-tip="Leave this alliance" data-testid="aly-leave">Leave</button></article>
      : <form className="aly-new" onSubmit={e => { e.preventDefault(); act('create', { name }); }}><input className="m-input" value={name} onChange={e => setName(e.target.value)} placeholder="Name your alliance" aria-label="Alliance name" data-testid="aly-name" /><button type="submit" className="m-btn m-go" disabled={!!busy || name.trim().length < 3} data-tip="Starts an alliance with you as founder" data-testid="aly-create">{busy === 'create' ? 'Starting…' : 'Start an alliance'}</button></form>}
    {isAdmin ? <form className="aly-new" onSubmit={setDays} data-testid="aly-days"><input className="m-input" type="number" min="0" max="3650" value={days} onChange={e => setDaysText(e.target.value)} placeholder={`Days before a Union (now ${d.days})`} aria-label="Days before a Union" /><button type="submit" className="m-btn" disabled={!!busy || days === ''} data-tip="Owner only: how long an alliance waits before it can found a Union">Set days</button></form> : null}
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    {d.rows.length ? <ul className="aly-list">{d.rows.map((a, i) => <li key={a.id} style={{ '--i': i }}><span><b>{a.union?.name || a.name}</b><small>{a.union ? 'Union' : 'Alliance'} · since {new Date(a.at * 1000).toLocaleDateString()}</small></span><small className="m-num">{a.n}/{a.max}</small>{!me && a.n < a.max ? <button type="button" className="m-btn" disabled={!!busy} onClick={() => act('join', { id: a.id })} data-tip={`Join ${a.name}`} data-testid={`aly-join-${a.id}`}>Join</button> : null}</li>)}</ul> : <p className="aly-note">No alliance yet. Be the first.</p>}</section>;
}
