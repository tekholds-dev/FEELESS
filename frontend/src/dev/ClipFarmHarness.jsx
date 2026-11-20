import React, { useState } from 'react';
import ClipFarm from '../components/command/ClipFarm';
import PocStudio from '../components/command/PocStudio';
import { TrueRecord } from '../components/command/TrueRecord';
import FIX from './clipFarmFixture.json';   // ✂ Slice 15: Happy's real TEST clip-farm run on an iPhone HEVC .mov (5:00 public-domain interview, converted free) + its 3 clip PoCs, as feecats.json holds them, 2026-11-20
import '../styles/features.css';

// 🧪 DEV ONLY (`/dev/clipfarm`, never in a production build): the clip farm on a REAL TEST run (Happy's .mov, 2026-11-20), its real clip files served by the
// backend. The clip routes are answered here from the fixture (the page has no owner sign-in), so nothing reaches the server and nothing can
// post: the day buttons save into this page only, and Delete on a link ends it in this page only. ?running shows the same run mid-way. ?day = day theme. ?empty = before any upload.

const REAL_FETCH = window.fetch; const HOOK = { setLog: () => {}, setPocs: () => {}, pocs: FIX.folders };
window.fetch = async (url, opt = {}) => {   // installed before the first render: ClipFarm's first load is answered from the fixture too
  const u = String(url); const q = window.location.search;
  if (!u.includes('/clipfarm')) return REAL_FETCH(url, opt);
  HOOK.setLog(l => [...l, `${opt.method || 'GET'} ${u.replace(/\?.*/, '')} ${opt.body || ''}`].slice(-4));
  const ok = j => ({ ok: true, status: 200, json: async () => j });
  if (u.includes('/slot')) { const b = JSON.parse(opt.body || '{}'); HOOK.pocs = HOOK.pocs.map(f => f.id === b.job ? { ...f, studio: { ...f.studio, slot: b.day } } : f); return ok({ pocFolders: HOOK.pocs }); }
  if (u.includes('/unlink')) { const b = JSON.parse(opt.body || '{}'); FIX.run.links = (FIX.run.links || []).map(k => k.id === b.id ? { ...k, gone: true } : k); return ok({ ok: true }); }   // page only: the real link stays
  if (/empty/.test(q)) return ok({ runs: [], busy: false });
  const run = /running/.test(q) ? { ...FIX.run, status: 'running', clips: FIX.run.clips.slice(0, 1), doneS: null, steps: FIX.run.steps.map(s => s.key === 'clips' ? { ...s, state: 'running', note: 'clip 2 of 3: 9:16 made', secs: null } : s.key === 'file' ? { ...s, state: 'todo', note: '' } : s) } : FIX.run;
  return ok({ runs: [run], busy: /running/.test(q) });
};

export default function ClipFarmHarness() {
  const q = window.location.search; if (/day/.test(q)) document.body.classList.add('theme-day');
  const [pocs, setPocs] = useState(FIX.folders); const [focus, setFocus] = useState(FIX.folders[0]?.id); const [log, setLog] = useState([]);
  HOOK.setLog = setLog;
  const f = pocs.find(x => x.id === focus);
  return <div style={{ padding: 16, maxWidth: 1180, margin: '0 auto', display: 'grid', gap: 12 }} data-testid="clipfarm-harness">
    <small className="m-label">HARNESS · Happy’s real TEST clip run (iPhone HEVC .mov, converted) {FIX.run.id} · PoC #{FIX.folders.map(x => x.n).join(', #')} · nothing reaches the server here</small>
    <ClipFarm cat={{ id: FIX.cat }} wsId="" pocs={/empty/.test(q) ? [] : pocs} onPocs={rows => rows && setPocs(rows)} onOpen={x => { setFocus(x.id); document.getElementById('cfh-studio')?.scrollIntoView({ behavior: 'smooth' }); }} />
    <div id="cfh-studio">{f ? <PocStudio cat={{ id: FIX.cat }} f={f} work={async (_id, b) => { if (b.op === 'poc_accounts') return { services: [] }; throw new Error('Harness only: nothing posts from this page.'); }} /> : null}</div>
    {f ? <TrueRecord kind="poc" folders={[f]} /> : null}
    <pre style={{ fontSize: 11, opacity: 0.7, whiteSpace: 'pre-wrap' }} data-testid="harness-log">{log.join('\n')}</pre>
  </div>;
}
