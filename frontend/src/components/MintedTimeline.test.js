jest.mock('react-router-dom', () => ({}), { virtual: true });
// eslint-disable-next-line import/first
import { timelineOf } from './MintedTimeline';

test('minted timeline: real earns + trophies, newest first, editions kept, HQ grants left out', () => {
  const d = { badges: [{ id: 'q-trader', name: 'Trader', earned: true, tier: 'common', art: '/a' }, { id: 'q-vip', name: 'VIP', earned: true, granted: true, tier: 'rare' }],
    earnedAt: { 'q-trader': 100, 'q-vip': 300 }, editions: { 'q-trader': 7 }, trophies: [{ id: 't1', name: 'Week 1 #1', glyph: '🥇', rarity: 'mythic', at: 200 }] };
  const rows = timelineOf(d);
  expect(rows.map(r => r.key)).toEqual(['t1', 'q-trader']);
  expect(rows[1].edition).toBe(7);
});
