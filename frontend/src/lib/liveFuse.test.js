import { liveFuseFrom, fuseLevels } from './liveFuse';

const snap = { tpl: 'degen', pairAddress: 'P1', mint: 'M1' };
const card = legs => ({ cfg: {}, cards: [{ tpl: 'degen', label: 'Blaze', cfgEff: { sl: 15, rideAt: 25, rideTrail: 15 }, legs }] });

test('a coin opened from a card follows the card: fresh entry after a rebuy, and the states in between', () => {
  const held = liveFuseFrom(card([{ pairAddress: 'P1', mint: 'M1', symbol: 'LOOT', entry: 0.0002 }]), snap);
  expect(held.state).toBe('held'); expect(held.fuse.entry).toBe(0.0002); expect(held.fuse.stop).toBeCloseTo(0.00017); expect(held.fuse.lock).toBeCloseTo(0.00025); expect(held.fuse.tpl).toBe('degen');
  const d = card([]); d.cards[0].rebuying = 'M1';
  expect(liveFuseFrom(d, snap).state).toBe('rebuying');                               // sold, sale landing
  const d2 = card([]); d2.cards[0].seatPick = { pairAddress: 'P1' };
  expect(liveFuseFrom(d2, snap).state).toBe('rebuying');                              // queued for its seat
  expect(liveFuseFrom(card([{ pairAddress: 'P1', mint: 'M1', entry: 0.0003, buying: true }]), snap).state).toBe('buying');
  expect(liveFuseFrom(card([]), snap).state).toBe('gone');
  expect(liveFuseFrom(card([]), { pairAddress: 'P1' }).state).toBe('none');           // not opened from a card
  expect(fuseLevels({ entry: 0 }, {}, 'x')).toBeNull();
});
