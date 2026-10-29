import { scanFunnel } from './FeeLiveTab';
import { callThread } from '../../lib/feeCallChat';
import { feePins } from '../../lib/feecatCalls';
import { laneSave, laneWord } from './FeeCatDesk';

test('her scan reads as a funnel with the top reasons', () => {
  const f = scanFunnel({ scanned: 9, passed: 2, rejections: { 'chasing (5m)': 4, liquidity: 2 }, top: [{ symbol: 'A' }] }, 1);
  expect(f).toMatchObject({ read: 9, passed: 2, held: 1 }); expect(f.reasons[0]).toMatchObject({ k: 'chasing (5m)', c: 4, w: 1 }); expect(f.next).toHaveLength(1);
});

test('only her BUY / SELL become calls and chart pins, with the paper note trimmed', () => {
  const ev = [{ id: 'a', type: 'BUY', ts: 2000, pairAddress: 'P', marketCapUsd: 50000, detail: 'Bought 0.1 SOL of X — 🤖 agents lane (paper).' }, { id: 'b', type: 'LEARN', ts: 3000, pairAddress: 'P', marketCapUsd: 1 }];
  expect(callThread(ev)).toHaveLength(1); expect(callThread(ev)[0]).toMatchObject({ side: 'BUY', coin: 'X', sol: 0.1, why: '🤖 agents lane' });   // the chat (lib/feeCallChat)
  const pins = feePins(ev, 'P'); expect(pins).toHaveLength(1); expect(pins[0]).toMatchObject({ kind: 'feecat', who: 'Fee', cap: 50000, at: 2 });
  expect(feePins(ev, 'OTHER')).toEqual([]);
});

test('her agents lane: empty = follow the agents, numbers saved, words readable', () => {
  expect(laneSave({ mcMin: '20000', mcMax: '', poolMin: 'x' })).toEqual({ mcMin: 20000 });
  expect(laneWord(300000, '$')).toBe('$300K'); expect(laneWord(0.25, 'h')).toBe('15m'); expect(laneWord(null, '$')).toBe('—');
});

test('💬 public FeeCat: scan reasons + calls are chip rows, FeeCat AI\'s desk words become 🔮 bubbles (names never public)', () => {
  const { reasonChip, talkPins, tapeRow } = require('../../lib/feeTape');
  expect(reasonChip('🔫 🧱 1.4% under its gun line — buying under resistance')).toMatchObject({ icon: '🧱', label: 'under gun line' });
  expect(reasonChip('market cap band')).toMatchObject({ icon: '📏', label: 'cap band' });
  expect(reasonChip("older than the agents' max age")).toMatchObject({ icon: '⏳' });
  expect(reasonChip('weird reason here!!')).toMatchObject({ icon: '•', label: 'weird reason her' });
  const f = scanFunnel({ scanned: 9, passed: 2, rejections: { liquidity: 6 } }, 0);
  expect(f.reasons[0]).toMatchObject({ icon: '💧', label: 'thin pool', full: 'liquidity (6)' });
  const g = scanFunnel({ rejections: { '🔫 chart says SKIP': 2, '🔫 COMPRESSION — the models': 3, 'too new': 4 } }, 0);
  expect(g.reasons.map(r => [r.label, r.c])).toEqual([['chart skip', 5], ['too new', 4]]);   // two chart reasons = ONE chip, summed
  const talk = [{ pair: 'P', word: 'YES', why: 'graduated, buyers lead', at: 100, mc: 28000 }, { pair: 'P', word: 'skim', why: '', at: 200, mc: 41000 },
    { pair: 'Q', word: 'NO', at: 150, mc: 9000 }, { pair: 'P', word: 'HOLD', at: 300, mc: 0 }];
  const pins = talkPins(talk, 'P');
  expect(pins.map(p => [p.action, p.cap])).toEqual([['YES', 28000], ['SKIM', 41000]]);   // this coin only, a word + a cap
  expect(pins[0]).toMatchObject({ who: 'FeeCat AI', kind: 'talk', icon: '🔮', text: 'graduated, buyers lead' });
  expect(pins[1].text).toBe('said skim');
  expect(talkPins(talk, null)).toEqual([]);
  expect(tapeRow({ type: 'SELL', detail: 'Sold SQUADS at +18.3% — 🔮 FeeCat AI said exit. P&L +0.0181 SOL on the price move (fees apart, paper, live price).' })).toMatchObject({ coin: 'SQUADS', move: 18.3, ai: true, sol: null }); expect(tapeRow(null).coin).toBeNull();
  expect(tapeRow({ type: 'SELL', detail: 'Sold 1 at -0.3% — 🔮 FeeCat AI said exit. P&L -0.0002 SOL on the price move' })).toMatchObject({ coin: '1', sol: null, move: -0.3 });
  expect(tapeRow({ type: 'BUY', detail: 'Bought 0.06 SOL of AAPL at live price — 🔮 FeeCat AI favored it' })).toMatchObject({ coin: 'AAPL', sol: 0.06 });
  const { trailKey } = require('../terminal/ChartCallPins');
  expect(trailKey({ kind: 'talk', who: 'FeeCat AI' })).toBe('fcai');
});
