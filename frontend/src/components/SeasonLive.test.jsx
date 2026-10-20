import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SeasonLive, rankMoves, clock } from './SeasonLive';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('rank moves are real events between two reads; the clock reads like a countdown', () => {
  const a = [{ address: 'A', rank: 1, handle: 'a', score: 10 }, { address: 'B', rank: 2, handle: 'b', score: 9 }];
  const b = [{ address: 'B', rank: 1, handle: 'b', score: 12 }, { address: 'A', rank: 2, handle: 'a', score: 10 }];
  const m = rankMoves(a, b, 100);
  expect(m.map(x => x.text)).toEqual(['@b climbed to #1 (12 pts)', '@a slipped to #2 (10 pts)']);
  expect(rankMoves(null, b, 1)).toEqual([]);
  expect(clock(3661)).toBe('01:01:01'); expect(clock(90061)).toBe('1d 01h 01m');
});

test('the hub shows the vitals, the race and the family feed', async () => {
  global.fetch = jest.fn(u => Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('crews') ? { events: [{ kind: 'paid', fam: 'SIC', text: '50 pts paid', at: Date.now() / 1000, id: 'x' }], vitals: { families: 3 } } : { cards: [], moves: [], past: [], endsAt: Date.now() / 1000 + 3600 }) }));
  const d = { endsIn: 7200, players: 9, me: { rank: 2, tier: 'Bronze' }, top: [{ address: 'A', rank: 1, handle: 'feeless', score: 445 }, { address: 'B', rank: 2, handle: 'x', score: 100 }] };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SeasonLive d={d} />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.textContent).toContain('@feeless'); expect(el.textContent).toContain('345 pts'); expect(el.textContent).toContain('#2 · Bronze');
  expect(el.textContent).toContain('[SIC] 50 pts paid');
});
