import { agentPool, PICK_LENSES, AGENT_LENS, pickRow } from './ArenaPrime';

test('the agents lens is creator-only and every row carries the KERNEL\'s decision — the same words as the Agents tab', () => {
  expect(PICK_LENSES.map(x => x[0])).not.toContain('agents');            // never in the public list — added only where an admin `call` exists
  expect(AGENT_LENS[0]).toBe('agents');
  const k = { status: 'READY', rank: 152, why: 'RUNNING — buyers in charge', trigger: 'ENTER', devil: [], size: 1, unknown: [], courier: true };
  const x = { mint: 'M', pair: 'P', symbol: 'GOOD', px: 1, nums: { liq: 60000, d5: 3, buy: 64, age: 8 }, why: { lean: 0.1, drivers: [] }, trigger: ['skip', 'paper'], devil: ['object', 'paper'], go: false, k };
  const r = pickRow(agentPool(x));
  expect(r.mint).toBe('M'); expect(r.pairAddress).toBe('P'); expect(r.liq).toBe(60000); expect(r.chg5m).toBe(3);
  expect(r.agent).toEqual(expect.objectContaining({ state: 'go', word: '🟢 READY', rank: 152, devil: 'NO OBJECTION' }));     // the paper desk's skip / object is not read
  const warn = agentPool({ ...x, go: true, k: { ...k, status: 'CONTENDING', rank: 90, devil: [['busted_read', 'STRONG_WARNING', 'its read is BOND RUN']] } });
  expect(warn.divisionLabel).toBe('⚠ DEVIL WARNS · rank 90'); expect(warn.agent.arg).toContain('BOND RUN');             // a concern is a warning, never "objected"
  expect(agentPool({ ...x, k: { ...k, status: 'TRACKING', devil: [['wall', 'HARD_VETO', 'collapsing']] } }).divisionLabel).toMatch(/^✕ BLOCKED/);
  expect(agentPool({ ...x, go: true, k: undefined }).agent.state).toBe('skip');                                           // a paper GO with no kernel decision is nothing
});
