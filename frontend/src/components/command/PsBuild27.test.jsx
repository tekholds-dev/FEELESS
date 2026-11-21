import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeaturesFolder } from './FeaturesFolder';
import { PsDash, psChecks, psFolders } from './PsDash';
import { addPick, canEdit, pickWord } from './PsInspect';

// 💻 Slice 27 · PoStatic: the builder's dashboard, the build on Slice 33's shell (steps in the bar, one toolbar row + ⋯, an issues tray), and inspect
// everything (text nodes, canvas regions, 3D objects; labels + pin numbers outside the page; text edited in place for $0). Click → op → what comes back.
jest.mock('../terminal/TrenchChart', () => ({ TrenchChart: () => <i data-testid="trench" /> }));
jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => <i data-testid="perps" /> }));
jest.mock('../terminal/TradeTape', () => ({ TradeTape: () => <i data-testid="tape" /> }));
jest.mock('./FeeCatShell', () => ({ goTo: jest.fn() }));
const DATA = { workspaces: [{ id: 'w1', kind: 'build', name: 'Site' }], memory: { notes: 0, mindNotes: 0, recent: [], personal: '' }, print: { level: 1, proofs: 0, traits: [] }, edge: [], edgeCats: {}, indicators: [], pocFolders: [] };
const DOC = { id: 'w1', kind: 'build', name: 'Site', messages: [], versions: 3, by: 'Mind A', code: '<h1>hi</h1>', preview: '<h1>hi</h1>', busy: null, stage: 'filed', inspect: [], comments: [],
  kitsUsed: [{ id: 'three', name: 'three.js', used: true }], kitsOutside: ['https://cdn.jsdelivr.net/npm/gsap/dist/gsap.min.js', '//cdn.tailwindcss.com'] };
const type = async (n, v) => { await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(n, v); n.dispatchEvent(new Event('input', { bubbles: true })); }); };

async function open(doc = DOC) {
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc } : b.op === 'ws_build' ? { doc: { ...doc, versions: doc.versions + 1 } } : DATA));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FeaturesFolder cat={{ id: 'c' }} d={{ setup: { use: 'code' } }} work={work} onCommand={() => {}} />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { q('fea-tab-work').click(); }); await act(async () => { q('ws-w1').click(); }); await act(async () => { await Promise.resolve(); });
  return { el, q, work, w: q('ws-frame').contentWindow };
}
const say = async (w, data) => act(async () => { window.dispatchEvent(new MessageEvent('message', { data, source: w })); });
const lastBuild = work => work.mock.calls.filter(([, b]) => b.op === 'ws_build').at(-1)?.[1];
afterEach(() => { document.body.innerHTML = ''; });

test('💻 the shell: the steps sit in the slim top bar, the tools are one row with ⋯ for the rest, the outside files live in an issues tray', async () => {
  const { q, work } = await open();
  const steps = q('pws-bar').querySelector('[data-testid="ws-steps"]'); expect(steps.className).toContain('is-compact'); expect(steps.querySelector('.is-now')).toBeTruthy();
  const bar = q('ws-toolbar'); for (const id of ['ws-view-static', 'ws-inspect', 'ws-dev-phone', 'ws-kits-did', 'ws-issues', 'ws-full', 'ws-more']) expect(bar.querySelector(`[data-testid="${id}"]`)).toBeTruthy();
  expect(bar.querySelector('[data-testid="ws-kit-outside"]')).toBeNull();   // no "✕ Also loads" chips wrapping the bar any more
  expect(q('ws-more-menu').hidden).toBe(true);
  await act(async () => { q('ws-more').click(); });
  const menu = q('ws-more-menu'); expect(menu.hidden).toBe(false);
  for (const id of ['store-check', 'go-live', 'ws-save-repo']) expect(menu.querySelector(`[data-testid="${id}"]`)).toBeTruthy();
  await act(async () => { document.body.dispatchEvent(new Event('pointerdown', { bubbles: true })); }); expect(q('ws-more-menu').hidden).toBe(true);   // a click elsewhere closes it
  expect(q('ws-issues').textContent).toContain('2'); expect(q('ws-issues-tray')).toBeNull();
  await act(async () => { q('ws-issues').click(); });
  const rows = q('ws-issues-tray').querySelectorAll('[data-testid="ws-kit-outside"]'); expect(rows).toHaveLength(2); expect(rows[0].textContent).toContain('Also loads cdn.jsdelivr.net');
  await act(async () => { q('ws-issue-fix-cdn.tailwindcss.com').click(); });
  expect(lastBuild(work)).toMatchObject({ job: 'w1', to: 'a', text: expect.stringContaining('Stop loading //cdn.tailwindcss.com') });   // saved → its minds get it
  expect(q('ws-issues-tray')).toBeNull();
});

test('🔍 inspect everything: the hover label shows outside the page, pin numbers sit in a gutter beside it, each pick says what it is', async () => {
  const { q, w } = await open();
  await act(async () => { q('ws-inspect').click(); });
  expect(q('ws-insp-hover').textContent).toContain('3D objects');
  await say(w, { t: 'feeless-inspect-hover', label: '3D · Hero cube · BoxGeometry' }); expect(q('ws-insp-hover').textContent).toBe('3D · Hero cube · BoxGeometry');
  await say(w, { t: 'feeless-inspected', sel: '#stage', tag: 'canvas', node: 'three', three: { name: 'Hero cube', type: 'Mesh', geometry: 'BoxGeometry', material: 'MeshStandardMaterial', color: '#19e68c', path: 'Scene > Hero cube' }, text: '' });
  await say(w, { t: 'feeless-inspected', sel: '#chart', tag: 'canvas', node: 'canvas', part: { x: 0, y: 0, w: 1 / 3, h: 1 / 3 }, text: '' });
  await say(w, { t: 'feeless-inspected', sel: '#hero', tag: 'div', node: 'text', text: 'Loose words', leaf: false });
  expect([0, 1, 2].map(i => q(`ws-insp-kind-${i}`).textContent)).toEqual(['3D · Hero cube', 'CANVAS · top left', 'TEXT']);
  expect(q('ws-insp-3d-0').textContent).toContain('Mesh · BoxGeometry · MeshStandardMaterial'); expect(q('ws-insp-edit-0')).toBeNull(); expect(q('ws-insp-edit-1')).toBeNull();
  await say(w, { t: 'feeless-inspect-pinpos', rows: [{ n: 1, kind: 'fix', top: 0.25, h: 0.1 }, { n: 2, kind: 'fix', top: 1.4, h: 0.1 }] });
  const g = q('ws-insp-gutter'); expect(g.querySelectorAll('li')).toHaveLength(1); expect(g.querySelector('li').style.top).toBe('25%');   // off-screen pins are not drawn
  expect(q('ws-frame').closest('.fea-view').className).toContain('has-gutter');   // the page moves over: the gutter never covers it
  const spy = jest.spyOn(w, 'postMessage');
  await act(async () => { q('ws-gutter-1').click(); }); expect(spy).toHaveBeenCalledWith({ t: 'feeless-inspect-go', sel: '#stage' }, '*');
});

test('🧰 a text pick is edited in place: Apply sends its new words for the $0 page tools; a 3D fix goes to the minds with the object', async () => {
  const { q, w, work } = await open();
  await say(w, { t: 'feeless-inspected', sel: 'body > header > h1', tag: 'h1', node: 'text', text: 'Solana pool turnover' });
  await act(async () => { q('ws-insp-edit-0').click(); });
  expect(q('ws-insp-editin-0').value).toBe('Solana pool turnover'); expect(q('ws-insp-apply-0').disabled).toBe(true);   // no change, nothing to send
  await type(q('ws-insp-editin-0'), 'Pool turnover, live');
  expect(q('ws-insp-apply-0').textContent).toContain('$0');
  await act(async () => { q('ws-insp-apply-0').click(); });
  const b = lastBuild(work);
  expect(b).toMatchObject({ job: 'w1', to: 'a', text: 'Change this text to "Pool turnover, live"' });
  expect(b.tools.region[0]).toMatchObject({ sel: 'body > header > h1', node: 'text', mode: 'fix', edit: 'Pool turnover, live', text: 'Solana pool turnover' });
  expect(q('ws-insp-card-0')).toBeNull();
  await say(w, { t: 'feeless-inspected', sel: '#stage', tag: 'canvas', node: 'three', three: { name: 'Hero cube', type: 'Mesh' } });
  await type(q('ws-insp-note-0'), 'make it spin slowly');
  await act(async () => { q('ws-insp-fix-0').click(); });
  expect(lastBuild(work).tools.region[0]).toMatchObject({ node: 'three', three: { name: 'Hero cube', type: 'Mesh' }, note: 'make it spin slowly', mode: 'fix' });
});

test('picks keep their kind: a text node and its element are two picks, two 3D objects on one canvas are two picks', () => {
  let ps = addPick([], { sel: '#hero', tag: 'div', text: 'Hi' });
  ps = addPick(ps, { sel: '#hero', tag: 'div', node: 'text', text: 'Hi' });
  ps = addPick(ps, { sel: '#c', tag: 'canvas', node: 'three', three: { name: 'A' } }); ps = addPick(ps, { sel: '#c', tag: 'canvas', node: 'three', three: { name: 'B' } });
  ps = addPick(ps, { sel: '#c', tag: 'canvas', node: 'three', three: { name: 'B' } });
  expect(ps.map(pickWord)).toEqual(['<div>', 'TEXT', '3D · A', '3D · B']);
  expect(addPick([], { sel: '#x', node: 'evil' })[0].node).toBeUndefined();
  expect(canEdit({ text: 'x', leaf: true })).toBe(true); expect(canEdit({ text: 'x', leaf: false })).toBe(false); expect(canEdit({ text: 'x', node: 'three' })).toBe(false);
});

test('🗂 the dashboard: folders and checks read from the folders; Inspect opens the folder with inspect on, Code opens its code', async () => {
  const folders = [{ id: 'w1', kind: 'build', name: 'Landing', at: 10 }, { id: 'w2', kind: 'build', name: 'Old', at: 1 }, { id: 'w3', kind: 'content', name: 'Post' }];
  const statics = [{ id: 'f1', ws: 'w1', n: 4, version: 2, at: 20, graded: 'right', unique: { like: 0.2, copy: false, nearest: 3, briefNew: true }, codeCheck: { passed: 5, total: 6, failed: ['links'] }, keep: { kept: 4, had: 4, from: 1, parts: 5, lost: [] } }];
  const list = psFolders(folders, statics); expect(list.map(f => f.id)).toEqual(['w1', 'w2']); expect(list[0]).toMatchObject({ top: 2, works: 1 });
  const ck = psChecks(statics[0]); expect(ck.map(c => [c.k, c.c.ok, c.c.val])).toEqual([['unique', true, '20% like'], ['clean', false, '5/6'], ['progress', true, '4/4 kept']]);
  expect(psChecks(null).every(c => c.c === null)).toBe(true);   // a check that never ran says so, never a score
  const work = jest.fn(async (_, b) => (b.op === 'ws_open' ? { doc: { id: b.text, versions: 2, preview: '<p>x</p>', by: 'Mind A', kitsUsed: [{ id: 'three', name: 'three.js', used: true }] } } : {}));
  const onOpen = jest.fn(); const onStudio = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<PsDash cat={{ id: 'c' }} work={work} folders={folders} statics={statics} onOpen={onOpen} onStudio={onStudio} tiles={<p>tiles</p>} />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(work).toHaveBeenCalledWith('c', { op: 'ws_open', text: 'w1' }); expect(q('psd-frame')).toBeTruthy(); expect(q('psd-vers').querySelectorAll('li')).toHaveLength(2);
  expect(q('psd-ck-clean').className).toContain('is-bad'); expect(q('psd-kits').textContent).toContain('three.js');
  await act(async () => { q('psd-inspect').click(); }); expect(onOpen).toHaveBeenLastCalledWith(expect.objectContaining({ id: 'w1' }), { inspect: true });
  await act(async () => { q('psd-code').click(); }); expect(onOpen).toHaveBeenLastCalledWith(expect.objectContaining({ id: 'w1' }), { view: 'code' });
  await act(async () => { q('psd-studio').click(); }); expect(onStudio).toHaveBeenCalledWith(expect.objectContaining({ id: 'w1' }));
  await act(async () => { q('psd-f-w2').click(); }); expect(work).toHaveBeenLastCalledWith('c', { op: 'ws_open', text: 'w2' });
});
