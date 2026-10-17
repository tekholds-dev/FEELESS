import { calloutPost, readCallout, calloutLive, xWord } from './callout';

test('📣 a callout post round-trips and reads its live P&L', () => {
  const t = calloutPost({ chainId: 'solana', pairAddress: 'Pool1111111111111111111111', marketCap: 52000, baseToken: { symbol: 'CATE' } }, 'dev locked, buyers 70%');
  const c = readCallout(t);
  expect(c).toMatchObject({ chain: 'solana', pair: 'Pool1111111111111111111111', mc: 52000, sym: 'CATE', why: 'dev locked, buyers 70%' });
  expect(calloutLive(52000, 104000)).toMatchObject({ x: 2, tone: 'up' }); expect(calloutLive(52000, 104000).pct).toBeCloseTo(100);
  expect(calloutLive(100, 50).tone).toBe('down'); expect(calloutLive(0, 5).x).toBe(null);
  expect(xWord(2.345)).toBe('2.3×'); expect(readCallout('gm')).toBe(null);
});
