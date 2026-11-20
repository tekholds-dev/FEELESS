import React, { useState } from 'react';
import ClipFarm from '../components/command/ClipFarm';
import PocStudio from '../components/command/PocStudio';
import { TrueRecord } from '../components/command/TrueRecord';
import FIX from './clipFarmFixture.json';   // ✂ Slice 15: Happy's real TEST clip-farm run on an iPhone HEVC .mov (5:00 public-domain interview, converted free) + its 3 clip PoCs, as feecats.json holds them, 2026-11-20
import '../styles/features.css';

// 🧪 DEV ONLY (`/dev/clipfarm`, never in a production build): the clip farm on a REAL TEST run (Happy's .mov, 2026-11-20), its real clip files served by the
// backend. The clip routes are answered here from the fixture (the page has no owner sign-in), so nothing reaches the server and nothing can
// post: the day buttons save into this page only, and Delete on a link ends it in this page only. ?running shows the same run mid-way. ?day = day theme. ?empty = before any upload.

// 🎨🗓 Slice 29: `?real` reads the gitignored public/dev-clips.json (Happy's live clips, plan, chat and words after the TEST, exported from
// feecats.json) so the studio is checked on real data. Its clicks are answered here too: a look is saved as a version in this page (no render),
// the week saves in this page, the minds (agent plan, chat, minds pick) answer only in the TEST, never from this page.
const REAL_FETCH = window.fetch; const HOOK = { setLog: () => {}, setPocs: () => {}, pocs: FIX.folders, real: null, plan: { versions: [], chat: [] } };
// 🎨 Slice 29 add-on: templates are answered here too (save / delete / default / put on), in this page only, with no render; the minds' picks answer only in the TEST.
const tplOps = (u, b) => {
  const T = HOOK.real?.templates; if (!T) throw Object.assign(new Error('Harness only: templates need ?real.'), { status: 409 });
  const view = () => ({ templates: { ...T, list: [...T.list], defaults: { ...T.defaults } } });
  if (u.includes('/template/minds')) throw Object.assign(new Error('Harness only: the minds pick in the TEST run, not from this page.'), { status: 409 });
  if (u.includes('/template/save')) { const row = { id: b.id || `t${Date.now() % 1e6}`, name: b.name, look: b.look, fmts: b.fmts || ['story', 'feed', 'wide'], by: 'owner', builtin: false, describe: `${b.look?.cap?.style || 'pop'} captions · ${b.look?.tr || 'cut'}`, at: Date.now() / 1000 };
    T.list = b.id ? T.list.map(x => x.id === b.id ? row : x) : [...T.list, row]; return { ...view(), id: row.id }; }
  if (u.includes('/template/delete')) { T.list = T.list.filter(x => x.id !== b.id); Object.keys(T.defaults).forEach(k => { if (T.defaults[k] === b.id) T.defaults[k] = k === 'farm' ? 'minds' : ''; }); return view(); }
  if (u.includes('/template/default')) { T.defaults = { ...T.defaults, [b.key]: b.tpl }; return view(); }
  if (u.includes('/template/apply')) { const tp = T.list.find(x => x.id === b.tpl); const runOf = f => f.studio.clip?.run;
    const run = b.run; const hit = f => !f.posted && (b.job ? f.id === b.job : run ? runOf(f) === run : !!f.studio.slot);
    HOOK.pocs = HOOK.pocs.map(f => hit(f) ? { ...f, studio: { ...f.studio, look: { ...tp.look, preset: tp.id }, tpl: { id: tp.id, name: tp.name, by: 'owner', why: 'put on in this page (no render)', at: Date.now() / 1000 } } } : f);
    return { pocFolders: HOOK.pocs, changed: HOOK.pocs.filter(hit).map(f => f.id), notes: [] }; }
  return null;
};
const clipOps = (u, b) => {
  const plan = HOOK.plan; const v = (plan.versions || []).slice(-1)[0]?.v || 0;
  if (u.includes('/words')) { const job = new URL(u, window.location.href).searchParams.get('job'); return { words: HOOK.real?.words?.[job] || [], dur: 30 }; }
  if (u.includes('/plan/undo')) { const old = plan.versions.find(x => x.v === b.v); HOOK.plan = { ...plan, versions: [...plan.versions, { ...old, v: v + 1, by: 'undo', why: `back to plan v${b.v}`, at: Date.now() / 1000 }], cur: v + 1 }; return { plan: HOOK.plan }; }
  if (u.includes('/template/')) return tplOps(u, b);
  if (u.includes('/plan/agent') || u.includes('/plan/chat') || u.includes('/look/mind') || u.includes('/template/mind')) throw Object.assign(new Error('Harness only: the minds answer in the TEST run, not from this page.'), { status: 409 });
  if (u.includes('/plan')) { HOOK.plan = { ...plan, versions: [...plan.versions, { v: v + 1, by: 'owner', why: 'your week (this page only)', slots: b.slots, at: Date.now() / 1000 }], cur: v + 1 };
    HOOK.pocs = HOOK.pocs.map(f => { const sl = b.slots.find(x => x.job === f.id); return { ...f, studio: { ...f.studio, slot: sl?.day || '', slotTime: sl?.time || '' } }; }); return { plan: HOOK.plan, pocFolders: HOOK.pocs }; }
  if (u.includes('/look/undo')) { HOOK.pocs = HOOK.pocs.map(f => { if (f.id !== b.job) return f; const o = f.studio.looks.find(x => x.v === b.v); const n = f.studio.looks.slice(-1)[0].v + 1;
    return { ...f, studio: { ...f.studio, look: o.look, files: o.files || f.studio.files, looks: [...f.studio.looks, { ...o, v: n, by: 'undo', why: `back to look v${b.v}`, at: Date.now() / 1000 }] } }; }); return { pocFolders: HOOK.pocs }; }
  if (u.includes('/look')) { HOOK.pocs = HOOK.pocs.map(f => { if (f.id !== b.job) return f; const ls = f.studio.looks?.length ? f.studio.looks : [{ v: 1, by: 'code', why: 'how it was first made', look: f.studio.look, files: f.studio.files, at: f.at }];
    return { ...f, studio: { ...f.studio, look: b.look, looks: [...ls, { v: ls.slice(-1)[0].v + 1, by: 'owner', why: `${b.why} (this page only: no render)`, look: b.look, at: Date.now() / 1000 }] } }; }); return { pocFolders: HOOK.pocs }; }
  return null;
};
window.fetch = async (url, opt = {}) => {   // installed before the first render: ClipFarm's first load is answered from the fixture too
  const u = String(url); const q = window.location.search;
  if (!u.includes('/clipfarm')) return REAL_FETCH(url, opt);
  HOOK.setLog(l => [...l, `${opt.method || 'GET'} ${u.replace(/\?.*/, '')} ${opt.body || ''}`].slice(-4));
  const ok = j => ({ ok: true, status: 200, json: async () => j });
  if (/real/.test(q) && !HOOK.real) { try { HOOK.real = await (await REAL_FETCH('/dev-clips.json')).json(); HOOK.pocs = HOOK.real.folders; HOOK.plan = HOOK.real.plan || HOOK.plan; HOOK.setPocs(HOOK.pocs); } catch { HOOK.real = {}; } }
  try { const j = clipOps(u, JSON.parse(opt.body || '{}')); if (j) return ok(j); } catch (e) { return { ok: false, status: e.status || 400, json: async () => ({ detail: e.message }) }; }
  if (u.includes('/slot')) { const b = JSON.parse(opt.body || '{}'); HOOK.pocs = HOOK.pocs.map(f => f.id === b.job ? { ...f, studio: { ...f.studio, slot: b.day } } : f); return ok({ pocFolders: HOOK.pocs }); }
  if (u.includes('/unlink')) { const b = JSON.parse(opt.body || '{}'); FIX.run.links = (FIX.run.links || []).map(k => k.id === b.id ? { ...k, gone: true } : k); return ok({ ok: true }); }   // page only: the real link stays
  if (/empty/.test(q)) return ok({ runs: [], busy: false });
  const run = /running/.test(q) ? { ...FIX.run, status: 'running', clips: FIX.run.clips.slice(0, 1), doneS: null, steps: FIX.run.steps.map(s => s.key === 'clips' ? { ...s, state: 'running', note: 'clip 2 of 3: 9:16 made', secs: null } : s.key === 'file' ? { ...s, state: 'todo', note: '' } : s) } : FIX.run;
  if (HOOK.real?.runs) return ok({ runs: HOOK.real.runs, busy: false, plan: HOOK.plan, kit: HOOK.real.kit, templates: HOOK.real.templates ? { ...HOOK.real.templates, list: [...HOOK.real.templates.list] } : undefined, rendering: [] });
  return ok({ runs: [run], busy: /running/.test(q), plan: HOOK.plan });
};

export default function ClipFarmHarness() {
  const q = window.location.search; if (/day/.test(q)) document.body.classList.add('theme-day');
  const [pocs, setPocs] = useState(FIX.folders); const [focus, setFocus] = useState(FIX.folders[0]?.id); const [log, setLog] = useState([]);
  HOOK.setLog = setLog; HOOK.setPocs = setPocs;
  const f = pocs.find(x => x.id === focus);
  return <div style={{ padding: 16, maxWidth: /w=(\d+)/.test(q) ? Number(q.match(/w=(\d+)/)[1]) : 1180, margin: '0 auto', display: 'grid', gap: 12 }} data-testid="clipfarm-harness">
    <small className="m-label">HARNESS · Happy’s real TEST clip run (iPhone HEVC .mov, converted) {FIX.run.id} · PoC #{FIX.folders.map(x => x.n).join(', #')} · nothing reaches the server here</small>
    <ClipFarm cat={{ id: HOOK.real?.cat || FIX.cat }} wsId="" pocs={/empty/.test(q) ? [] : pocs} onPocs={rows => rows && setPocs(rows)} onOpen={x => { setFocus(x.id); document.getElementById('cfh-studio')?.scrollIntoView({ behavior: 'smooth' }); }} />
    <div id="cfh-studio">{f ? <PocStudio cat={{ id: FIX.cat }} f={f} work={async (_id, b) => { if (b.op === 'poc_accounts') return { services: [] }; throw new Error('Harness only: nothing posts from this page.'); }} /> : null}</div>
    {f ? <TrueRecord kind="poc" folders={[f]} /> : null}
    <pre style={{ fontSize: 11, opacity: 0.7, whiteSpace: 'pre-wrap' }} data-testid="harness-log">{log.join('\n')}</pre>
  </div>;
}
