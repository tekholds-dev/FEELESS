import { liveOverlay, livePairs } from './agentLive';

const d = { card: { seats: [{ kind: 'agent', symbol: 'A', mint: 'MA', pair: 'PA', pct: 1 }, { kind: 'open' }] },
  office: { positions: [{ symbol: 'A', mint: 'MA', pair: 'PA', entry: 1, px: 1.01, pct: 1, usd: 0.101, peak: 3 }], seatBoard: [{ seat: 1, mint: 'MA', pct: 1 }, { seat: 2, empty: true }] } };

test('positions and seats are re-priced live against the entry snapshot', () => {
  expect(livePairs(d)).toEqual(['PA']);
  const out = liveOverlay(d, new Map([['PA', { price: 1.2, at: 5 }]]));
  expect(out.office.positions[0]).toMatchObject({ pct: 20, px: 1.2, peak: 20, liveAt: 5 });
  expect(out.office.positions[0].usd).toBeCloseTo(0.12, 4);
  expect(out.card.seats[0]).toMatchObject({ pct: 20, live: true }); expect(out.office.seatBoard[0].pct).toBe(20);
  expect(out.card.seats[1]).toEqual({ kind: 'open' });
});

test('no live price yet = the server snapshot stands', () => {
  expect(liveOverlay(d, new Map())).toBe(d);
  expect(liveOverlay(d, new Map([['OTHER', { price: 2 }]]))).toBe(d);
});
