import { lossSplit, profitSplit, rungs } from './PaysFlow';
import { biggestLift, potBoard } from './AgentPot';

test('a profit pays seats first, the Collective only what is left, the rest compounds (pay_profit order)', () => {
  expect(profitSplit(30, 20)).toEqual({ seats: 30, keep: 20, compound: 50 });
  expect(profitSplit(90, 20)).toEqual({ seats: 90, keep: 10, compound: 0 });
  expect(profitSplit(0, 20)).toEqual({ seats: 0, keep: 20, compound: 80 });
});

test('a loss drains what compounded first, then stakes (pool_loss order)', () => {
  expect(lossSplit(70)).toEqual({ fromCompound: 70, fromStake: 30 });
  expect(lossSplit(150)).toEqual({ fromCompound: 100, fromStake: 0 });
});

test('the pot ladder marks the rung it is on and how full the next ones are', () => {
  const r = rungs({ potUsd: 25000, ladder: [{ pot: 0, top: 300, drip: 7 }, { pot: 10000, top: 500, drip: 3.5 }, { pot: 100000, top: 750, drip: 1.75 }] });
  expect(r.map(x => [x.top, x.open, x.now])).toEqual([[300, true, false], [500, true, true], [750, false, false]]);
  expect(r[2].fill).toBe(0.25);
});

test('its proofs join their real pot score, oldest first, and the biggest lift is named', () => {
  const d = { powFolders: [{ id: 'b', topic: 'later', at: 20 }, { id: 'a', topic: 'first', at: 10 }, { id: 'z', topic: 'unscored', at: 5 }], psFolders: [{ id: 'c', topic: 'site', at: 15 }] };
  const w = { a: { score: 108, top: 300, rank: 'D', parts: [] }, b: { score: 210, top: 300, rank: 'B', parts: [] }, c: { score: 90, top: 300, rank: 'D', parts: [] } };
  const rows = potBoard(d, w);
  expect(rows.map(r => [r.n, r.id, r.kind])).toEqual([[1, 'a', 'PoW'], [2, 'c', 'PoStatic'], [3, 'b', 'PoW']]);
  expect(rows[2].x).toBe(2.1); expect(rows[1].x).toBe(1);
  expect(biggestLift([{ key: 'r', label: 'Real build', weight: 30, value: 0.6 }, { key: 'u', label: 'Unique', weight: 10, value: 0 }, { key: 'n', label: 'New', weight: 10, value: null }]).label).toBe('Real build');
});
