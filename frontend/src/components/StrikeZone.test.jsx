import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { StrikeZone } from './StrikeZone';
jest.mock('./StrikeGame', () => ({ StrikeGame: ({ mode, diff }) => <div data-testid="mock-game">{mode}:{diff}</div> }));

const HOME = { guns: { rifle: { name: 'FX-7 RIFLE', dmg: 24, rpm: 600, mag: 30, reload: 2.1, range: 120, spread: 0.012, recoil: 0.35, speed: 1, pellets: 1, level: 1 }, smg: { name: 'VIPER SMG', dmg: 16, rpm: 900, mag: 32, reload: 1.7, range: 55, spread: 0.024, recoil: 0.25, speed: 1.08, pellets: 1, level: 3 } },
  parts: { barrel: [{ id: 'std', name: 'STANDARD', level: 1, mod: {} }, { id: 'long', name: 'LONG', level: 5, mod: { range: 0.35 } }], optic: [{ id: 'iron', name: 'IRON', level: 1, mod: { zoom: 1.25 } }],
    mag: [{ id: 'std', name: 'STANDARD', level: 1, mod: {} }], stock: [{ id: 'std', name: 'STANDARD', level: 1, mod: {} }], skin: [{ id: 'green', name: 'FEELESS GREEN', level: 1, mod: {} }] },
  default: { gun: 'rifle', barrel: 'std', optic: 'iron', mag: 'std', stock: 'std', skin: 'green' }, xp: { kill: 100, head: 50, win: 400 },
  me: { level: 4, xp: 2000, into: 150, need: 1350, kills: 20, wins: 2, loadout: { gun: 'rifle', barrel: 'std', optic: 'iron', mag: 'std', stock: 'std', skin: 'green' }, unlocked: { guns: ['rifle', 'smg'], parts: { barrel: ['std'], optic: ['iron'], mag: ['std'], stock: ['std'], skin: ['green'] } } },
  board: [{ place: 1, name: 'Sicario', tag: 'FRT', level: 9, kills: 40, xp: 5200 }], rooms: [] };
const q = id => document.querySelector(`[data-testid="${id}"]`);

test('🎯 the Strike Zone lobby: level + XP, a gunsmith that locks parts by level and saves the build, PLAY opens the match', async () => {
  const posts = [];
  global.fetch = jest.fn((url, opt) => { if (opt?.method === 'POST') { const b = JSON.parse(opt.body); posts.push(b); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...HOME.me, loadout: b.loadout }) }); }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(HOME) }); });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StrikeZone addr="W" sess="S" family={{ id: 'f', tag: 'FRT' }} />); });
  await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  expect(q('strike-zone').textContent).toContain('STRIKE ZONE'); expect(q('strike-zone').textContent).toContain('[FRT] Sicario');
  expect(q('sz-barrel-long').disabled).toBe(true);                                       // LONG unlocks at level 5
  await act(async () => { q('sz-gun-smg').click(); });
  expect(posts[0]).toMatchObject({ address: 'W', session: 'S', loadout: { gun: 'smg' } });
  await act(async () => { q('sz-diff-hard').click(); }); await act(async () => { q('sz-play').click(); }); await act(async () => { await new Promise(r => setTimeout(r, 10)); });
  expect(q('mock-game').textContent).toBe('bots:hard');
  act(() => root.unmount());
});
