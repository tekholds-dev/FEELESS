import { scanFunnel, feeCalls } from './FeeLiveTab';
import { feePins } from '../../lib/feecatCalls';
import { laneSave, laneWord } from './FeeCatDesk';

test('her scan reads as a funnel with the top reasons', () => {
  const f = scanFunnel({ scanned: 9, passed: 2, rejections: { 'chasing (5m)': 4, liquidity: 2 }, top: [{ symbol: 'A' }] }, 1);
  expect(f).toMatchObject({ read: 9, passed: 2, held: 1 }); expect(f.reasons[0]).toMatchObject({ k: 'chasing (5m)', c: 4, w: 1 }); expect(f.next).toHaveLength(1);
});

test('only her BUY / SELL become calls and chart pins, with the paper note trimmed', () => {
  const ev = [{ id: 'a', type: 'BUY', ts: 2000, pairAddress: 'P', marketCapUsd: 50000, detail: 'Bought 0.1 SOL of X — 🤖 agents lane (paper).' }, { id: 'b', type: 'LEARN', ts: 3000, pairAddress: 'P', marketCapUsd: 1 }];
  expect(feeCalls(ev)).toHaveLength(1); expect(feeCalls(ev)[0].text).toBe('Bought 0.1 SOL of X — 🤖 agents lane');
  const pins = feePins(ev, 'P'); expect(pins).toHaveLength(1); expect(pins[0]).toMatchObject({ kind: 'feecat', who: 'Fee', cap: 50000, at: 2 });
  expect(feePins(ev, 'OTHER')).toEqual([]);
});

test('her agents lane: empty = follow the agents, numbers saved, words readable', () => {
  expect(laneSave({ mcMin: '20000', mcMax: '', poolMin: 'x' })).toEqual({ mcMin: 20000 });
  expect(laneWord(300000, '$')).toBe('$300K'); expect(laneWord(0.25, 'h')).toBe('15m'); expect(laneWord(null, '$')).toBe('—');
});
