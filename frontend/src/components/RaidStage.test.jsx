import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { RaidStage, raidOdds, lastFx } from './RaidStage';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const lot = (i, b, extra = {}) => ({ lot: i, b, lvl: 3, share: 0.2, def: null, shield: 0, ...extra });
const R = { id: 'r1', status: 'live', kind: 'family', a: { id: 'fa', tag: 'AAA' }, b: { id: 'fb', tag: 'BBB' }, round: 1, rounds: 2, turn: 'a', deadline: Date.now() / 1000 + 200,
  power: 3, hitters: [5, 4, 2], hurt: 0, stash: 10000, loot: 1200, actions: { hit: 'steal', sabotage: 'shut', scout: 'see', retreat: 'leave' },
  board: [lot(0, 'pizza', { def: 2 }), lot(6, 'bank', { def: 4, shield: 3 }), lot(12, 'casino', { down: true })],
  moves: [{ side: 'a', act: 'hit', lot: 6, win: true, word: '🔫 hit lot 7 (bank) — took 1,200 MP (55 %)' }] };
const q = (el, id) => el.querySelector(`[data-testid="${id}"]`);

test("pure: the engine's odds (unknown guards → null) and the move that just happened", () => {
  expect(raidOdds(R, R.board[0])).toBeCloseTo(17 / (17 + 1.4 * 2 + 1), 5); expect(raidOdds(R, R.board[2])).toBeNull();
  expect(raidOdds({ ...R, hurt: 9 }, R.board[1])).toBeCloseTo(1 / (1 + 1.4 * 7 + 1), 5);   // a beaten crew vs a guarded bank
  expect(lastFx(R)).toMatchObject({ kind: 'hit', lot: 6, win: true, n: 1 }); expect(lastFx({ moves: [] })).toBeNull();
});

test('the raid plays on their block: hotkeys pick a move, tapping a building strikes it, the last hit plays on that building', async () => {
  const send = jest.fn(); const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<RaidStage r={R} act={send} busy={false} />); });
  expect(q(el, 'rl-6').querySelector('.rds-fx.k-hit.is-win')).not.toBeNull();             // the coins fly off the bank
  expect(q(el, 'rl-6').querySelector('.rds-dome')).not.toBeNull(); expect(q(el, 'rl-12').querySelector('.rds-smoke')).not.toBeNull();
  expect(q(el, 'rl-1').disabled).toBe(true);                                                 // an empty lot is never a target
  expect(el.querySelector('.rds-banner').textContent).toContain('took 1,200 MP');
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: '2' })); });
  expect(q(el, 'mv-sabotage').className).toContain('active');
  await act(async () => { q(el, 'rl-0').click(); });
  expect(send).toHaveBeenLastCalledWith({ act: 'attack', raid: 'r1', kind: 'sabotage', lot: 0 }, expect.any(String));
  await act(async () => { q(el, 'mv-retreat').click(); });                                   // no building needed
  expect(send).toHaveBeenLastCalledWith({ act: 'attack', raid: 'r1', kind: 'retreat', lot: -1 }, expect.any(String));
  await act(async () => { root.render(<RaidStage r={{ ...R, status: 'done', end: 'bell', paid: 1800, downLots: [12] }} act={send} busy={false} />); });
  expect(q(el, 'raid-over').textContent).toContain('1,800 MP'); expect(q(el, 'mv-hit')).toBeNull();
  await act(async () => { root.unmount(); });
});
