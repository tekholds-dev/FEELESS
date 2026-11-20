import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ClipStudio from './ClipStudio';
import ClipFarm from './ClipFarm';
import { CapLayer } from './ClipCaption';
import { emojiFor, frameAt, fullLook, hookKey, keyword, safeTop } from '../../lib/clipLook';

// 🎨 Slice 29 add-on: templates (saved looks per agent, defaults per format / platform / farm, one tap on a clip, its run or the week) and the
// modern captions. Every button is proven to send the call the backend saves and renders from (backend/tests/test_slice29_templates.py proves
// the saving, the per-format render, the minds' distinct picks and that every style stays inside the frame).
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
const sel = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
const pick = async (node, v) => act(async () => { sel.call(node, v); node.dispatchEvent(new Event('change', { bubbles: true })); });
const type = async (node, v) => act(async () => { set.call(node, v); node.dispatchEvent(new Event('input', { bubbles: true })); });
const file = (id, fm) => [{ piece: 'video', format: fm, url: `/m/${id}${fm}.mp4` }, { piece: 'image', format: fm, url: `/m/${id}${fm}.jpg` }];
const POP = fullLook({ cap: { style: 'pop', font: 'sf', hot: 'green', words: 4 }, tr: 'zoom' });
const clip = (id, n, extra = {}) => ({ id, n, at: 100 + n, studio: { hook: `Hook ${n}`, files: ['story', 'feed', 'wide'].flatMap(fm => file(id, fm)), look: fullLook({ cap: { hot: ['green', 'pink', 'cyan'][n % 3] } }),
  looks: [{ v: 1, at: 1, by: 'code', why: 'start', look: fullLook({}), files: [] }], clip: { run: 'r1', from: 'ohara', rank: n, s: 0, e: 30, dur: 30, both: 8 }, ...extra } });
const CLIPS = [clip('a', 1, { tpl: { id: 'b:pop', name: 'Pop highlight', by: 'minds', why: 'a fast hook' } }), clip('b', 2, { slot: 'Tue', slotTime: '12:00' }), clip('c', 3)];
const TPLS = { list: [
  { id: 'b:pop', name: 'Pop highlight', builtin: true, look: POP, fmts: ['story', 'feed', 'wide'], describe: 'Pop highlight captions · zoom', why: 'the said word pops' },
  { id: 'b:sweep', name: 'Karaoke sweep', builtin: true, look: fullLook({ cap: { style: 'sweep', font: 'avenir', hot: 'yellow' }, tr: 'fade' }), fmts: ['story', 'feed', 'wide'], describe: 'Karaoke sweep captions' },
  { id: 'b:classic', name: 'Classic', builtin: true, legacy: true, look: fullLook({}), fmts: ['story', 'feed', 'wide'] },
  { id: 't1', name: 'Late night', by: 'owner', look: fullLook({ cap: { style: 'lower', font: 'demi', hot: 'cyan' }, tr: 'cut' }), fmts: ['story'] }],
  defaults: { farm: 'minds' }, platFmt: { tiktok: 'story', instagram: 'story', youtube: 'story', x: 'wide' }, inForce: {} };
const WORDS = [{ i: 0, w: 'Seven', s: 0.1, e: 0.4 }, { i: 1, w: 'thousand', s: 0.45, e: 0.8 }, { i: 2, w: 'meters', s: 0.85, e: 1.2 }];

function mount(api, view, extra = {}) {
  try { localStorage.setItem('feeless.clipStudioView', view); } catch { /* jsdom */ }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onTemplates = jest.fn(); const onPocs = jest.fn();
  return { el, root, onTemplates, onPocs, render: async () => act(async () => root.render(<ClipStudio cat={{ id: 'c' }} clips={CLIPS} plan={{ versions: [], chat: [] }} kit={{}} templates={TPLS} api={api}
    onPocs={onPocs} onPlan={jest.fn()} onTemplates={onTemplates} onOpen={jest.fn()} runs={[{ id: 'r1', converted: { url: '/api/cats/vid/v0' }, links: [{ kind: 'upload', exp: Date.now() / 1000 + 9e5 }] }]} {...extra} />)) };
}

test('pure: keywords, emoji, the pop frames and the safe area match the renderer', () => {
  expect(keyword('4,000')).toBe(true); expect(keyword('the')).toBe(false); expect(emojiFor('money')).toBeTruthy();
  expect(frameAt('pop', 0.01, 0, 1).scale).toBeGreaterThan(1.1); expect(frameAt('pop', 0.5, 0, 1).scale).toBe(1); expect(frameAt('sweep', 0.5, 0, 1).frac).toBeLessThan(1);
  expect(hookKey('A seven-foot titanium sphere')).toBe('seven-foot');
  const face = safeTop({ pos: 'mid', safe: 'face' }, 0.5, 0.16); expect(Math.abs(face + 0.08 - 0.5)).toBeGreaterThan(0.1);   // moved off the face
  expect(safeTop({ pos: 'bottom', safe: 'ui' }, null, 0.16) + 0.16).toBeLessThanOrEqual(0.8);   // out of the bottom 20 % (platform buttons)
});

test('a modern caption: no slab, the said word pops in the accent, the emoji lands on a keyword', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const g = WORDS.map(x => ({ w: x.w, i: x.i }));
  await act(async () => root.render(<CapLayer cap={fullLook({ cap: { style: 'emoji' } }).cap} g={g} hot={1} scale={1.16} top={0.6} />));
  const cap = $(el, 'cse-cap'); expect(cap.className).toContain('is-m'); expect(cap.className).toContain('is-emoji');
  const hot = cap.querySelector('.is-hot'); expect(hot.textContent).toBe('THOUSAND'); expect(hot.style.getPropertyValue('--sc')).toBe('1.16'); expect(hot.dataset.emo).toBeTruthy();
  expect(cap.querySelector('.is-said').textContent).toBe('SEVEN');
  act(() => root.unmount()); el.remove();
});

test('the Templates tab: defaults save per farm / format / platform, one tap puts a template on a clip, its run or the week, delete is for yours only', async () => {
  const api = jest.fn(async (path, body) => ({ templates: TPLS, pocFolders: CLIPS, path, body })); const m = mount(api, 'tpl'); await m.render();
  expect(m.el.querySelectorAll('.cst-tpl-grid')[0].querySelectorAll('.cst-tpl')).toHaveLength(3);   // modern + yours; the old ones fold away
  expect($(m.el, 'cst-tpl-b:pop').textContent).toContain('1');   // in use on clip a
  expect($(m.el, 'cst-tpl-b:pop').querySelector('.cse-cap.is-m.is-pop')).not.toBeNull();   // its moving sample
  await pick($(m.el, 'cst-def-farm'), 'b:sweep'); expect(api).toHaveBeenCalledWith('/template/default', { key: 'farm', tpl: 'b:sweep' }); expect(m.onTemplates).toHaveBeenCalledWith(TPLS);
  await pick($(m.el, 'cst-def-wide'), 't1'); expect(api).toHaveBeenCalledWith('/template/default', { key: 'wide', tpl: 't1' });
  await pick($(m.el, 'cst-def-tiktok'), 'b:pop'); expect(api).toHaveBeenCalledWith('/template/default', { key: 'tiktok', tpl: 'b:pop' });
  await pick($(m.el, 'cst-tpl-clip'), 'c');
  await act(async () => $(m.el, 'cst-tpl-apply-b:sweep-clip').click()); expect(api).toHaveBeenCalledWith('/template/apply', { tpl: 'b:sweep', job: 'c' });
  await act(async () => $(m.el, 'cst-tpl-apply-t1-run').click()); expect(api).toHaveBeenCalledWith('/template/apply', { tpl: 't1', run: 'r1' });
  await act(async () => $(m.el, 'cst-tpl-apply-b:pop-week').click()); expect(api).toHaveBeenCalledWith('/template/apply', { tpl: 'b:pop', week: true });
  expect(m.onPocs).toHaveBeenCalledWith(CLIPS);
  expect($(m.el, 'cst-tpl-del-b:pop')).toBeNull(); await act(async () => $(m.el, 'cst-tpl-del-t1').click()); expect(api).toHaveBeenCalledWith('/template/delete', { id: 't1' });
  await act(async () => $(m.el, 'cst-tpl-minds-run').click()); expect(api).toHaveBeenCalledWith('/template/minds', { run: 'r1' });
  await type($(m.el, 'cst-tpl-ask'), 'finance numbers'); await act(async () => $(m.el, 'cst-tpl-design').click()); expect(api).toHaveBeenCalledWith('/template/mind', { ask: 'finance numbers' });
  act(() => m.root.unmount()); m.el.remove();
});

test('Edit on a template opens it in the editor; style, words and safe area change it; Save as template sends the look, Update keeps its id; the render names it', async () => {
  const api = jest.fn(async (path, body) => (path.startsWith('/words') ? { words: WORDS, dur: 30, face: 0.42 } : { templates: TPLS, pocFolders: CLIPS, id: 't9', path, body })); const m = mount(api, 'tpl'); await m.render();
  await act(async () => $(m.el, 'cst-tpl-edit-t1').click());
  expect($(m.el, 'cse-a')).not.toBeNull(); expect($(m.el, 'cse-pre-t1').className).toContain('is-on'); expect($(m.el, 'cse-tpl-name').value).toBe('Late night');
  await act(async () => $(m.el, 'cse-style-gradient').click()); await act(async () => $(m.el, 'cse-words-n-5').click()); await act(async () => $(m.el, 'cse-safe-ui').click());
  expect($(m.el, 'cse-stage').className).toContain('is-gradient');
  await act(async () => $(m.el, 'cse-tpl-update').click());
  const up = api.mock.calls.find(c => c[0] === '/template/save'); expect(up[1]).toMatchObject({ id: 't1', name: 'Late night', fmts: ['story'], look: { cap: { style: 'gradient', words: 5, safe: 'ui' } } });
  await type($(m.el, 'cse-tpl-name'), 'Money talk'); await act(async () => $(m.el, 'cse-tpl-fmt-wide').click()); await act(async () => $(m.el, 'cse-tpl-save').click());
  const nw = api.mock.calls.filter(c => c[0] === '/template/save')[1]; expect(nw[1].id).toBeUndefined(); expect(nw[1]).toMatchObject({ name: 'Money talk', fmts: ['story', 'wide'] });
  await act(async () => $(m.el, 'cse-pre-sweep').click()); await act(async () => $(m.el, 'cse-render').click());
  const look = api.mock.calls.find(c => c[0] === '/look'); expect(look[1]).toMatchObject({ job: 'a', tpl: 'b:sweep', look: { cap: { style: 'sweep' } } });
  act(() => m.root.unmount()); m.el.remove();
});

test('the tile names its template, who picked it and why', async () => {
  const m = mount(jest.fn(async () => ({})), 'grid'); await m.render();
  const chip = $(m.el, 'cst-tplchip-a'); expect(chip.textContent).toContain('Pop highlight'); expect(chip.className).toContain('is-minds'); expect(chip.textContent + chip.getAttribute('data-tip')).toContain('a fast hook');
  act(() => m.root.unmount()); m.el.remove();
});

test('the farm: clips come out in the picked template (upload or link), your default is preselected, the run card says each clip’s template', async () => {
  const RUN = { id: 'r1', name: 'Talk', status: 'done', steps: [], cands: [{ n: 1, s: 0, e: 30, first2: 'Seven thousand', minds: [] }], picks: [{ n: 1 }], clips: [],
    tpls: [{ n: 1, tpl: 'b:sweep', name: 'Karaoke sweep', by: 'minds', why: 'a slow build', fmts: { wide: 'Late night' } }], links: [] };
  const calls = []; global.fetch = jest.fn(async (url, opt) => { calls.push([String(url), opt]); return { ok: true, json: async () => ({ runs: [RUN], busy: false, templates: { ...TPLS, defaults: { farm: 't1' } } }) }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const P = { ...CLIPS[0], studio: { ...CLIPS[0].studio, clip: { ...CLIPS[0].studio.clip, n: 1 } } };   // its template was swapped after the run
  await act(async () => root.render(<ClipFarm cat={{ id: 'c' }} pocs={[P]} />));
  expect($(el, 'cfm-tpl').value).toBe('t1');   // the owner's saved default applies to every new run
  expect($(el, 'cfm-tpl-1').textContent).toContain('Pop highlight'); expect($(el, 'cfm-tpl-1').textContent).toContain('16:9 Late night'); expect($(el, 'cfm-tpl-1').textContent).toContain('was Karaoke sweep');
  await pick($(el, 'cfm-tpl'), 'minds');
  await act(async () => $(el, 'cfm-rights').click()); await type($(el, 'cfm-link'), 'https://example.com/a.mp4'); await act(async () => $(el, 'cfm-link-go').click());
  const link = calls.find(c => c[0].includes('/link')); expect(JSON.parse(link[1].body)).toMatchObject({ tpl: 'minds' });
  act(() => root.unmount()); el.remove();
});
