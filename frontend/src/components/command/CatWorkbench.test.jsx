import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CatWorkbench } from './CatWorkbench';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const STATE = { live: true, providers: ['steel', 'reader'], cap: 0.05, credit: 9.2, chat: [{ by: 'you', text: 'hi' }, { by: 'cats', text: 'hello', cost: 0.0004 }],
  task: { id: 't', text: 'research', status: 'working', cap: 0.05, cost: 0.013 },
  windows: [{ i: 0, model: 'qwen/qwen3-32b', status: 'working', provider: 'steel', url: 'https://kalshi.com', bubble: 'reading the YES ladder', steps: [{ action: 'open', thought: 'open Kalshi' }], cost: 0.008 },
    { i: 1, model: 'x/opus', status: 'human', provider: 'reader', url: 'https://site/login', bubble: '✋ needs you', human: { why: 'a sign-in' }, steps: [], cost: 0.005 }] };

test('🧠🧠 two windows with their provider + bubble; a sign-in pauses one with ✋ continue; one chat; the $ cap; the ask is sent', async () => {
  const calls = [];
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b); return { ok: true, json: async () => (b.op === 'state' ? STATE : { ...STATE, task: { ...STATE.task, status: 'done', answer: 'YES at $0.31' }, windows: STATE.windows.map(w => ({ ...w, status: 'done' })) }) }; };
  localStorage.setItem('feeless-paper-owner', 'browser-1');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b', 'x/opus'], credit: 9.2 } }} />); });
  expect(calls[0]).toEqual({ ownerId: 'browser-1', op: 'state' });
  expect(el.querySelector('[data-testid="cwb-win-0"]').textContent).toContain('STEEL'); expect(el.querySelector('[data-testid="cwb-bubble"]').textContent).toContain('reading the YES ladder');
  expect(el.querySelector('[data-testid="cwb-human"]').textContent).toContain('a sign-in');
  expect(el.textContent).toContain('$0.0130 / $0.0500');
  await act(async () => { el.querySelector('[data-testid="cwb-continue"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'continue', i: 1 });
  expect(el.querySelector('[data-testid="cwb-answer"]').textContent).toContain('YES at $0.31');
  await act(async () => { el.querySelector('[data-testid="cwb-cap-0.25"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'cap', cap: 0.25 });
  const inp = el.querySelector('[data-testid="cwb-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'find best bids'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'find best bids', to: 'both' });
  await act(async () => { el.querySelector('[data-testid="cwb-to-1"]').click(); });
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'only you'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)).toMatchObject({ op: 'ask', text: 'only you', to: '1' });                       // one mind takes the whole task
  await act(async () => { root.unmount(); });
});

test('☁ the + puts an image in its storage, shows a chip + the storage meter, and the next ask carries it; non-images are refused here', async () => {
  const calls = []; const idle = { ...STATE, task: { ...STATE.task, status: 'done', answer: 'ok' }, windows: STATE.windows.map(w => ({ ...w, status: 'idle', human: null })) };
  const FILE = { id: 'a'.repeat(32), name: 'logo.png', mime: 'image/png', size: 2048, url: `/api/cats/g1/files/${'a'.repeat(32)}.png` };
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push([String(u), b]);
    return { ok: true, json: async () => (String(u).endsWith('/files') ? { file: FILE, used: 2048, quota: 1024 ** 3, ttlDays: 7 } : idle) }; };
  localStorage.setItem('feeless-paper-owner', 'browser-1');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['qwen/qwen3-32b'], credit: 2.5 } }} />); });
  const plus = el.querySelector('[data-testid="cwb-plus"]'); expect(plus.getAttribute('data-tip')).toContain('own storage');
  const input = el.querySelector('[data-testid="cwb-file-input"]');
  const put = async files => { Object.defineProperty(input, 'files', { configurable: true, value: files }); await act(async () => { input.dispatchEvent(new Event('change', { bubbles: true })); await new Promise(r => setTimeout(r, 30)); }); };
  await put([new File(['<html>'], 'x.html', { type: 'text/html' })]);
  expect(el.textContent).toContain('Images only'); expect(calls.some(([u]) => u.endsWith('/files'))).toBe(false);
  await put([new File([new Uint8Array([137, 80, 78, 71])], 'logo.png', { type: 'image/png' })]);
  const up = calls.find(([u]) => u.endsWith('/api/cats/g1/files'));
  expect(up[1]).toMatchObject({ ownerId: 'browser-1', name: 'logo.png' }); expect(up[1].dataUrl).toMatch(/^data:image\/png;base64,/);
  expect(el.querySelector('[data-testid="cwb-files"]').textContent).toContain('logo.png'); expect(el.querySelector('[data-testid="cwb-store"]').textContent).toContain('2 KB / 1.0 GB');
  const inp = el.querySelector('[data-testid="cwb-input"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, 'launch my coin on pump.fun with this logo'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { el.querySelector('[data-testid="cwb-send"]').click(); });
  expect(calls.at(-1)[1]).toMatchObject({ op: 'ask', text: 'launch my coin on pump.fun with this logo', files: [FILE.id] });
  expect(el.querySelector('[data-testid="cwb-files"]')).toBeNull();                       // sent: the chips clear
  act(() => root.unmount()); el.remove();
});
