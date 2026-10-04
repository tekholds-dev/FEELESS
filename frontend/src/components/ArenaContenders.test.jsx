import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaContenders, liveRow } from './ArenaContenders';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./WarRoomHost', () => ({ openWarRoom: jest.fn() }));
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => null }));
jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map([['P1', { price: 2, h1: 40, m5: 3 }]]) }));
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const row = (o) => ({ mint: 'M1', pairAddress: 'P1', symbol: 'AAA', price: 1, liq: 90000, vol24h: 5e6, vol1h: 60000, chg24h: 12, chg1h: 20, score: 81, rank: 1, move: 'up', streak: 2, seat: 'next', parts: [{ part: 'volume', points: 30, why: '$5M today' }], ...o });

test('live prices override the league snapshot; runners are judged on the hour', () => {
  const live = new Map([['P1', { price: 2, h1: 40, m5: 3 }]]);
  expect(liveRow(row(), live, 'fresh')).toMatchObject({ price: 2, move: 40, moveLabel: '1H' });
  expect(liveRow(row(), live, 'popular')).toMatchObject({ price: 2, move: 12, moveLabel: '24H' });
  expect(liveRow(row(), new Map(), 'proven')).toMatchObject({ price: 1, move: 20 });
});

test('divisions are tabs; rows show rank, live price, seat and the cited score', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ divisions: [
    { key: 'popular', label: '🔥 Popular', rule: 'Most traded today', role: 'pool', rows: [row(), row({ mint: 'M2', pairAddress: 'P2', symbol: 'BBB', rank: 2, seat: 'card', move: 'new', streak: 0 })] },
    { key: 'fresh', label: '⚡ Fresh runners', rule: 'Under 12h', role: 'runner', rows: [row({ mint: 'M3', symbol: 'CCC', seat: '' })] },
    { key: 'deep', label: '🌊 Deepest', rule: 'x', role: 'pool', rows: [] }] }) }));
  const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<ArenaContenders />); }); await tick();
  expect(host.querySelectorAll('[role="tab"]').length).toBe(2);                       // an empty division is not shown
  const a = host.querySelector('[data-testid="cn-row-AAA"]');
  expect(a.textContent).toContain('$2'); expect(a.textContent).toContain('NEXT UP'); expect(a.textContent).toContain('🔥 ×2');
  expect(host.querySelector('[data-testid="cn-row-BBB"]').textContent).toContain('ON A CARD');
  act(() => host.querySelector('[data-testid="cn-tab-fresh"]').click()); await tick();
  expect(host.querySelector('[data-testid="cn-row-CCC"]').textContent).toContain('+40.0%');   // 1h live move on the runner tab
});
