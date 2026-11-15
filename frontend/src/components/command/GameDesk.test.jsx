import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { GameDesk, webDoc } from './GameDesk';

const T = [{ id: 'fivem', name: 'FiveM · GTA V RP', what: 'w', drop: 'd' }, { id: 'gtasa_vita', name: 'GTA SA · PS Vita port', what: 'w', drop: 'd' }];
const P = { id: 'p1', name: 'chain', target: 'fivem', files: { 'client.lua': "print('a')" }, bins: {}, chat: [], checks: [{ file: 'client.lua', ok: true, msg: 'blocks and brackets balance' }, { file: 'INSTALL.md', ok: false, msg: 'no INSTALL.md yet' }] };

test('🎮 the Game desk starts a project, asks the chosen mind, shows the check, and switches tabs', async () => {
  const calls = []; let proj = null;
  const work = jest.fn(async (_id, b) => { calls.push(b); if (b.op === 'gdesk_get') return { targets: T, modes: [], projects: proj ? [proj] : [], project: proj, minds: ['sonnet', 'qwen'], style: [] };
    if (b.op === 'gdesk_new') { proj = { ...P, target: b.job }; return { project: proj, projects: [proj] }; }
    if (b.op === 'gdesk_ask') return { project: { ...proj, chat: [{ by: 'Mind B', model: 'qwen', text: 'Added a menu', files: ['menu.lua'], at: 1 }] }, say: 'Added a menu', model: 'qwen' };
    return {}; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<GameDesk cat={{ id: 'c1' }} work={work} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('gd-start')).not.toBeNull();
  await act(async () => { q('gd-target-gtasa_vita').click(); });
  await act(async () => { q('gd-make').click(); });
  expect(calls.find(c => c.op === 'gdesk_new').job).toBe('gtasa_vita');
  expect(q('gd-checks').textContent).toMatch(/1\/2 pass/);
  await act(async () => { q('gd-mind-1').click(); q('gd-quick-faster-cars').click(); });
  expect(q('gd-ask').value).toMatch(/handling\.cfg/);
  await act(async () => { q('gd-go').click(); });
  const ask = calls.find(c => c.op === 'gdesk_ask'); expect(ask.i).toBe(1); expect(ask.job).toBe('build'); expect(ask.tools.id).toBe('p1');
  expect(q('gd-chat').textContent).toMatch(/Added a menu/); expect(q('gd-chat').textContent).toMatch(/menu\.lua/);
  await act(async () => { q('gd-tab-files').click(); });
  expect(q('gd-code').value).toBe("print('a')");
  await act(async () => { root.unmount(); });
});

test('▶ a web game inlines its own scripts and styles, never outside ones', () => {
  const html = webDoc({ 'index.html': '<link rel="stylesheet" href="s.css"><script src="./g.js"></script><script src="https://cdn.x/y.js"></script>', 'g.js': 'go()', 's.css': 'b{}' });
  expect(html).toContain('<script>go()</script>'); expect(html).toContain('<style>b{}</style>'); expect(html).toContain('https://cdn.x/y.js');
  expect(webDoc({})).toBe('');
});

test('🎮 the real-server test reads a pasted console, a fix fills the Studio, a typed ask survives a tab switch, Undo and Share ask first', async () => {
  const calls = []; const proj = { ...P, name: 'my garage', files: { 'server.lua': 'x', 'fxmanifest.lua': 'y' } };
  const work = jest.fn(async (_id, b) => { calls.push(b);
    if (b.op === 'gdesk_get') return { targets: T, modes: [], projects: [proj], project: proj, minds: ['sonnet'], style: [], undo: 2 };
    if (b.op === 'gdesk_console') return { console: { name: 'my_garage', started: true, ok: false, verdict: 'It started, but 1 problem came from it.', rows: [{ kind: 'start', file: '', line: 0, msg: 'Started resource my_garage' }, { kind: 'error', file: 'server.lua', line: 12, msg: "attempt to index a nil value (global 'Config')", known: true }] } };
    if (b.op === 'gdesk_undo') return { project: proj, undo: 1 };
    if (b.op === 'gdesk_lab') return { platforms: [{ id: 'fivem', name: 'FiveM', what: 'w', tools: [], steps: ['a'] }], log: [], checks: {}, stats: { sessions: 0, bugs: 0, ship: 0 } };
    return { project: proj }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<GameDesk cat={{ id: 'c1' }} work={work} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  const type = async (node, v) => { await act(async () => { Object.getOwnPropertyDescriptor(Object.getPrototypeOf(node), 'value').set.call(node, v); node.dispatchEvent(new Event('input', { bubbles: true })); }); };
  await type(q('gd-ask'), 'a half typed ask');
  await act(async () => { q('gd-tab-files').click(); }); await act(async () => { q('gd-tab-studio').click(); });
  expect(q('gd-ask').value).toBe('a half typed ask');
  expect(q('gd-undo').textContent).toMatch(/Undo · 2/);
  await act(async () => { q('gd-undo').click(); });
  expect(calls.at(-1).op).toBe('gdesk_undo'); expect(q('gd-undo').textContent).toMatch(/Undo · 1/);
  window.confirm = jest.fn(() => false);
  await act(async () => { q('gd-share').click(); });
  expect(window.confirm).toHaveBeenCalled(); expect(calls.some(c => c.op === 'gdesk_share')).toBe(false);
  window.confirm = jest.fn(() => true);
  await act(async () => { q('gd-share').click(); });
  expect(calls.find(c => c.op === 'gdesk_share').tools.mine).toBe(true);
  await act(async () => { q('gd-tab-test').click(); });
  expect(q('gd-srv').textContent).toMatch(/ensure my_garage/);
  await type(q('gd-srv-log'), "[ script:my_garage] SCRIPT ERROR: @my_garage/server.lua:12: attempt to index a nil value (global 'Config')");
  await act(async () => { q('gd-srv-read').click(); });
  expect(q('gd-srv-out').textContent).toMatch(/server\.lua:12/);
  await act(async () => { q('gd-srv-fix').click(); });
  expect(q('gd-mode-fix').getAttribute('aria-selected')).toBe('true');
  expect(q('gd-ask').value).toMatch(/server\.lua:12/); expect(q('gd-log').value).toMatch(/SCRIPT ERROR/);
  await act(async () => { root.unmount(); });
});
