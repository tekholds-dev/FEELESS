import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { SplitFlow, sendRows, splitOf } from './SplitFlow';
import { BoostFolder } from './BoostFolder';
import { CollectiveOwner, topOptions } from './CollectiveOwner';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RULES = { deal: 'plans', skimPct: 20, potPct: 50, potPayDayPct: 5, weightMaxX: 2, boostBackPts: 5, ptsBase: 5, ptsPerUsd: 2, ptsMaxSend: 60, ptsPerDay: 10, boostFadeDays: 60, depositPct: 10, firstMinUsd: 50, txnSmallPct: 5, txnMidPct: 3, txnBigPct: 1, txnSmallUsd: 10, txnBigUsd: 100, boostMode: 'payout', plans: [{ plan: 'week', days: 7, backPct: 70, weightX: 1, roomX: 1 }, { plan: 'month', days: 30, backPct: 85, weightX: 2, roomX: 2 }, { plan: 'quarter', days: 90, backPct: 95, weightX: 3, roomX: 3 }, { plan: 'vault', days: null, backPct: 0, weightX: 6, roomX: 6 }] };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root }; };
const click = async n => act(async () => { n.dispatchEvent(new MouseEvent('click', { bubbles: true })); });

test('a plan says how much comes back, and the Vault says nothing does', () => {
  expect(splitOf(RULES, 10, 'month')).toMatchObject({ kept: 2, locked: 8, days: 30, backPct: 85 }); expect(splitOf(RULES, 10, 'month').back).toBeCloseTo(6.8); expect(splitOf(RULES, 10, 'month', 1).back).toBeCloseTo(7.2);
  expect(splitOf(RULES, 10, 'vault', 1)).toMatchObject({ back: 0, vault: true, house: 8 }); expect(splitOf({ ...RULES, boostMode: 'rank' }, 10, 'month', 1).backPct).toBe(85);
});
test('the calculator follows the plan and the fees, says short or ahead, and the Vault asks twice', async () => {
  const asked = []; globalThis.fetch = jest.fn(async u => { asked.push(String(u)); const plan = /plan=(\w+)/.exec(u)[1]; const rich = /feesDay=10000/.test(u); return { ok: true, json: async () => ({ sent: 10, plan, days: 30, back: 6.8, pot: rich ? 9 : 1.2, profit: rich ? 5.8 : -2, breakEven: rich ? 14 : null, capped: false, series: [{ day: 0, back: 0, pot: 0 }, { day: 30, back: 6.8, pot: rich ? 9 : 1.2 }] }) }; });
  const settle = () => act(async () => { await new Promise(r => setTimeout(r, 150)); });
  const { el, root } = await mount(<SplitFlow rules={RULES} />); await settle();
  expect(asked.at(-1)).toContain('usd=10&plan=month'); expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('not a promise'); expect(el.querySelector('[data-testid="split-flow-sum"]').textContent).toContain('SHORT BY');
  await click(el.querySelector('[data-testid="spf-fees-10000"]')); await settle(); expect(el.querySelector('[data-testid="split-flow-sum"]').textContent).toContain('AHEAD BY'); expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('day 14');
  await click(el.querySelector('[data-testid="plan-week"]')); await settle(); expect(asked.at(-1)).toContain('plan=week');
  await click(el.querySelector('[data-testid="plan-vault"]')); expect(el.querySelector('[data-testid="plan-vault"]').textContent).toContain('Tap again');
  await click(el.querySelector('[data-testid="plan-vault"]')); await settle(); expect(asked.at(-1)).toContain('plan=vault');
  await act(async () => root.unmount());
});
test('a rule the server changes moves the picture', async () => {
  const rows = sendRows(splitOf({ ...RULES, skimPct: 30 }, 10, 'month'));
  expect(rows[0]).toEqual(['Sent', 'Collective, right away', 3]); expect(rows.map(r => r[1])).toContain('Back to the agent');
  const vault = sendRows(splitOf(RULES, 10, 'vault')); expect(vault.map(r => r[1])).toEqual(['Collective, right away', 'Vault']);
});
const OWNER_VIEW = { cfg: { ...RULES, collectivePoolPct: 20, cutPerX: 1, walletCapPct: 10, fastPtsPerDay: 5, fastMaxDays: 30, depositPct: 10 }, defaults: { collectivePoolPct: 20, cutPerX: 1, walletCapPct: 10, fastPtsPerDay: 5, fastMaxDays: 30 }, bounds: { collectivePoolPct: [5, 80], cutPerX: [0.25, 10], walletCapPct: [1, 50], fastPtsPerDay: [0.25, 100], fastMaxDays: [1, 90] }, stake: { stakedUsd: 200, profitUsd: 50, paidUsd: 2, keepUsd: 17, compoundUsd: 31 }, pools: [{ id: 'p1', platform: 'meteora', pair: 'SOL-USDC', address: 'Addr11112222', on: true, profitUsd: 50 }], stakeAgents: [{ id: 'a', name: 'Happy', sentUsd: 200, x: 1.87, cutPct: 1.87, nowPct: 1.87, paidUsd: 2, pointsLeft: 372, fast: true }], totals: { usd: {}, in: { txn: 5, proofs: 200 }, agents: 1 }, chain: { short: [], tokens: {} }, site: { feesUsd: 75, movedUsd: 0, owedUsd: 15 }, held: [{ cat: 'c', id: 'h1', name: 'Nova', sym: 'WIF', review: { seats: [] } }], reviewed: 3 };
test('HQ shows the money, the pools and each cut, saves a dial, and profit needs a transaction', async () => {
  const call = jest.fn(async (u, o) => (o ? OWNER_VIEW : OWNER_VIEW));
  const { el, root } = await mount(<CollectiveOwner call={call} />);
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(q('cof-cover').textContent).toContain('FULLY COVERED'); expect(q('cof-withdrawals').textContent).toContain('OFF');
  expect(q('hq-kpi-stakedUsd').textContent).toContain('$200'); expect(q('hq-kpi-keepUsd').textContent).toContain('$17');
  expect(q('hq-live').textContent).toContain('THE LIVE FLOOR'); expect(q('hqf-agent-a')).toBeTruthy(); expect(q('hqf-tank-p1')).toBeTruthy(); expect(q('hq-needs')).toBeTruthy(); expect(q('hq-top')).toBeTruthy();
  await click(q('hq-view-agents')); expect(q('hq-agent-a').textContent).toContain('1.87%'); expect(q('hq-agent-a').textContent).toContain('FAST');
  await click(q('cof-clear-h1')); expect(JSON.parse(call.mock.calls.find(c => c[1])[1].body)).toEqual({ clear: { cat: 'c', id: 'h1' } }); call.mockClear();
  await click(q('hq-view-deal')); expect(q('cof-save').disabled).toBe(true); expect(q('hq-amt-profit')).toBeTruthy();
  await click(q('hq-view-build')); expect(q('hq-pool-p1').textContent).toContain('SOL-USDC'); expect(q('hq-range-note').textContent).toContain('not wired');
  await click(q('hq-pool-on-p1')); expect(JSON.parse(call.mock.calls.find(c => c[1])[1].body)).toEqual({ poolSet: { id: 'p1', on: false } });
  await act(async () => root.unmount());
});
test('the top options are the best payers of each kind, thin pools left out, and nothing with no pay', () => {
  const rows = [{ id: 'l1', kind: 'lend', per1k24: 0.2 }, { id: 'l2', kind: 'lend', per1k24: 0.3 }, { id: 'l3', kind: 'lend', per1k24: 0.1 }, { id: 'p1', kind: 'pool', per1k24: 9, tvl: 500 }, { id: 'p2', kind: 'pool', per1k24: 1, tvl: 2e6 }, { id: 'p3', kind: 'pool', per1k24: 0, tvl: 2e6 }, { id: 's1', kind: 'stock', per1k24: 0 }];
  expect(topOptions(rows).map(r => r.id)).toEqual(['l2', 'l1', 'p2']); expect(topOptions(null)).toEqual([]);
});
test('the boost folder shows the deal in live numbers, and burning points asks the server', async () => {
  const stake = { sentUsd: 10, capUsd: 18.7, x: 1.87, grade: 87, paidUsd: 2, burned: 0, pointsLeft: 16.7, cutPct: 1.87, fastPct: 0, nowPct: 1.87, topPct: 2, fastUntil: null };
  const work = jest.fn(async (id, b) => (b.op === 'pool' ? { pool: { streams: [] }, stake, pools: [{ id: 'p1', pair: 'SOL-USDC', platform: 'orca', on: true, profitUsd: 4 }, { id: 'p2', pair: 'X-Y', platform: 'orca', on: false }], sends: [{ id: 's1', name: 'PoW 1', sym: 'BONK', grade: 87, x: 1.87, usd: 10, sig: 'abc' }, { id: 's2', held: true, name: 'PoW 2', usd: 5, x: 1 }], rules: { collectivePoolPct: 20, cutPerX: 1, fastPtsPerDay: 5, fastMaxDays: 30 } } : { stake: { ...stake, burned: 5, pointsLeft: 11.7, nowPct: 2, fastUntil: Date.now() / 1000 + 86400 } }));
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={work} />);
  const q = t => el.querySelector(`[data-testid="${t}"]`);
  expect(work).toHaveBeenCalledWith('c', { op: 'pool' }); expect(q('bof-x').textContent).toBe('1.87x'); expect(q('bof-cut').textContent).toBe('1.87%'); expect(q('bof-points').textContent).toContain('16.7');
  expect(q('bof-pool-p1')).toBeTruthy(); expect(q('bof-pool-p2')).toBeNull(); expect(q('bst-withdraw-off')).toBeTruthy();
  expect(q('bst-count').textContent).toContain('$'); expect(q('bof-it')).toBeTruthy(); expect(q('bof-send-s1').textContent).toContain('$18.70'); expect(q('bof-send-s2').textContent).toContain('Held');
  expect(q('send-warning').textContent).toContain('Only stake what you can lose');
  await click(q('bof-burn')); expect(work).toHaveBeenCalledWith('c', { op: 'pool_fast', cap: 1 }); expect(q('bof-fast-left').textContent).toContain('left');
  await act(async () => root.unmount());
});
test('with nothing staked and no pools it says so and promises nothing', async () => {
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={async () => ({ pool: { streams: [] }, stake: {}, pools: [], sends: [], rules: {} })} />);
  expect(el.querySelector('[data-testid="bof-no-pools"]').textContent).toContain('nothing pays'); expect(el.querySelector('[data-testid="bof-fast-why"]').textContent).toContain('no points'); expect(el.querySelector('[data-testid="bof-burn"]')).toBeNull();
  await act(async () => root.unmount());
});
