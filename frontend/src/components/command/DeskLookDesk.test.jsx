jest.mock('../perps/PerpsChart', () => ({ PerpsChart: () => null }));
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('./AtomPrint', () => ({ __esModule: true, default: () => null }));
import { CatWorkbench } from './CatWorkbench';
import { deskCommand, proofStatus, collectiveOf, paperOf, clipQueue, ecoOf, todayOf } from '../desk/deskData';
import { genPct, stamp, Md } from '../desk/DeskLook';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ signMessage: async () => 'SIG' }) }));
HTMLCanvasElement.prototype.getContext = () => null;   // jsdom has no canvas: the smoke draws nothing, everything else renders

// 🖥 Slice 34: the Desk look is the DEFAULT agent desk. Every piece of it runs on the agent's own state (op: state) and its Approve inbox,
// and every chat command goes through the very op its button calls.
const NOW = Date.now() / 1000;
const STATE = { live: true, providers: ['steel', 'reader'], cap: 0.05, credit: 9.2,
  chat: [{ by: 'you', text: 'hi', at: NOW - 120 }, { by: 'cats', text: 'hello **there**', cost: 0.0004, at: NOW - 100 }],
  task: { id: 't', text: 'research', status: 'working', cap: 0.05, cost: 0.013 },
  windows: [{ i: 0, model: 'qwen/qwen3-32b', status: 'working', provider: 'steel', url: 'https://kalshi.com', bubble: 'reading the YES ladder', steps: [{ action: 'open', thought: 'open Kalshi' }], cost: 0.008 },
    { i: 1, model: 'x/opus', status: 'human', provider: 'reader', url: 'https://site/login', bubble: '✋ needs you', human: { why: 'a sign-in' }, steps: [], cost: 0.005 }],
  pocFolders: [{ id: 'c1', n: 14, topic: 'Sneaker drop', at: NOW - 600, status: 'approve', ws: 'ws1', clips: [{ status: 'ready', url: '/a.mp4' }, { status: 'rendering' }],
    review: { verdict: 'pass', agree: true, by: { ossy: { score: 82, verdict: 'pass' }, g4: { score: 74, verdict: 'pass' } } } }],
  poeFolders: [{ id: 'e1', n: 3, topic: 'Logo job', at: NOW - 900, bid: 120, status: 'open' }],
  parked: [{ text: 'find the cheapest flight', why: 'a sign-in', at: NOW - 50 }] };
const WAIT = [{ id: 'ap1', state: 'waiting', what: 'Redo PoC #14', ref: 'c1' }];

function mount(extraState = {}) {
  const calls = [];
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b);
    const j = b.op === 'approvals' ? { approvals: WAIT } : b.op === 'approve' ? { approvals: [], row: { id: b.text, state: 'ran' } } : { ...STATE, ...extraState };
    return { ok: true, json: async () => j }; };
  localStorage.setItem('feeless-paper-owner', 'browser-1'); localStorage.removeItem('feeless.deskLook');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  return { calls, el, root };
}
const type = async (el, t) => { const inp = el.querySelector('[data-testid="cwb-input"]'); await act(async () => { Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set.call(inp, t); inp.dispatchEvent(new Event('input', { bubbles: true })); }); };
const send = async (el, t) => { await type(el, t); await act(async () => { el.querySelector('[data-testid="cwb-input"]').closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); }); };
const CAT = { id: 'g1', name: 'Happy', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } };

test('🖥 the Desk look is the default: bar, rail, widgets, two monitors, vitals, cabinet and chat — on real state, with timestamps', async () => {
  const { el, root, calls } = mount();
  await act(async () => { root.render(<CatWorkbench cat={CAT} />); });
  expect(el.querySelector('[data-testid="cwb-desk"]')).not.toBeNull(); expect(el.querySelector('[data-testid="cat-workbench"]')).toBeNull();
  ['dkl-widgets', 'dkl-monitors', 'dkl-vitals', 'dkl-cab', 'dkl-chat', 'dkl-bg', 'dkl-pulse'].forEach(t => expect(el.querySelector(`[data-testid="${t}"]`)).not.toBeNull());
  expect(el.querySelector('[data-testid="cwb-win-0"]').textContent).toContain('STEEL');   // the same live windows as the classic desk, on the monitors
  expect(el.querySelector('[data-testid="cwb-human"]').textContent).toContain('a sign-in');
  await act(async () => { el.querySelector('[data-testid="cwb-continue"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'continue', i: 1 });
  const times = [...el.querySelectorAll('[data-testid="dkl-msg-time"]')].map(t => t.textContent);
  expect(times).toHaveLength(2); times.forEach(t => expect(t).toMatch(/^\d\d:\d\d$|\d\d:\d\d$/));   // 🕐 every message has its time
  const chat = el.querySelector('[data-testid="cwb-chat"]'); expect(chat.textContent).toContain('hello there'); expect(el.textContent).not.toContain('**');   // markdown, never raw ** (chat or cabinet)
  // widgets: the Collective's real scores, the clip queue, PoEco's bid; the waiting approve lights PoEco
  expect(el.querySelector('[data-testid="dkl-wd-collective"]').textContent).toMatch(/OSSY.*82.*G4.*74/);
  expect(el.querySelector('[data-testid="dkl-wd-clips"]').textContent).toMatch(/1\s*ready · 1 making/);
  expect(el.querySelector('[data-testid="dkl-wd-eco"]').textContent).toContain('1 to approve');
  // nothing goes missing: parked asks resume, the who-to-ask picker, the gear's $ cap
  await act(async () => { el.querySelector('[data-testid="cwb-resume-0"]').disabled = false; });
  expect(el.querySelector('[data-testid="cwb-parked"]').textContent).toContain('cheapest flight');
  await act(async () => { el.querySelector('[data-testid="cwb-gear"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cwb-cap-0.25"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'cap', cap: 0.25 });
  await act(async () => { root.unmount(); }); el.remove();
});

test('💬 chat commands run through the same ops as the buttons: /poc, approve 1, /stop pow, a plain ask to one mind', async () => {
  const { el, root, calls } = mount({ task: { id: 't', status: 'done' }, windows: STATE.windows.map(w => ({ ...w, status: 'idle', human: null })) });
  await act(async () => { root.render(<CatWorkbench cat={CAT} />); });
  await send(el, '/poc a sneaker drop');
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'file a poc a sneaker drop', to: 'both' });
  await send(el, 'approve 1');
  expect(calls.at(-1)).toMatchObject({ op: 'approve', text: 'ap1', job: 'yes' });   // the very call the Approve button makes
  expect(el.querySelector('[data-testid="dkl-said"]').textContent).toContain('Approved: Redo PoC #14');
  await send(el, '/stop pow');
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'stop PoW' });   // the ✕ on a running PoW sends exactly this
  await act(async () => { el.querySelector('[data-testid="cwb-to-1"]').click(); });
  await send(el, 'only you');
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'only you', to: '1' });
  await act(async () => { root.unmount(); }); el.remove();
});

test('⚙ Settings › Classic desktop brings the old desk back, saved; Desk look returns to it', async () => {
  const { el, root } = mount();
  await act(async () => { root.render(<CatWorkbench cat={CAT} />); });
  await act(async () => { el.querySelector('[data-testid="cwb-gear"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cwb-look-classic"]').click(); });
  expect(el.querySelector('[data-testid="cat-workbench"]')).not.toBeNull(); expect(JSON.parse(localStorage.getItem('feeless.deskLook')).classic).toBe(true);
  if (!el.querySelector('[data-testid="cwb-look-desk"]')) await act(async () => { el.querySelector('[data-testid="cwb-gear"]').click(); });
  await act(async () => { el.querySelector('[data-testid="cwb-look-desk"]').click(); });
  expect(el.querySelector('[data-testid="cwb-desk"]')).not.toBeNull();
  await act(async () => { root.unmount(); }); el.remove();
});

test('📊 desk data is real or empty, never made up', () => {
  expect(proofStatus(null)).toEqual([]); expect(collectiveOf({})).toBeNull(); expect(paperOf({})).toEqual([]);
  const st = proofStatus(STATE, WAIT);
  expect(st[0]).toMatchObject({ k: 'poc', label: 'PoC', n: 14, waiting: true, next: 'waits for your approve' });
  expect(st[1]).toMatchObject({ k: 'poe', cost: null });   // no cost filed → none shown (never $0)
  expect(collectiveOf(STATE)).toMatchObject({ verdict: 'pass', agree: true, by: [{ k: 'OSSY', score: 82, pass: true }, { k: 'G4', score: 74, pass: true }] });
  expect(clipQueue(STATE)).toEqual({ ready: 1, making: 1, posted: 0, folders: 1 });
  expect(ecoOf(STATE, WAIT)).toMatchObject({ n: 1, open: 1, bidsUsd: 120, wait: 1 });
  expect(todayOf({ pocFolders: [{ at: NOW, status: 'closed', review: { verdict: 'pass' } }] })).toEqual({ n: 1, won: 1, open: 0 });
  expect(deskCommand('hello')).toBeNull();
  expect(deskCommand('approve 2', { approvals: WAIT })).toEqual({ kind: 'say', text: 'There are 1 waiting: say approve 1 to 1.' });
  expect(deskCommand('reject', { approvals: WAIT })).toMatchObject({ kind: 'decide', id: 'ap1', yes: false });
  expect(deskCommand('/image a green horizon')).toEqual({ kind: 'media', media: 'image', prompt: 'a green horizon' });
  expect(deskCommand('/open pob')).toEqual({ kind: 'open', win: 'bids' });
});

test('🕐 timestamps, 🎨 honest generation %, and markdown that never sets HTML', () => {
  const now = new Date(2026, 10, 20, 15, 0).getTime();
  expect(stamp(new Date(2026, 10, 20, 9, 5).getTime() / 1000, now)).toBe('09:05');
  expect(stamp(new Date(2026, 10, 19, 23, 1).getTime() / 1000, now)).toBe('Nov 19 23:01');
  expect(stamp(0, now)).toBe('');
  expect(genPct({ status: 'running', kind: 'image', at: 100 }, 100)).toBe(0);
  expect(genPct({ status: 'running', kind: 'image', at: 1 }, 10000)).toBe(95);   // never a fake 100% before the server says done
  expect(genPct({ status: 'done' })).toBe(100);
  const el = document.createElement('div'); const root = createRoot(el);
  act(() => { root.render(<Md text={'<img src=x onerror=alert(1)> `code` [ok](https://x.y) [bad](javascript:alert(1))'} />); });
  expect(el.querySelector('img')).toBeNull(); expect(el.querySelector('code').textContent).toBe('code');
  expect([...el.querySelectorAll('a')].map(a => a.getAttribute('href'))).toEqual(['https://x.y']);
  act(() => root.unmount());
});

test('🗂 owner 2026-11-21: "All folders" on the Desk look opens the OG desktop exactly as it was (wall, folders, print, count, widgets); one folder popped out keeps the Desk glass', async () => {
  const { el, root } = mount();
  await act(async () => { root.render(<CatWorkbench cat={CAT} />); });
  await act(async () => { el.querySelector('[data-testid="dkl-rail-folders"]').click(); });
  const og = document.querySelector('[data-testid="cwb-pop"]');
  expect(og).not.toBeNull(); expect(og.className).not.toContain('is-dl'); expect(og.className).not.toContain('is-over'); expect(og.dataset.og).toBe('on');
  expect(document.body.classList.contains('dsk-over')).toBe(false);   // the OG desktop covers the page, like it always did
  expect(og.querySelector('.dsk-icons')).not.toBeNull(); expect(og.querySelectorAll('.dsk-icons button').length).toBeGreaterThan(5);   // every folder
  expect(og.querySelector('[data-testid="dsk-widgets"]')).not.toBeNull();   // its widgets
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(document.querySelector('[data-testid="cwb-pop"]')).toBeNull();
  await act(async () => { el.querySelector('[data-testid="dkl-rail-stash"]').click(); });   // one folder over the desk: its window only, in the Desk glass
  const one = document.querySelector('[data-testid="cwb-pop"]'); expect(one.className).toContain('is-over'); expect(one.className).toContain('is-dl');
  expect(one.querySelector('.dsk-icons')).toBeNull(); expect(document.body.classList.contains('dsk-over')).toBe(true);
  await act(async () => { root.unmount(); }); el.remove();
});

test('⚙ owner 2026-11-21: every control in the desk settings panel works — click → saved → used (chat look, theme, animations, way, cursor, $ cap, job, Browse / Forms)', async () => {
  const { el, root, calls } = mount({ task: null, windows: [], job: 'agent', tools: { browse: true, forms: true }, toolkits: { agent: ['browse', 'forms'], researcher: ['browse', 'notes'] } });
  localStorage.removeItem('feeless.chatStyle.g1'); localStorage.removeItem('feeless:ai-cursor');
  await act(async () => { root.render(<CatWorkbench cat={CAT} />); });
  const q = t => document.querySelector(`[data-testid="${t}"]`); const click = async t => { await act(async () => { q(t).click(); }); };
  await click('cwb-gear');
  const panel = q('cwb-settings');
  const seen = panel.cloneNode(true); seen.querySelectorAll('[hidden]').forEach(n => n.remove());   // a real 3D icon keeps its symbol hidden for copy / search
  expect(seen.textContent).not.toMatch(/\p{Extended_Pictographic}/u);   // words + drawn glyphs, never a bare emoji beside line icons
  expect(panel.querySelector('input[type="checkbox"], select')).toBeNull();   // switches and segments, never a native checkbox / select
  expect(q('cwb-job-agent').textContent).toBe('General helper');   // never the raw "agent" id
  const saved = () => JSON.parse(localStorage.getItem('feeless.chatStyle.g1') || '{}');
  for (const s of ['classic', 'bubbles', 'feed', 'clean']) { await click(`chs-${s}`); expect(saved().style).toBe(s); expect(q('cwb-chat').dataset.style).toBe(s); }
  await click('chs-agent'); expect(q('chs-stage')).not.toBeNull(); expect(q('cwb-chat').hidden).toBe(true); await click('chs-clean');
  await click('chs-theme-day'); expect(saved().theme).toBe('day'); expect(q('cwb-chat').dataset.theme).toBe('day');
  await click('chs-motion'); expect(saved().motion).toBe(false); expect(q('chs-motion').getAttribute('aria-checked')).toBe('false'); expect(q('cwb-chat').dataset.motion).toBe('off');
  await click('cwb-way-jobs'); expect(calls.find(c => c.op === 'mode')).toMatchObject({ op: 'mode', job: 'jobs' });
  await click('cwb-cur-paw'); expect(localStorage.getItem('feeless:ai-cursor')).toBe('paw'); expect(q('cwb-cur-paw').getAttribute('aria-checked')).toBe('true');
  await click('cwb-cap-1'); expect(calls.at(-1)).toMatchObject({ op: 'cap', cap: 1 });
  await click('cwb-job-researcher'); expect(calls.at(-1)).toMatchObject({ op: 'tools', job: 'researcher' });
  expect(q('cwb-tool-browse').getAttribute('aria-checked')).toBe('true');
  await click('cwb-tool-browse'); expect(calls.at(-1)).toMatchObject({ op: 'tools', tools: { browse: false, forms: true } });   // the engine refuses a blocked tool (backend: test_desk_settings_engine)
  await act(async () => { root.unmount(); }); el.remove();
});
