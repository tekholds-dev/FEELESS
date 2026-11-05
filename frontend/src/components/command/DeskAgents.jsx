import React, { useCallback, useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';
import { CatWorkbench } from './CatWorkbench';
import '../../styles/collectiveSetup.css';

// 🎩 SICARIO'S (owner 2026-11-05): one agent with OSSY and G4 as its two minds, on the owner's own models, private to the owner. It gets the same full desk as every agent. Its one difference: with its Fuse seat on, an agreed PoW goes to the real card's one model seat, through every guard that seat already has. It holds no wallet.
export const DESK_AGENT = "Sicario's";
const call = async (path, opts) => { const r = await fetch(apiUrl(path), { headers: { 'Content-Type': 'application/json' }, ...opts }); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`); return j; };
export function DeskAgents() {
  const [cats, setCats] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const load = useCallback(() => call(`/api/cats?${agentAuthQuery()}`).then(j => setCats(j.cats || [])).catch(e => { setErr(e.message); setCats([]); }), []);
  useEffect(() => { load(); }, [load]);
  if (!cats) return null;
  const c = cats.find(x => x.name === DESK_AGENT && !x.revoked); if (!c) return null;
  const flip = async (op, on) => { setBusy(true); setErr(''); try { await call(`/api/cats/${c.id}/work`, { method: 'POST', body: JSON.stringify({ ...agentAuth(), op, on }) }); await load(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const loop = !!c.brainsCfg?.endless; const seat = !!c.brainsCfg?.cardSeat; const proofs = ['powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders'].reduce((n, k) => n + (c[k]?.length || 0), 0);
  return <section className="dag" data-testid="desk-agents"><header><span className="dag-n"><span><em>ONLY YOU SEE THIS · OSSY + G4 ON YOUR OWN MODELS</em><b>{DESK_AGENT}</b><small>{proofs} proofs filed. {seat ? 'An agreed PoW goes to the Fuse card seat. The card can still refuse it.' : 'PoWs stay on paper until you turn on its Fuse seat.'}</small></span></span>
      <span className="dag-a"><button type="button" className={`m-btn dag-loop${seat ? ' is-on' : ''}`} aria-pressed={seat} disabled={busy} onClick={() => flip('desk_seat', !seat)} data-tip={seat ? 'Agreed PoWs go to the card. Tap to stop' : "Sends each agreed PoW to the real card's one model seat. Card rules, desk buys off and its cash still apply"} data-testid="desk-seat"><i aria-hidden="true" />{seat ? 'Fuse seat: on' : 'Fuse seat: off'}</button>
        <button type="button" className={`m-btn dag-loop${loop ? ' is-on' : ''}`} aria-pressed={loop} disabled={busy} onClick={() => flip('desk_loop', !loop)} data-tip={loop ? 'It keeps filing proofs, one at a time. Tap to stop' : 'Keep filing proofs, one at a time, on your own models'} data-testid="desk-loop"><i aria-hidden="true" />{loop ? 'Endless: on' : 'Endless: off'}</button></span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <CatWorkbench cat={c} /></section>;
}
