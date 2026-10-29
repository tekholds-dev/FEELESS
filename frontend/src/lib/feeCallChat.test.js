import { callMsg, callThread, callStats, capWord } from './feeCallChat';

const BUY = { id: 'b1', type: 'BUY', ts: 1793000000000, pairAddress: 'P1', marketCapUsd: 394498, detail: 'Bought 0.06 SOL of paws at live price — 🔮 FeeCat AI favored it (2 min ago): High buyers and top10 %, cap under $30K.; 🪟 over the chart (🔫 🧱 1.1% under its gun line — buying under resistance; waits f) · 🎯 HH/HL pullback · 🔮 FeeCat AI said YES' };
const SELL = { id: 's1', type: 'SELL', ts: 1793000000000 + 34 * 60_000, pairAddress: 'P1', pnlSol: -0.000559, entryMarketCapUsd: 394498, detail: 'Sold paws at -0.9% — thesis broken: sellers own the hour (49 sells vs 30 buys). P&L -0.0006 SOL on the price move (fees apart, paper, live price).' };

test('🐱 a call reads in her own words: what, why, tags — no bookkeeping tail', () => {
  const b = callMsg(BUY);
  expect(b).toMatchObject({ side: 'BUY', coin: 'paws', sol: 0.06, cap: 394498, at: 1793000000, pair: 'P1' });
  expect(b.why).toBe('High buyers and top10 %, cap under $30K');
  expect(b.tags).toEqual(['🪟 over the chart', '🎯 HH/HL pullback', '🔮 FeeCat AI said YES']);
  const s = callMsg(SELL);
  expect(s).toMatchObject({ side: 'SELL', coin: 'paws', move: -0.9, pnl: -0.000559 });
  expect(s.why).toBe('thesis broken — sellers own the hour (49 sells vs 30 buys)');
  expect(callMsg({ type: 'LEARN', detail: 'x' })).toBeNull();
});

test('🧵 each BUY is threaded to the SELL that closed it (result + hold), or marked still held; stats count her last 24h', () => {
  const t = callThread([SELL, BUY]);
  expect(t.map(m => m.id)).toEqual(['s1', 'b1']);
  expect(t[1].closed).toEqual({ pnl: -0.000559, move: -0.9, heldMin: 34 });
  const open = callThread([{ ...BUY, id: 'b2', pairAddress: 'P2' }], [{ pairAddress: 'P2' }]);
  expect(open[0].open).toBe(true);
  expect(callStats(t, 1793000000 + 3600)).toEqual({ calls: 2, closed: 1, won: 0, pnl: -0.000559 });
  expect(capWord(394498)).toBe('$394.5K'); expect(capWord(2.1e6)).toBe('$2.10M'); expect(capWord(null)).toBeNull();
});
