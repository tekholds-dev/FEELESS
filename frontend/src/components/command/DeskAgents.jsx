import React, { useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';
import { AgentDesktop } from './CatWorkbench';
import '../../styles/collectiveSetup.css';

// 🎩 OSSY AND G4 ON THEIR OWN DESKTOPS (owner 2026-11-05: "have these guys do all of what fee agents do"). Each is a real agent with the same desktop and proof loop as any other, on paper: no wallet is ever attached here, so a filed PoW cannot buy with real money. Assigning one to a user's agent comes later.
export const DESK_AGENTS = [['OSSY', 'ossy-desk', 'You are OSSY. You read a coin the way a careful trader does: pool, holders, age, who bought, then a call you can defend. File proofs with the evidence behind them.'], ['G4', 'g4-desk', 'You are G4. You challenge every call: what would make this wrong, who is exiting, what the chart hides. File proofs that survive your own doubts.']];
const call = async (path, opts) => { const r = await fetch(apiUrl(path), { headers: { 'Content-Type': 'application/json' }, ...opts }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`); return j; };
export function DeskAgents() {
  const [cats, setCats] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState(''); const [said, setSaid] = useState(''); const [open, setOpen] = useState(null);
  const load = useCallback(() => call(`/api/cats?${agentAuthQuery()}`).then(j => setCats(j.cats || [])).catch(e => { setErr(e.message); setCats([]); }), []);
  useEffect(() => { load(); }, [load]);
  const brains = (cats || []).map(c => c.brainsCfg?.brains).find(b => b?.length);
  const make = async ([name, handle, prompt]) => { setBusy(name); setErr(''); setSaid(''); try { const a = agentAuth(); await call('/api/cats', { method: 'POST', body: JSON.stringify({ ...a, name, handle, strategy: 'momentum', walletMode: 'paper', brains, brainMode: 'turns', billing: 'payg', brainKind: 'trading', prompt, job: 'trading' }) }); await load(); setSaid(`${name} has its desktop.`); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  const file = async c => { setBusy(c.name); setErr(''); setSaid(''); try { const body = text => ({ method: 'POST', body: JSON.stringify({ ...agentAuth(), op: 'ask', text }) }); await call(`/api/cats/${c.id}/work`, body('file a pow')); await call(`/api/cats/${c.id}/work`, body('go')); setSaid(`${c.name} started a PoW, on paper. Watch it on its desktop.`); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  if (!cats) return <p className="fch-nil">Reading the desk…</p>;
  return <section className="dag" data-testid="desk-agents"><header><b>THE DESK'S AGENTS</b><small>Paper only. They have no wallet, so nothing they file can buy with real money.</small></header>
    <ul>{DESK_AGENTS.map(row => { const [name] = row; const c = cats.find(x => x.name === name && !x.revoked); const proofs = c ? (c.powFolders?.length || 0) + (c.popFolders?.length || 0) + (c.pobFolders?.length || 0) : 0; const credit = Number(c?.brainsCfg?.credit) || 0;
      return <li key={name} data-testid={`desk-agent-${name}`}><span className="dag-n"><Ic3 e="🎩" size="26px" /><span><b>{name}</b><small>{c ? `${proofs} proofs · $${credit.toFixed(2)} model credit` : 'No desktop yet'}</small></span></span>
        {c ? <span className="dag-a"><button type="button" className="m-btn" onClick={() => setOpen(c)} data-tip={`Open ${name}'s desktop`} data-testid={`desk-open-${name}`}>Open desktop</button><button type="button" className="m-btn m-go" disabled={!!busy || c.agentWallet?.address || credit <= 0} onClick={() => file(c)} data-tip={credit <= 0 ? 'It needs model credit first' : 'Asks it to file a PoW, on paper'} data-testid={`desk-file-${name}`}>{busy === name ? 'Asking…' : 'File a PoW'}</button></span>
          : <button type="button" className="m-btn m-go" disabled={!!busy || !brains} onClick={() => make(row)} data-tip={brains ? `Makes ${name} with the same two minds as your other agent` : 'Launch one agent first, so it can use the same minds'} data-testid={`desk-make-${name}`}>{busy === name ? 'Making…' : 'Make its desktop'}</button>}</li>; })}</ul>
    {said ? <small className="pvr-msg" role="status">{said}</small> : null}{err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {open ? <AgentDesktop cat={open} onClose={() => { setOpen(null); load(); }} /> : null}</section>;
}
