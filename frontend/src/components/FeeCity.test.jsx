import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { FamilyWorld } from './FamilyWorld';
import { cityLayout, vitalsOf } from './FamilyCity3D';
import { feeSpot, markLine, FEE_PLOTS, FEE_W } from './FeeCapital';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const bor = (key, name, col, row, tier = 1) => ({ key, name, icon: '', col, row, tier, vibe: '' });
const VIEW = {
  boroughs: [bor('harbor', 'Pump Harbor', 0, 0), bor('heights', 'Raydium Heights', 1, 0, 1.4), bor('hills', 'Jupiter Hills', 2, 0), bor('fee', 'Fee City', 1, 2, 2.5)],
  bridges: [{ a: 'heights', b: 'hills', name: 'Oracle Span' }, { a: 'fee', b: 'heights', name: 'Golden Gate of Fee' }, { a: 'fee', b: 'harbor', name: 'Crown Bridge' }],
  blocks: [{ id: 'fee-0', b: 'fee', i: 0, owner: 'c1', tag: 'SIC', name: 'Sicario', power: 600, kind: 'family', mine: true }, { id: 'fee-1', b: 'fee', i: 1 },
    { id: 'heights-2', b: 'heights', i: 2 }, { id: 'hills-0', b: 'hills', i: 0 }],
  cities: [{ key: 'fee', name: 'FEE CITY', boroughs: ['fee'], vibe: 'Capital', held: 1, plots: 24 }, { key: 'heights', name: 'Raydium Heights', boroughs: ['heights', 'hills'], vibe: 'old money', held: 0, plots: 32 },
    { key: 'harbor', name: 'Pump Harbor', boroughs: ['harbor'], vibe: 'piers', held: 0, plots: 16 }],
  landmarks: [{ key: 'arena', name: '⚔ FUSE ARENA', lore: 'The stadium.', live: { raids: 2, minMp: 2000 } }, { key: 'house', name: '🏦 THE HOUSE', lore: 'The vault.', live: { mp: 7158 } }],
  ranked: [{ id: 'c1', tag: 'SIC', name: 'Sicario', power: 600, place: 1, rank: { name: 'Capo', div: 'III', tier: 3, pct: 10, next: 733 } }],
  rules: { fuseMinMp: 2000 }, season: { name: 'S', weather: 'clear' }, cpu: [], cartels: [], log: [], rate: { mp: 1, feecat: 1 }, raids: [],
};
const q = id => document.querySelector(`[data-testid="${id}"]`);
beforeEach(() => { global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('/chat/') ? { messages: [{ id: 'm1', username: 'don', text: 'gm', fam: { tag: 'SIC' } }] } : VIEW) })); });

test('pure: plots, landmarks and outer cities have places; vitals read the real numbers', () => {
  expect(FEE_PLOTS).toHaveLength(24); expect(feeSpot({ lm: 'arena' }).x).toBeGreaterThan(feeSpot({ i: 8 }).x);
  expect(markLine('arena', { raids: 2, minMp: 2000 })).toBe('2 raids live · MP battles ≥ 2,000 MP'); expect(markLine('mansion', null)).toMatch(/creator/);
  const lay = cityLayout(VIEW.boroughs.filter(b => ['heights', 'hills'].includes(b.key)));
  expect(lay.pos.hills.x - lay.pos.heights.x).toBe(384); expect(lay.W).toBeLessThan(FEE_W * 2);
  const v = vitalsOf(VIEW.blocks[0], VIEW);
  expect(v.title).toBe('[SIC] Sicario'); expect(v.groups.map(g => g[0])).toEqual(['WHO', 'STRENGTH', 'MONEY']);
  expect(v.groups[1][1].map(r => r[0])).toEqual(['POWER', 'RANK']); expect(v.groups[1][1][1][1]).toBe('Capo III · #1');
  expect(vitalsOf({ lm: 'house' }, VIEW).groups).toEqual([['LIVE', [['MP', '7,158']]]]);
});

test('Fee City is the landing: landmarks open their panel, a bridge gate crosses to another city, the street chat wears family tags, the ladder ranks', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FamilyWorld addr="A" sess="s" onEnter={() => {}} />); });
  expect(q('fee-capital')).not.toBeNull(); expect(q('city-fee').getAttribute('aria-selected')).toBe('true');
  await act(async () => { q('lm-arena').click(); });
  expect(q('mark-panel').textContent).toContain('never 4 vs 6'); expect(q('city-vitals').textContent).toContain('RAIDS');
  await act(async () => { q('lm-arena').click(); });
  expect(q('city-vitals')).toBeNull();                                                      // tap again = zoom back out
  expect(q('city-chat').textContent).toContain('SIC');
  await act(async () => { q('gate-heights').click(); });
  expect(q('fee-capital')).toBeNull(); expect(q('borough-heights')).not.toBeNull(); expect(q('borough-hills')).not.toBeNull();
  await act(async () => { q('gate-fee').click(); });
  expect(q('fee-capital')).not.toBeNull();
  await act(async () => { q('wl-ranked').click(); });
  expect(q('rank-ladder').textContent).toContain('Capo');
  await act(async () => { root.unmount(); });
});
