import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamilyWorld, cardOf, blockTone, CrewDeck } from './FamilyWorld';

const VIEW = {
  boroughs: [{ key: 'harbor', name: 'Pump Harbor', icon: '⚓', col: 0, row: 0, tier: 1, vibe: 'piers' }],
  bridges: [], season: { name: '🎃 Haunted Trenches', weather: 'fog' }, boom: { word: 'ai', borough: 'harbor', mult: 1.25 },
  blocks: [{ id: 'harbor-0', b: 'harbor', i: 0, owner: 'c1', tag: 'SIC', name: 'Sicario', power: 50, kind: 'family', mine: true, home: true },
    { id: 'harbor-1', b: 'harbor', i: 1 }, { id: 'harbor-3', b: 'harbor', i: 3, owner: 'cpu-1', tag: 'RUG', name: 'Rugpull', kind: 'cpu', power: 900 }],
  cpu: [{ id: 'cpu-1', name: 'Rugpull', tag: 'RUG', level: 6, guards: 10, stash: 9000 }], cartels: [{ id: 'cartel-sniper-1', name: 'Block Zero Snipers', tag: 'SN1', role: 'sniper', icon: '🎯', members: 40, hits: 300, coins: 90, active7d: 12, level: 4 }],
  log: [], rate: { mp: 1000000, feecat: 10000 },
  me: { id: 'c1', bank: 5000, turf: [], pts: 12, metrics: {}, reach: { harbor: true }, prices: { 'harbor-1': 2400 }, moveMp: { harbor: 1500 }, hitters: [3],
    errands: [{ store: 'gas', name: '⛽ Fuel', how: 'tap', cd: 300, lvl: 1, ready: 0 }], challenges: [{ key: 'first-run', name: '🍕 First', metric: 'errands', need: 5, have: 5, recruit: { k: 'earner', lvl: 3 }, mp: 500, ready: true, done: false }],
    rewards: [{ key: 'rush', name: '⚡ Rush', what: 'x', cost: 4000 }], redeems: [] },
  raids: [],
};

const q = id => document.querySelector(`[data-testid="${id}"]`);
beforeEach(() => { global.fetch = jest.fn((url, o) => Promise.resolve({ ok: true, json: () => Promise.resolve(o?.method === 'POST' ? { ...VIEW, result: { mp: 120 } } : VIEW) })); });

test('recruits are playing cards and blocks have a tone', () => {
  expect(cardOf({ k: 'hitter', lvl: 1 })).toMatchObject({ suit: '♠', face: 'A', red: false });
  expect(cardOf({ k: 'earner', lvl: 10 })).toMatchObject({ face: 'K', red: true });
  expect(blockTone({ mine: true })).toBe('mine'); expect(blockTone({ kind: 'cpu', owner: 'x' })).toBe('cpu'); expect(blockTone({})).toBe('free');
  const el = document.createElement('div'); document.body.appendChild(el);
  act(() => { createRoot(el).render(<CrewDeck crew={[{ id: 1, k: 'spy', lvl: 4, xp: 0 }]} />); });
  expect(q('crew-deck').textContent).toContain('♦');
});

test('the city map opens a block, buys turf and runs a tap errand', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamilyWorld addr="A" sess="s" onEnter={() => {}} />); });
  expect(q('world-map')).not.toBeNull();
  const posted = w => global.fetch.mock.calls.some(c => c[1]?.method === 'POST' && c[1].body.includes(w));
  await act(async () => { q('blk-harbor-1').click(); });
  await act(async () => { q('blk-buy').click(); });
  expect(posted('"buy"')).toBe(true);
  await act(async () => { q('city-places').click(); }); await act(async () => { q('place-jobs').click(); });   // 📍 the lens tabs are places in the city now
  await act(async () => { q('job-go-gas').click(); });
  for (let i = 0; i < 6; i += 1) await act(async () => { q('job-tap-gas').click(); });
  expect(posted('"errand"')).toBe(true);
  await act(async () => { q('city-places').click(); }); await act(async () => { q('place-cartels').click(); });   // 📍 the lens tabs are places in the city now
  expect(q('cartel-cartel-sniper-1').textContent).toContain('Block Zero Snipers');
  await act(async () => { root.unmount(); });
});

test('💸 every building pop-out carries the Money Menu: 12 real doors, each opens its place in the city', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamilyWorld addr="A" sess="s" onEnter={() => {}} />); });
  await act(async () => { q('city-places').click(); }); await act(async () => { q('place-jobs').click(); });
  expect(q('money-menu').querySelectorAll('button')).toHaveLength(12);
  expect(q('money-jobs').className).toContain('active');
  await act(async () => { q('money-shop').click(); });
  expect(q('place-panel-shop')).not.toBeNull();
  await act(async () => { root.unmount(); });
});

test('📺 Pawn & Gold rents a billboard: the line goes to the server as a billboard act', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamilyWorld addr="A" sess="s" onEnter={() => {}} />); });
  await act(async () => { q('city-places').click(); }); await act(async () => { q('place-rewards').click(); });
  const inp = q('billboard-text'); const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, '$SIC runs the city'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { q('billboard-go').click(); });
  expect(global.fetch.mock.calls.some(c => c[1]?.method === 'POST' && c[1].body.includes('"billboard"') && c[1].body.includes('$SIC runs the city'))).toBe(true);
  await act(async () => { root.unmount(); });
});
