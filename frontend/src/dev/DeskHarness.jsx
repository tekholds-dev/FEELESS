import React, { useEffect, useState } from 'react';
import { CatWorkbench } from '../components/command/CatWorkbench';
import { FeeCatDesk } from '../components/command/FeeCatDesk';
import '../styles/feecatDesk.css';
import { applyLook, DEFAULT_LOOK, LOCAL_LOOKS } from '../lib/looks';
import '../styles/agentDemo.css';
import '../styles/catWorkbench.css';
import '../styles/agentDesk.css';

// 🧪 DEV ONLY (`/dev/desk`, never in a production build): the agent desk in the Desk look on Happy's REAL data — the read-only snapshot
// `scripts/dev-agent-snapshot.py` writes to the gitignored public/dev-agent.json (no keys, logins or wallet records). Every work op is answered
// here: nothing reaches the server, nothing can spend, post or trade. ?classic = the classic desk · ?w=700 = that wide · ?approve = one waiting row.
const Q = window.location.search; const W = Number((Q.match(/[?&]w=(\d+)/) || [])[1]) || 0;
let SNAP = null; const SENT = []; window.__deskSent = SENT;
const state = () => ({ chat: SNAP.chat, powFolders: SNAP.powFolders, psFolders: SNAP.psFolders, pobFolders: SNAP.pobFolders, pocFolders: SNAP.pocFolders, popFolders: SNAP.popFolders, poeFolders: SNAP.poeFolders,
  windows: [], live: true, task: null, commands: [['file a PoW', 'A new 4-coin PoW folder'], ['file a poc', 'A new PoC'], ['file a pob', 'A new PoB']], logins: [], secrets: [], signedIn: [], storage: { files: [] }, refusals: [], cloud: [], jobs: [], artifacts: [], activeProofs: [] });
const REAL = window.fetch;
window.fetch = async (url, opt) => {
  const u = String(url);
  if (/\/api\/cats\/[^/]+\/work/.test(u)) { const b = JSON.parse(opt?.body || '{}'); SENT.push(b);
    const ok = j => ({ ok: true, status: 200, json: async () => j });
    if (b.op === 'state') return ok(state());
    if (b.op === 'approvals') return ok({ approvals: /approve/.test(Q) ? [{ id: 'ap1', state: 'waiting', what: 'Redo PoC #14 with both minds', op: { op: 'poc' }, models: SNAP.brains, estUsd: 0.04, at: Date.now() / 1000 - 300 }] : [] });
    if (b.op === 'approve') return ok({ approvals: [], row: { id: b.text, state: b.job === 'yes' ? 'ran' : 'declined' } });
    if (b.op === 'ws_open') return ok({ doc: SNAP.docs?.[b.job] || { id: b.job, kind: 'content', messages: [] } });
    if (b.op === 'desk_apps') return ok({ apps: [] });
    return { ok: false, status: 400, json: async () => ({ detail: `Harness only: “${b.op}” is not sent from this page.` }) }; }
  if (u.includes('/feed')) return { ok: true, status: 200, json: async () => ({ rows: [] }) };
  return REAL(url, opt);
};
applyLook(LOCAL_LOOKS[(Q.match(/[?&]look=(\w+)/) || [])[1]] || DEFAULT_LOOK);   // the site's default look, as the real page wears it
// ?fee = Fee's desk on her REAL public state (leader profile + activity, read live); every POST is only recorded here, never sent
const feeCall = async (u, o) => { if (o?.method && o.method !== 'GET') { SENT.push({ u, ...JSON.parse(o.body || '{}') }); return {}; }
  const [prof, act] = await Promise.all([REAL('/api/cats/leader/profile').then(r => r.json()), REAL('/api/cats/activity?catId=leader').then(r => r.json())]);
  return { rules: {}, bounds: {}, leader: { status: (prof.cat || {}).status }, strategyPreset: 'feecat', events: (act.events || []).slice(0, 30), discipline: prof.discipline, cat: prof.cat || {}, scan: {}, duo: {}, duoLearn: {} }; };
export default function DeskHarness() {
  const [cat, setCat] = useState(null);
  useEffect(() => { try { localStorage.setItem('feeless.deskLook', JSON.stringify({ ...JSON.parse(localStorage.getItem('feeless.deskLook') || '{}'), classic: /classic/.test(Q) })); } catch { /* private */ }
    REAL('/dev-agent.json').then(r => r.json()).then(j => { SNAP = j; setCat({ id: j.id, name: j.name, brainsCfg: { kind: 'general', brains: j.brains } }); }); }, []);
  if (/fee/.test(Q)) return <div className="kd" style={{ height: '100vh', width: W ? `${W}px` : '100%', overflow: 'auto' }} data-testid="desk-harness"><FeeCatDesk call={feeCall} /></div>;
  if (!cat) return <p style={{ padding: 20 }}>Loading the snapshot… (run scripts/dev-agent-snapshot.py first)</p>;
  return <div className="kd" style={{ height: '100vh', width: W ? `${W}px` : '100%' }} data-testid="desk-harness"><CatWorkbench cat={cat} /></div>;
}
