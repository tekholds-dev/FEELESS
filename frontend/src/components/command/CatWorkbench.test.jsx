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
  expect(calls[0]).toEqual({ ownerId: 'browser-1', session: '', op: 'state' });
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

test('🔑 a window sign-in is a small card → the credentials drawer opens with the site filled in; saved sealed; rows show the site only until 👁', async () => {
  const calls = [];
  const LOGIN = { ...STATE, logins: [{ site: 'x.com', user: 'me@mail.com', at: 1 }],
    windows: [{ i: 0, model: 'm/a', status: 'human', provider: 'steel', url: 'https://www.dropbox.com/login', human: { kind: 'login', site: 'dropbox.com', why: 'log in to dropbox.com' }, steps: [] }] };
  global.fetch = async (u, o) => { const b = JSON.parse(o.body); calls.push(b);
    return { ok: true, json: async () => (b.op === 'reveal' ? { password: 'Sup3r!pw' } : b.op === 'save_login' ? { ok: true, logins: [...LOGIN.logins, { site: 'dropbox.com', user: b.user }] } : LOGIN) }; };
  Element.prototype.scrollIntoView = () => {};
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatWorkbench cat={{ id: 'g1', brainsCfg: { kind: 'general', brains: ['m/a'], credit: 1 } }} />); });
  const card = el.querySelector('[data-testid="cwb-login"]');
  expect(card.textContent).toContain('dropbox.com needs a sign-in'); expect(card.querySelector('input')).toBeNull();   // no form inside the window
  const vault = el.querySelector('[data-testid="cwb-vault"]');
  expect(vault.textContent).toContain('x.com'); expect(vault.textContent).not.toContain('me@mail.com');                 // site name only
  expect(el.querySelector('[data-testid="cwb-signup"]')).toBeNull();
  await act(async () => { card.querySelector('[data-testid="cwb-login-go"]').click(); });
  expect(vault.open).toBe(true); expect(el.querySelector('[data-testid="cwb-cred-site"]').value).toBe('dropbox.com');
  expect(el.querySelector('[data-testid="cwb-signup"]').getAttribute('href')).toBe('https://dropbox.com');
  el.querySelector('[data-testid="cwb-login-user"]').value = 'me@drop.com'; el.querySelector('[data-testid="cwb-login-pass"]').value = 'Dr0p!pw';
  await act(async () => { el.querySelector('[data-testid="cwb-cred-add"]').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(calls.find(c => c.op === 'save_login')).toMatchObject({ text: 'dropbox.com', user: 'me@drop.com', secret: 'Dr0p!pw' });
  expect(el.querySelector('[data-testid="cwb-login-pass"]').value).toBe('');                                            // the form forgets it
  await act(async () => { el.querySelector('[data-testid="cwb-reveal-x.com"]').click(); });
  expect(el.querySelector('[data-testid="cwb-cred-x.com"]').textContent).toContain('Sup3r!pw');
  await act(async () => { el.querySelector('[data-testid="cwb-reveal-x.com"]').click(); });
  expect(el.querySelector('[data-testid="cwb-cred-x.com"]').textContent).not.toContain('Sup3r!pw');
  await act(async () => root.unmount()); el.remove();
});

test('☁ the cloud drawer: off until a deposit; then NEW, the space left, the 5 newest, every file, and 3 bigger sign-ups that fill the credentials drawer', async () => {
  const { CloudDrawer } = await import('./CatWorkbench');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CloudDrawer cat={{ id: 'g1' }} storage={{ files: [], used: 0, quota: 1024 ** 3, cloud: null }} />); });
  expect(el.querySelector('[data-testid="cwb-cloud-off"]').textContent).toContain('first real deposit');
  const files = Array.from({ length: 6 }, (_, i) => ({ id: `f${i}`, name: `pic${i}.png`, mime: i === 5 ? 'video/mp4' : 'image/png', size: 2 * 1024 ** 2, at: i, url: `/x/f${i}.png` }));
  const asked = [];
  await act(async () => { root.render(<CloudDrawer cat={{ id: 'g1' }} storage={{ files, used: 12 * 1024 ** 2, quota: 1024 ** 3, cloud: { pool: 'feeless', label: 'FEELESS server', quota: 1024 ** 3, startedAt: Date.now() / 1000 - 60 } }} onSignUp={s => asked.push(s)} />); });
  expect(el.querySelector('[data-testid="cwb-cloud-new"]').textContent).toContain('FEELESS server');
  expect(el.querySelector('[data-testid="cwb-cloud-left"]').textContent).toBe('1012.0 MB left');
  expect(el.querySelectorAll('[data-testid="cwb-cloud-latest"] a').length).toBe(5); expect(el.querySelector('[data-testid="cwb-cloud-latest"] video')).not.toBeNull();   // newest first: the clip
  expect(el.querySelectorAll('[data-testid="cwb-cloud-files"] li').length).toBe(6);
  await act(async () => { el.querySelector('[data-testid="cwb-bigger-mega.io"]').click(); });
  expect(asked).toEqual(['mega.io']);
  await act(async () => root.unmount()); el.remove();
});
