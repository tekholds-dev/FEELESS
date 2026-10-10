import { agentPool, PICK_LENSES, AGENT_LENS, pickRow } from './ArenaPrime';

test('the agents lens is creator-only and every row carries the four agents\' words', () => {
  expect(PICK_LENSES.map(x => x[0])).not.toContain('agents');            // never in the public list — added only where an admin `call` exists
  expect(AGENT_LENS[0]).toBe('agents');
  const x = { mint: 'M', pair: 'P', symbol: 'GOOD', px: 1, nums: { liq: 60000, d5: 3, buy: 64, age: 8 }, why: { lean: 2.5, drivers: [['buyers', 1, 'buyers in charge']] },
    trigger: ['enter', 'lean +2.5 ≥ bar 1.5'], devil: ['agree', 'no evidence against it'], go: true };
  const r = pickRow(agentPool(x));
  expect(r.mint).toBe('M'); expect(r.pairAddress).toBe('P'); expect(r.liq).toBe(60000); expect(r.chg5m).toBe(3);
  expect(r.agent).toEqual(expect.objectContaining({ go: true, call: 'enter', devil: 'agree', lean: 2.5, drivers: ['buyers in charge'] }));
  expect(agentPool({ ...x, go: false, devil: ['object', 'BOND RUN'] }).divisionLabel).toMatch(/^⚖ objected/);
});
