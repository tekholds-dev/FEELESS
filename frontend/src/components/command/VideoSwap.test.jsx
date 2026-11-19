import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { SwapFiled, VideoSwapPanel, VideoSwapTile } from './VideoSwap';

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('motion/react', () => { const R = require('react'); const passthrough = new Proxy({}, { get: (_, tag) => ({ initial, animate, transition, ...p }) => R.createElement(tag, p) }); return { motion: passthrough }; });
jest.mock('../../lib/chatSession', () => ({ agentAuth: () => ({ ownerId: 'o', session: 's' }), agentAuthQuery: () => 'ownerId=o&session=s' }));

// 🎭 Slice 4: the swap panel is wired — plan read → engine / clip / person / quality picked → the price on screen is the price sent → filed swap shows before | after
const ENG = [{ id: 'fal-h3-recast', label: 'MiniMax H3 Max · Recast', who: 'fal.ai', why: 'x', ready: true, env: 'FAL_KEY', res: ['768P', '1080P'], pick: true, sound: 'kept by the engine' },
  { id: 'or-aleph', label: 'Runway Aleph 2', who: 'OpenRouter', why: 'y', ready: false, env: 'OPENROUTER_API_KEY', res: [], runnerUp: true, sound: 'laid back from your clip' }];
const Q = (usd, make) => ({ usd, lines: [{ what: 'swap', usd: make ? usd - 0.03 : usd }, ...(make ? [{ what: 'portrait', usd: 0.03 }] : [])] });
const PLAN = (over = {}) => ({ engines: ENG, allowed: true, cap: 3, dayCap: 10, daySpent: 1, res: '768P', auto: 'fal-h3-recast', jobs: [],
  person: { mid: 'm1', url: '/api/cats/g/m1.png', prompt: 'a woman, red hair', source: 'character' },
  clips: [{ mid: 'mc', url: '/api/cats/media/g/mc.mp4', label: 'Dance', secs: 10, fit: { 'fal-h3-recast': '', 'or-aleph': '' },
    quote: { 'fal-h3-recast': { '768P': { char: Q(2.24), make: Q(2.27, true) }, '1080P': { char: Q(3.09), make: Q(3.12, true) } }, 'or-aleph': { std: { char: Q(2.8), make: Q(2.87, true) } } } }], ...over });

let root; let el;
beforeEach(() => { el = document.createElement('div'); document.body.appendChild(el); root = createRoot(el); });
afterEach(() => { act(() => root.unmount()); el.remove(); delete global.fetch; });
const flush = async () => { await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); }); };
const $ = id => el.querySelector(`[data-testid="${id}"]`) || document.body.querySelector(`[data-testid="${id}"]`);
const click = async id => { await act(async () => { $(id).dispatchEvent(new MouseEvent('click', { bubbles: true })); }); await flush(); };

function mockFetch(plan, onPost) {
  const calls = [];
  global.fetch = jest.fn(async (url, opts = {}) => { calls.push({ url, opts }); const body = opts.method === 'POST' ? (onPost ? onPost(JSON.parse(opts.body)) : plan) : plan; return { ok: true, json: async () => body }; });
  return calls;
}

test('reads the plan, prices the pick, and sends exactly the price on screen after a second press', async () => {
  const calls = mockFetch(PLAN(), b => PLAN({ jobs: [{ id: 'v1', label: 'MiniMax H3 Max · Recast', res: b.res, step: 'sending', quote: { usd: b.usd } }] }));
  await act(async () => { root.render(<VideoSwapPanel cat={{ id: 'g' }} row={{ id: 'w1' }} work={jest.fn()} />); }); await flush();
  expect(calls[0].url).toContain('/api/cats/g/vswap?ws=w1&ownerId=o&session=s');
  expect($('vsw-total').textContent).toBe('$2.24');
  expect($('vsw-eng-or-aleph').textContent).toContain('NEEDS OPENROUTER_API_KEY');
  await click('vsw-res-1080P'); expect($('vsw-total').textContent).toBe('$3.09');
  await click('vsw-res-768P');
  await click('vsw-go');   // first press only arms it
  expect(calls.filter(c => c.opts.method === 'POST')).toHaveLength(0); expect($('vsw-go').textContent).toContain('Confirm: spend $2.24 on fal.ai');
  await click('vsw-go');
  const post = calls.find(c => c.opts.method === 'POST'); const b = JSON.parse(post.opts.body);
  expect(post.url).toContain('/api/cats/g/vswap'); expect(b).toMatchObject({ ownerId: 'o', session: 's', ws: 'w1', clip: 'mc', engine: 'fal-h3-recast', res: '768P', person: 'character', usd: 2.24 });
  expect($('vsw-job-v1').textContent).toContain('MAKING');
});

test('a described person costs the portrait too, and nothing presses without words, a key or under the caps', async () => {
  mockFetch(PLAN({ person: null }));
  await act(async () => { root.render(<VideoSwapPanel cat={{ id: 'g' }} row={{ id: 'w1' }} work={jest.fn()} />); }); await flush();
  expect($('vsw-who-character').disabled).toBe(true); expect($('vsw-go').disabled).toBe(true); expect($('vsw-block').textContent).toContain('Say who');
  await act(async () => { const t = $('vsw-words'); const set = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set; set.call(t, 'a tall man, grey suit'); t.dispatchEvent(new Event('input', { bubbles: true })); }); await flush();
  expect($('vsw-total').textContent).toBe('$2.27'); expect($('vsw-go').disabled).toBe(false);
  await click('vsw-eng-or-aleph'); expect($('vsw-go').disabled).toBe(true); expect($('vsw-block').textContent).toContain('OPENROUTER_API_KEY');
});

test('only staff can press, and the day cap meter turns red when a swap would pass it', async () => {
  mockFetch(PLAN({ allowed: false }));
  await act(async () => { root.render(<VideoSwapPanel cat={{ id: 'g' }} row={{ id: 'w1' }} work={jest.fn()} />); }); await flush();
  expect($('vsw-go').disabled).toBe(true); expect($('vsw-block').textContent).toContain('staff');
  act(() => root.unmount()); root = createRoot(el); mockFetch(PLAN({ daySpent: 9 }));
  await act(async () => { root.render(<VideoSwapPanel cat={{ id: 'g' }} row={{ id: 'w1' }} work={jest.fn()} />); }); await flush();
  expect($('vsw-day').className).toContain('is-over'); expect($('vsw-go').disabled).toBe(true);
});

test('adding a clip needs the rights tick, then goes through the folder\'s own clip door', async () => {
  mockFetch(PLAN({ clips: [] })); const work = jest.fn(async () => ({ doc: { id: 'w1' } }));
  await act(async () => { root.render(<VideoSwapPanel cat={{ id: 'g' }} row={{ id: 'w1' }} work={work} setDoc={jest.fn()} />); }); await flush();
  const f = new File([new Uint8Array([0, 0, 0, 24, 102, 116, 121, 112])], 'dance.mp4', { type: 'video/mp4' });
  const input = $('vsw-file');
  await act(async () => { Object.defineProperty(input, 'files', { value: [f], configurable: true }); input.dispatchEvent(new Event('change', { bubbles: true })); }); await flush();
  expect(work).not.toHaveBeenCalled(); expect($('vsw-err').textContent).toContain('rights');
  await click('vsw-rights');
  await act(async () => { input.dispatchEvent(new Event('change', { bubbles: true })); }); await flush(); await flush();
  expect(work).toHaveBeenCalledWith('g', expect.objectContaining({ op: 'media_clip', job: 'w1', tools: expect.objectContaining({ rights: true, name: 'dance' }) }));
  expect(work.mock.calls[0][1].text).toMatch(/^data:video\/mp4;base64,/);
});

test('a filed swap shows the before and after side by side with its cost', () => {
  act(() => { root.render(<SwapFiled f={{ id: 'p1', n: 4, cost: 2.24, swap: { engine: 'MiniMax H3 Max · Recast', res: '768p', sound: 'kept by the engine', paid: 'FEELESS key', runnerUp: 'Runway Aleph 2', person: { source: 'made' },
    before: { url: '/api/cats/media/g/mb.mp4' }, after: { url: '/api/cats/media/g/ma.mp4' }, side: '/api/cats/media/g/ms.mp4', lines: [{ what: 'swap', usd: 2.24 }] } }} />); });
  expect($('vsw-filed-p1').textContent).toContain('$2.24'); expect($('vsw-filed-p1').textContent).toContain('no watermark');
  expect($('vsw-before').getAttribute('src')).toContain('mb.mp4'); expect($('vsw-after').getAttribute('src')).toContain('ma.mp4');
  act(() => { $('vsw-side-open').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect($('vsw-side').getAttribute('src')).toContain('ms.mp4');
  act(() => { root.render(<SwapFiled f={{ id: 'p2', n: 5, calls: [] }} />); }); expect(el.innerHTML).toBe('');   // a normal PoC shows nothing extra
});

test('the tile opens the panel as a sheet and Escape closes it', async () => {
  mockFetch(PLAN());
  await act(async () => { root.render(<VideoSwapTile cat={{ id: 'g' }} row={{ id: 'w1' }} work={jest.fn()} />); }); await click('vsw-open'); await flush();
  expect(document.body.querySelector('[data-testid="vsw"]')).toBeTruthy();
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(document.body.querySelector('[data-testid="vsw"]')).toBeNull();
});
