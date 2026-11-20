import React from 'react';
import { ProofDesk } from '../components/command/FeaturesFolder';
import FIX from './pocDeskFixture.json';   // 📣 Slice 24: Happy's real PoC folders (#1–#14, the last 3 from the Slice 24 TEST clip run on an iPhone HEVC .mov) + its content folders + that clip run, exported from feecats.json 2026-11-20
import '../styles/agentDemo.css';
import '../styles/catWorkbench.css';
import '../styles/agentDesk.css';

// 🧪 DEV ONLY (`/dev/pocdesk`, never in a production build): the PoC desk window on Happy's REAL folders, inside the real desk window chrome.
// The trend reader is the live public one (/api/cats/tools/content). Every other op is answered here from the fixture: nothing reaches the
// server and nothing can post. ?day = day theme · ?w=700 = the window that wide (a half window) · ?clips = open the first folder's Clips tab.
const Q = window.location.search; const W = Number((Q.match(/[?&]w=(\d+)/) || [])[1]) || 0;
const REAL_FETCH = window.fetch;
window.fetch = async (url, opt) => {   // the clip farm's own routes (it fetches directly) answered from the real run
  const u = String(url);
  if (u.includes('/clipfarm')) return { ok: true, status: 200, json: async () => ({ runs: [FIX.clipRun], busy: false }) };
  return REAL_FETCH(url, opt);
};
const DOC = id => { const w = FIX.workspaces.find(x => x.id === id) || FIX.workspaces[0]; return { id: w.id, kind: 'content', name: w.name, title: w.name, messages: [] }; };
const work = async (_id, b) => {
  if (b.op === 'features') return { workspaces: FIX.workspaces, pocFolders: FIX.pocFolders, psFolders: [] };
  if (b.op === 'ws_open') return { doc: DOC(b.text || b.job) };
  if (b.op === 'poc_accounts') return { services: [] };
  if (b.op === 'media_models') return { models: [], presets: [] };
  if (b.op === 'kits' || b.op === 'kit_pick') return { kits: [], picked: [] };
  throw new Error('Harness only: nothing is sent from this page.');
};

export default function PocDeskHarness() {
  if (/day/.test(Q)) document.body.classList.add('theme-day');
  const start = /clips/.test(Q) ? { folder: FIX.workspaces[FIX.workspaces.length - 1], draft: '', at: 1 } : null;
  return <div className="dsk-win" style={{ height: '100vh', width: W ? `${W}px` : '100%', background: 'var(--m-bg)', boxSizing: 'border-box' }} data-testid="pocdesk-harness">
    <div className="dsk-body" style={{ height: '100%', overflow: 'auto', display: 'grid', alignContent: 'start', padding: 10, boxSizing: 'border-box' }}>
      <ProofDesk cat={FIX.cat} kind="content" work={work} onCommand={t => console.log('[harness] chat box ←', t)} onBrowse={() => {}} d={{}} setD={() => {}} start={start} />
    </div></div>;
}
