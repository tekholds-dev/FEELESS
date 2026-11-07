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
  const [seats, setSeats] = useState(null); const sid = cats?.find(x => x.name === DESK_AGENT && !x.revoked)?.id;
  useEffect(() => { if (!sid) return undefined; const read = () => call(`/api/cats/${sid}/work`, { method: 'POST', body: JSON.stringify({ ...agentAuth(), op: 'desk_seats' }) }).then(j => setSeats(j.seats || null)).catch(() => {}); read(); const t = setInterval(read, 30000); return () => clearInterval(t); }, [sid]);
  if (!cats) return null;
  const c = cats.find(x => x.name === DESK_AGENT && !x.revoked); if (!c) return null;
  const flip = async (op, on) => { setBusy(true); setErr(''); try { await call(`/api/cats/${c.id}/work`, { method: 'POST', body: JSON.stringify({ ...agentAuth(), op, on }) }); await load(); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const loop = !!c.brainsCfg?.endless; const seat = !!c.brainsCfg?.cardSeat; const filling = !!c.hive?.on; const proofs = ['powFolders', 'popFolders', 'pobFolders', 'pocFolders', 'psFolders'].reduce((n, k) => n + (c[k]?.length || 0), 0);
  return <section className="dag" data-testid="desk-agents"><header><span className="dag-n"><span><em>ONLY YOU SEE THIS · OSSY + G4 ON YOUR OWN MODELS</em><b>{DESK_AGENT}</b><small>Works when you ask, on any proof, on your own models. {proofs} proofs filed. {filling && seats?.free ? `Auto-collect is on: it runs PoWs until the ${seats.seats} seats are full.` : filling ? 'Auto-collect is on and no seat is free, so no new PoW is filed.' : seat ? 'An agreed PoW goes to a free card seat. The card can still refuse it.' : 'Its PoWs stay on paper; the real card is not touched.'}</small></span></span>
      {seats ? <span className="dag-seats" role="img" aria-label={`${seats.held} of ${seats.seats} card seats full`} data-tip={`${seats.ai} held by its PoWs, ${seats.held - seats.ai} by the desk`} data-testid="desk-seat-meter">{Array.from({ length: seats.seats }, (_, i) => <i key={i} className={i < seats.held ? 'is-on' : ''} />)}<small className="m-num">{seats.held}/{seats.seats} SEATS</small></span> : null}
      <span className="dag-a"><button type="button" className="m-btn" disabled={busy} onClick={async () => { setBusy(true); setErr(''); try { const j = await call(`/api/cats/${c.id}/work`, { method: 'POST', body: JSON.stringify({ ...agentAuth(), op: 'desk_stop' }) }); setErr(j.stopped ? '' : 'OSSY and G4 were not writing anything.'); } catch (e) { setErr(e.message); } finally { setBusy(false); } }} data-tip="Stops what OSSY and G4 are writing right now, and anything waiting behind it" data-testid="desk-stop">⏹ Stop writing</button>{seat ? <button type="button" className={`m-btn dag-loop${seat ? ' is-on' : ''}`} aria-pressed={seat} disabled={busy} onClick={() => flip('desk_seat', !seat)} data-tip={seat ? 'Agreed PoWs go to the card. Tap to stop' : "Sends each agreed PoW to a free seat on the real card, any of the 4. Card rules and its cash still apply"} data-testid="desk-seat"><i aria-hidden="true" />{seat ? 'Fuse seat: on' : 'Fuse seat: off'}</button> : null}
        {loop ? <button type="button" className={`m-btn dag-loop${loop ? ' is-on' : ''}`} aria-pressed={loop} disabled={busy} onClick={() => flip('desk_loop', !loop)} data-tip={loop ? 'It keeps filing proofs, one at a time. Tap to stop' : 'Keep filing proofs, one at a time, on your own models'} data-testid="desk-loop"><i aria-hidden="true" />{loop ? 'Endless: on' : 'Endless: off'}</button> : null}</span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <CatWorkbench cat={c} /></section>;
}
