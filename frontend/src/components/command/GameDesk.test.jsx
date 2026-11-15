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
