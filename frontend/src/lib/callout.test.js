import { calloutPost, readCallout, calloutLive, xWord } from './callout';

test('📣 a callout post round-trips and reads its live P&L', () => {
  const t = calloutPost({ chainId: 'solana', pairAddress: 'Pool1111111111111111111111', marketCap: 52000, baseToken: { symbol: 'CATE' } }, 'dev locked, buyers 70%');
  const c = readCallout(t);
  expect(c).toMatchObject({ chain: 'solana', pair: 'Pool1111111111111111111111', mc: 52000, sym: 'CATE', why: 'dev locked, buyers 70%' });
  expect(calloutLive(52000, 104000)).toMatchObject({ x: 2, tone: 'up' }); expect(calloutLive(52000, 104000).pct).toBeCloseTo(100);
  expect(calloutLive(100, 50).tone).toBe('down'); expect(calloutLive(0, 5).x).toBe(null);
  expect(xWord(2.345)).toBe('2.3×'); expect(readCallout('gm')).toBe(null);
});

test('📍 chat callouts publish per pool once, and a pin snaps to its candle', () => {
  const { publishCallouts, callsFor } = require('./callout'); const { pinPlace } = require('../components/terminal/ChartCallPins');
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:callouts', on);
  const msgs = [{ id: 1, ts: '2026-10-16T22:00:00Z', username: 'roy', text: '📣 callout:solana:Pool1111111111111111111111@50000|DN huge' }, { id: 2, text: 'gm' }];
  publishCallouts(msgs); publishCallouts(msgs);
  expect(seen.length).toBe(1); expect(callsFor('Pool1111111111111111111111')[0]).toMatchObject({ who: 'roy', cap: 50000, text: 'huge', action: 'CALL' });
  window.removeEventListener('feeless:callouts', on);
  expect(pinPlace({ at: 125 }, 60)).toBe(120); expect(pinPlace({}, 60)).toBe(null);
});
