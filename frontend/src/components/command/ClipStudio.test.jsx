import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ClipStudio from './ClipStudio';
import { beats, captionAt, editedWords, filterClips, fullLook, fxAt, groupWords, moveSlot, pops, sig, twinOf } from '../../lib/clipLook';

// 🎨🗓 Slice 29: the clip studio — grid, week (+ its chat), editor. Every button here is proven to send the call the backend saves and renders
// from (backend/tests/test_slice29_clip_studio.py proves the saving, the render and the undo).
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const $ = (el, id) => el.querySelector(`[data-testid="${id}"]`);
const file = (id, fm) => [{ piece: 'video', format: fm, url: `/m/${id}${fm}.mp4` }, { piece: 'image', format: fm, url: `/m/${id}${fm}.jpg` }];
const clip = (id, n, both, extra = {}) => ({ id, n, at: 100 + n, studio: { hook: `Hook ${n}`, files: ['story', 'feed', 'wide'].flatMap(fm => file(id, fm)), look: fullLook({ cap: { hot: ['green', 'pink', 'cyan'][n % 3] } }),
  looks: [{ v: 1, at: 1, by: 'code', why: 'starting look', look: fullLook({ cap: { hot: ['green', 'pink', 'cyan'][n % 3] } }), files: [] }],
  clip: { run: 'r1', from: 'ohara_iphone', rank: n, s: 7, e: 37, dur: 30, both }, ...extra }, ...(extra.posted ? { posted: extra.posted } : {}) });
const CLIPS = [clip('a', 1, 9), clip('b', 2, 6, { slot: 'Tue', slotTime: '12:00' }), clip('c', 3, 4)];
const PLAN = { cur: 2, versions: [{ v: 1, by: 'owner', why: 'your week', slots: [], at: 1 }, { v: 2, by: 'minds', why: 'Agent plans it: two strong days', at: 2, cost: 0.002, slots: [{ job: 'b', day: 'Tue', time: '12:00', plats: ['instagram'], why: 'NASA trend' }] }],
  chat: [{ by: 'owner', text: 'make Tuesday funnier', at: 1 }, { by: 'mind', mind: 'ossy', text: 'Added word pops.', at: 2, v: 2, looks: ['b'], cost: 0.002 }] };
const KIT = { fonts: { bold: 'Bold sans', impact: 'Impact', condensed: 'Condensed heavy', rounded: 'Rounded', serif: 'Serif', chalk: 'Chalk' }, presetLooks: { classic: fullLook({}), hype: fullLook({ cap: { font: 'impact', hot: 'yellow' }, tr: 'zoom', fx: { punch: true } }) } };
const WORDS = [{ i: 0, w: "I've", s: 0.1, e: 0.3 }, { i: 1, w: 'wanted', s: 0.35, e: 0.6 }, { i: 2, w: 'to', s: 0.65, e: 0.7 }, { i: 3, w: 'explore.', s: 0.75, e: 1.2 }, { i: 4, w: 'Submersible', s: 4.0, e: 4.6 }];

test('pure: filters, the week, the uniqueness check and the caption timing match the renderer', () => {
  expect(filterClips(CLIPS).map(f => f.id)).toEqual(['a', 'b', 'c']); expect(filterClips(CLIPS, { status: 'planned' }).map(f => f.id)).toEqual(['b']);
  expect(filterClips(CLIPS, { min: 6 }).map(f => f.id)).toEqual(['a', 'b']); expect(filterClips(CLIPS, { sort: 'new' })[0].id).toBe('c');
  const w = moveSlot([{ job: 'b', day: 'Tue', time: '12:00', plats: ['x'] }], 'a', 'Mon'); expect(w.map(s => [s.job, s.day])).toEqual([['a', 'Mon'], ['b', 'Tue']]);
  expect(moveSlot(w, 'b', 'Fri').find(s => s.job === 'b')).toMatchObject({ day: 'Fri', time: '12:00', plats: ['x'] }); expect(moveSlot(w, 'a', '')).toHaveLength(1);
  expect(sig({ cap: { hot: 'pink' }, edit: { w: { 1: 'x' } } })).toBe(sig({ cap: { hot: 'pink' } })); expect(twinOf(CLIPS[1].studio.look, CLIPS, 'a').id).toBe('b'); expect(twinOf(CLIPS[1].studio.look, CLIPS, 'b')).toBeNull();
  const ews = editedWords(WORDS, { edit: { w: { 2: '' }, off: 0.1 } }); expect(ews.map(x => x.w)).toEqual(["I've", 'wanted', 'explore.', 'Submersible']); expect(ews[0].s).toBeCloseTo(0.2);
  const g = groupWords(ews, 2); expect(g.map(x => x.map(y => y.w))).toEqual([["I've", 'wanted'], ['explore.'], ['Submersible']]);
  expect(captionAt(g, 0.5)).toMatchObject({ hot: 1 }); expect(captionAt(g, 3)).toBeNull();
  expect(pops(ews, 10)).toEqual([[0.85, 'EXPLORE'], [4.1, 'SUBMERSIBLE']]); expect(beats(ews, 10)).toEqual([0, 4.1]);
  const fx = fxAt({ tr: 'zoom', fx: { punch: true, pop: true } }, 4.2, [0, 4.1], [[4.1, 'SUBMERSIBLE']], 10); expect(fx.zoom).toBeGreaterThan(1.12); expect(fx.hit).toBe('zoom'); expect(fx.pop).toBe('SUBMERSIBLE');
});

function mount(api, view) {
  try { localStorage.setItem('feeless.clipStudioView', view); } catch { /* jsdom */ }
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const onPocs = jest.fn(); const onPlan = jest.fn(); const onOpen = jest.fn();
  return { el, root, onPocs, onPlan, onOpen, render: async (p = {}) => act(async () => root.render(<ClipStudio cat={{ id: 'c' }} clips={CLIPS} plan={PLAN} kit={KIT} api={api} onPocs={onPocs} onPlan={onPlan} onOpen={onOpen}
    runs={[{ id: 'r1', converted: { url: '/api/cats/vid/v0' }, links: [{ kind: 'upload', exp: Date.now() / 1000 + 9e5 }] }]} {...p} />)) };
}

test('the grid: tiles by source with score, hook and status, quick filters, hover-play, Edit and Approve', async () => {
  const api = jest.fn(async () => ({})); const m = mount(api, 'grid'); await m.render();
  expect(m.el.querySelectorAll('.cst-tile')).toHaveLength(3); expect($(m.el, 'cst-tile-a').textContent).toContain('Hook 1'); expect($(m.el, 'cst-tile-a').textContent).toContain('9');
  expect($(m.el, 'cst-tile-b').textContent).toContain('planned · Tue 12:00'); expect($(m.el, 'cst-tile-a').textContent).toContain('to approve');
  const play = jest.fn(() => Promise.resolve()); window.HTMLMediaElement.prototype.play = play; window.HTMLMediaElement.prototype.pause = jest.fn();
  await act(async () => $(m.el, 'cst-tile-a').dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))); expect(play).toHaveBeenCalled();
  await act(async () => $(m.el, 'cst-f-planned').click()); expect(m.el.querySelectorAll('.cst-tile')).toHaveLength(1);
  await act(async () => $(m.el, 'cst-f-all').click()); await act(async () => $(m.el, 'cst-open-a').click()); expect(m.onOpen).toHaveBeenCalledWith(CLIPS[0]);
  await act(async () => $(m.el, 'cst-edit-c').click()); expect($(m.el, 'cse-c')).not.toBeNull();   // Edit opens that clip in the editor
  act(() => m.root.unmount()); m.el.remove();
});

test('the week: agent plans it, a slot edit is saved as the plan, the chat sends and its undo goes to the version before', async () => {
  const api = jest.fn(async (path, body) => ({ plan: PLAN, pocFolders: CLIPS, path, body })); const m = mount(api, 'week'); await m.render();
  expect($(m.el, 'cst-drop-Tue').textContent).toContain('Hook 2'); expect($(m.el, 'cst-drop-Tue').textContent).toContain('NASA trend'); expect($(m.el, 'cst-drop-tray').textContent).toContain('Hook 1');
  await act(async () => $(m.el, 'cst-agent').click()); expect(api).toHaveBeenCalledWith('/plan/agent', {}); expect(m.onPlan).toHaveBeenCalledWith(PLAN);
  expect($(m.el, 'cst-save').disabled).toBe(true);
  await act(async () => $(m.el, 'cst-plat-b-tiktok').click()); expect($(m.el, 'cst-save').disabled).toBe(false);
  await act(async () => $(m.el, 'cst-save').click());
  expect(api).toHaveBeenCalledWith('/plan', { slots: [expect.objectContaining({ job: 'b', day: 'Tue', plats: ['instagram', 'tiktok'] })] });
  const inp = $(m.el, 'cst-chat-in'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, 'move the best one to Friday'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => $(m.el, 'cst-chat-send').click()); expect(api).toHaveBeenCalledWith('/plan/chat', { text: 'move the best one to Friday' });
  await act(async () => $(m.el, 'cst-chat-undo-2').click()); expect(api).toHaveBeenCalledWith('/plan/undo', { v: 1 });
  await act(async () => $(m.el, 'cst-versions').click()); expect($(m.el, 'cst-ver-list').textContent).toContain('two strong days');
  act(() => m.root.unmount()); m.el.remove();
});

test('the editor: words load, a preset or a word edit renders through ffmpeg, a twin look is blocked, the minds can pick, undo goes back', async () => {
  const api = jest.fn(async (path, body) => (path.startsWith('/words') ? { words: WORDS, dur: 30 } : { pocFolders: CLIPS, path, body })); const m = mount(api, 'edit'); await m.render();
  expect(api).toHaveBeenCalledWith('/words?job=a'); expect($(m.el, 'cse-words').textContent).toContain('Submersible');
  expect($(m.el, 'cse-render').disabled).toBe(true);   // nothing changed yet
  await act(async () => $(m.el, 'cse-hot-cyan').click());   // = clip b's look → blocked
  expect($(m.el, 'cse-uniq').textContent).toContain('Same look as PoC #2'); expect($(m.el, 'cse-render').disabled).toBe(true);
  await act(async () => $(m.el, 'cse-pre-hype').click()); expect($(m.el, 'cse-uniq').textContent).toContain('No other clip');
  await act(async () => $(m.el, 'cse-w-1').click()); const wi = $(m.el, 'cse-wi-1'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(wi, 'WANTED'); wi.dispatchEvent(new Event('input', { bubbles: true })); wi.dispatchEvent(new FocusEvent('blur')); });
  await act(async () => { wi.blur(); });
  await act(async () => $(m.el, 'cse-fx-shake').click()); await act(async () => $(m.el, 'cse-tr-glitch').click());
  await act(async () => $(m.el, 'cse-render').click());
  const call = api.mock.calls.find(c => c[0] === '/look'); expect(call[1].job).toBe('a');
  expect(call[1].look).toMatchObject({ cap: { font: 'impact', hot: 'yellow' }, tr: 'glitch', fx: { punch: true, shake: true } });
  await act(async () => $(m.el, 'cse-mind').click()); expect(api).toHaveBeenCalledWith('/look/mind', { job: 'a', ask: '' });
  act(() => m.root.unmount()); m.el.remove();
});
