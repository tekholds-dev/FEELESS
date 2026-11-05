import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Ic3 } from '../../lib/icon3d';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';
import { AgentDesktop } from './CatWorkbench';
import '../../styles/collectiveSetup.css';

// 🎩 SICARIO'S (owner 2026-11-05): one agent with OSSY and G4 as its two minds, on its own desktop and proof loop, private to the owner. Paper only: no wallet is ever attached here, so a filed PoW cannot buy with real money.
export const DESK_AGENT = "Sicario's";
const ColonyGrid = lazy(() => import('./HiveBoard').then(m => ({ default: m.ColonyGrid })));
const colonyApi = async u => { const r = await fetch(apiUrl(u.startsWith('/api') ? u : `/api/cats${u}`)); if (!r.ok) throw new Error('Could not read the monitors.'); return r.json(); };
const call = async (path, opts) => { const r = await fetch(apiUrl(path), { headers: { 'Content-Type': 'application/json' }, ...opts }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`); return j; };
export function DeskAgents() {
  const [cats, setCats] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const [said, setSaid] = useState(''); const [open, setOpen] = useState(false);
  const load = useCallback(() => call(`/api/cats?${agentAuthQuery()}`).then(j => setCats(j.cats || [])).catch(e => { setErr(e.message); setCats([]); }), []);
  useEffect(() => { load(); }, [load]);
  const file = async c => { setBusy(true); setErr(''); setSaid(''); try { const body = text => ({ method: 'POST', body: JSON.stringify({ ...agentAuth(), op: 'ask', text }) }); await call(`/api/cats/${c.id}/work`, body('file a pow')); await call(`/api/cats/${c.id}/work`, body('go')); setSaid('It started a PoW, on paper. Watch it on the monitors.'); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (!cats) return null;
  const c = cats.find(x => x.name === DESK_AGENT && !x.revoked); if (!c) return null;
  const proofs = (c.powFolders?.length || 0) + (c.popFolders?.length || 0) + (c.pobFolders?.length || 0); const credit = Number(c.brainsCfg?.credit) || 0;
  return <section className="dag" data-testid="desk-agents"><header><span className="dag-n"><Ic3 e="🎩" size="26px" /><span><b>{DESK_AGENT}</b><small>OSSY + G4 · {proofs} proofs · ${credit.toFixed(2)} model credit · paper only, private to you</small></span></span>
      <span className="dag-a"><button type="button" className="m-btn" onClick={() => setOpen(true)} data-tip="Open its desktop" data-testid="desk-open">Open desktop</button><button type="button" className="m-btn m-go" disabled={busy || c.agentWallet?.address || credit <= 0} onClick={() => file(c)} data-tip={credit <= 0 ? 'It needs model credit first' : 'Asks both minds to file a PoW, on paper'} data-testid="desk-file">{busy ? 'Asking…' : 'File a PoW'}</button></span></header>
    <Suspense fallback={null}><ColonyGrid api={colonyApi} ids={c.id} onOpen={() => setOpen(true)} /></Suspense>
    {said ? <small className="pvr-msg" role="status">{said}</small> : null}{err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    {open ? <AgentDesktop cat={c} onClose={() => { setOpen(false); load(); }} /> : null}</section>;
}
