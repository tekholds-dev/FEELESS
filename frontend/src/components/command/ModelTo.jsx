import React, { useState } from 'react';

// 🪦 owner 2026-11-17: a model as you set it here (size, turn, spin) goes to a build, and that build's agent uses this exact model throughout the site
export function ModelTo({ obj, builds, proof, cat, work, onSaid, onErr }) {
  const [to, setTo] = useState(proof?.id || builds[builds.length - 1]?.id || ''); const [busy, setBusy] = useState(false);
  if (!builds.length) return <p className="p3d-hint" data-testid="p3d-to-none">Make a PoStatic folder to send this model to a build.</p>;
  const send = async () => { setBusy(true); onErr(''); onSaid(''); try { const j = await work(cat.id, { op: 'play3d_model_to', tools: { to, obj } }); onSaid(j.say); } catch (x) { onErr(x.message); } setBusy(false); };
  return <div className="p3d-to" data-testid="p3d-to"><small className="m-label">USE IN A BUILD</small><select className="m-input" value={to} onChange={e => setTo(e.target.value)} aria-label="Which PoStatic build uses it" data-testid="p3d-to-pick">{builds.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select><button type="button" className="m-btn m-go" disabled={busy || !to} onClick={send} data-tip="That build's agent uses this exact model, as you set it, throughout the site it builds" data-testid="p3d-to-send">{busy ? 'Adding…' : 'Add to build'}</button></div>;
}
