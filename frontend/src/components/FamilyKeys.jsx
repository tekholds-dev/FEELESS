import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { agentAuthQuery } from '../lib/chatSession';
import { ApiSlot } from './command/CatWorkbench';

// 🔑 ONE KEY VAULT (K01): every agent you own and its API keys, in one room of your family HQ. Each key stays sealed with its own agent's key: this page only ever sees a provider's name and the last 4 characters.
export function FamilyKeys() {
  const [cats, setCats] = useState(null); const [err, setErr] = useState(''); const [open, setOpen] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl(`/api/cats?${agentAuthQuery()}`)).then(r => (r.ok ? r.json() : Promise.reject(new Error('Could not read your agents.')))).then(j => { if (on) { setCats((j.cats || []).filter(c => !c.revoked)); } }).catch(e => { if (on) { setErr(e.message); setCats([]); } }); return () => { on = false; }; }, []);
  if (!cats) return <p className="fky-note">Reading your agents…</p>;
  if (!cats.length) return <p className="fky-note">{err || 'Sign in and launch an agent to keep its keys here.'}</p>;
  const saved = c => (c.apiDrawer || []).filter(r => r.saved).length; const total = cats.reduce((n, c) => n + saved(c), 0);
  return <section className="fky" data-testid="family-keys"><header><span><small>THE KEY VAULT</small><b className="m-num">{total} key{total === 1 ? '' : 's'} sealed</b></span><em>Only a provider's name and last 4 characters ever show here.</em></header>
    <ul>{cats.map((c, i) => <li key={c.id} style={{ '--i': i }} className={open === c.id ? 'is-open' : ''}><button type="button" aria-expanded={open === c.id} onClick={() => setOpen(open === c.id ? null : c.id)} data-tip={`Open ${c.name}'s keys`} data-testid={`fky-${c.id}`}><b>{c.name}</b><small className="m-num">{saved(c)} saved</small><i aria-hidden="true">{open === c.id ? '▴' : '▾'}</i></button>{open === c.id ? <div className="fky-in"><ApiSlot cat={c} /></div> : null}</li>)}</ul></section>;
}
