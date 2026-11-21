import React, { useEffect, useState } from 'react';
import { ProofDesk } from '../components/command/FeaturesFolder';
import '../styles/agentDemo.css';
import '../styles/catWorkbench.css';
import '../styles/agentDesk.css';

// 🧪 DEV ONLY (`/dev/posdesk`, never in a production build): Slice 27's PoStatic desk window on an agent's REAL PoStatic folders, inside the real
// desk window chrome. The data is the gitignored public/dev-postatic.json, written read-only by the services' own view:
//   PYTHONPATH=backend:. .venv/bin/python scripts/dev-postatic-snapshot.py <catId>
// Reads (features, ws_open, ws_version, state) are answered from it; anything that would build, mark or spend is refused here: nothing reaches the
// server. ?day = day theme · ?w=700 = the window that wide (a half window) · ?open=<wsId> opens that folder · ?inspect opens it with inspect on.
const Q = window.location.search; const W = Number((Q.match(/[?&]w=(\d+)/) || [])[1]) || 0;
const OPEN = (Q.match(/[?&]open=(w[0-9a-f]+)/) || [])[1] || '';

export default function PosDeskHarness() {
  const [fx, setFx] = useState(null); const [err, setErr] = useState('');
  useEffect(() => { fetch('/dev-postatic.json').then(r => (r.ok ? r.json() : Promise.reject(new Error(`dev-postatic.json: ${r.status}. Run scripts/dev-postatic-snapshot.py first`)))).then(setFx).catch(e => setErr(e.message)); }, []);
  if (/day/.test(Q)) document.body.classList.add('theme-day');
  if (err) return <p style={{ padding: 20, color: 'var(--m-danger)' }}>{err}</p>;
  if (!fx) return <p style={{ padding: 20, color: 'var(--m-dim)' }}>Reading the snapshot…</p>;
  const work = async (_id, b) => {
    if (b.op === 'features') return { workspaces: fx.workspaces, psFolders: fx.psFolders, pocFolders: [] };
    if (b.op === 'state') return { psFolders: fx.psFolders };
    if (b.op === 'ws_open') { const id = b.text || b.job; const w = fx.workspaces.find(x => x.id === id) || {}; return { doc: fx.docs[id] || { id, kind: 'build', name: w.name, messages: [], versions: 0 } }; }
    if (b.op === 'ws_version') { const v = (fx.versions[b.text] || [])[Number(b.i) - 1]; if (!v) throw new Error('Not in the snapshot.'); return { version: v }; }
    if (b.op === 'kits' || b.op === 'kit_pick') return { kits: [], picked: [] };
    if (b.op === 'parts' || b.op === 'parts_list') return { parts: [] };
    throw new Error('Harness only: nothing is sent from this page.');
  };
  const w0 = OPEN && fx.workspaces.find(x => x.id === OPEN);
  const start = w0 ? { folder: w0, draft: '', at: 1 } : null;
  return <div className="dsk-win" style={{ height: '100vh', width: W ? `${W}px` : '100%', background: 'var(--m-bg)', boxSizing: 'border-box' }} data-testid="posdesk-harness">
    <div className="dsk-body" style={{ height: '100%', overflow: 'auto', display: 'grid', alignContent: 'start', padding: 10, boxSizing: 'border-box' }}>
      <ProofDesk cat={fx.cat} kind="build" work={work} onCommand={t => console.log('[harness] chat box ←', t)} onBrowse={() => {}} d={{}} setD={() => {}} start={start} />
    </div></div>;
}
