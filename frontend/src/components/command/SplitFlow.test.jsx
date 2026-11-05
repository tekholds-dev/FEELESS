import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { SplitFlow, splitOf } from './SplitFlow';
import { BoostFolder } from './BoostFolder';
import { CollectiveOwner } from './CollectiveOwner';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RULES = { skimPct: 20, potPct: 50, potPayDayPct: 5, weightMaxX: 2, boostBackPts: 5, ptsBase: 5, ptsPerUsd: 2, ptsMaxSend: 60, ptsPerDay: 10, boostFadeDays: 60, depositPct: 10, firstMinUsd: 50, txnSmallPct: 5, txnMidPct: 3, txnBigPct: 1, txnSmallUsd: 10, txnBigUsd: 100, boostMode: 'payout', plans: [{ plan: 'week', days: 7, backPct: 70, weightX: 1, roomX: 1 }, { plan: 'month', days: 30, backPct: 85, weightX: 2, roomX: 2 }, { plan: 'quarter', days: 90, backPct: 95, weightX: 3, roomX: 3 }, { plan: 'vault', days: null, backPct: 0, weightX: 6, roomX: 6 }] };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root }; };
const click = async n => act(async () => { n.dispatchEvent(new MouseEvent('click', { bubbles: true })); });

test('a plan says how much comes back, and the Vault says nothing does', () => {
  expect(splitOf(RULES, 10, 'month')).toMatchObject({ kept: 2, locked: 8, days: 30, backPct: 85 }); expect(splitOf(RULES, 10, 'month').back).toBeCloseTo(6.8); expect(splitOf(RULES, 10, 'month', 1).back).toBeCloseTo(7.2);
  expect(splitOf(RULES, 10, 'vault', 1)).toMatchObject({ back: 0, vault: true, house: 8 }); expect(splitOf({ ...RULES, boostMode: 'rank' }, 10, 'month', 1).backPct).toBe(85);
});
test('the picture follows the plan, and the Vault asks twice', async () => {
  const { el, root } = await mount(<SplitFlow rules={RULES} />);
  expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$6.80'); expect(el.querySelector('[data-testid="spf-meter"]').textContent).toContain('not promised');
  await click(el.querySelector('[data-testid="plan-week"]')); expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$5.60');
  await click(el.querySelector('[data-testid="plan-vault"]')); expect(el.querySelector('[data-testid="plan-vault"]').textContent).toContain('Tap again'); expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$5.60');
  await click(el.querySelector('[data-testid="plan-vault"]')); expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$0.00'); expect(el.querySelector('[data-testid="spf-meter"]').textContent).toContain('stays in the Collective');
  await click(el.querySelector('[data-testid="spf-view-year"]')); expect(el.querySelector('[data-testid="ge-plans"]').textContent).toContain('Vault');
  await act(async () => root.unmount());
});
test('a rule the server changes moves the picture', async () => {
  const { el, root } = await mount(<SplitFlow rules={{ ...RULES, skimPct: 30 }} />);
  expect(el.querySelector('[data-testid="spf-kept"]').textContent).toContain('$3.00');
  await act(async () => root.unmount());
});
test('the boost folder counts up, shows each date and spends points', async () => {
  const stream = { id: 's1', plan: 'month', name: 'PoW 1', sym: 'BONK', sentUsd: 10, backUsd: 6.8, soFarUsd: 1, start: Date.now() / 1000 - 86400, at: Date.now() / 1000 - 86400, end: Date.now() / 1000 + 86400 * 29, sig: 'abc' };
  const work = jest.fn(async (id, b) => (b.op === 'pool' ? { pool: { owedUsd: 1.5, ratePerSecUsd: 0.5, lockedUsd: 8, sentUsd: 10, earnedUsd: 0.2, backLeftUsd: 5.8, nextEnd: stream.end, streams: [stream], levers: {} }, rules: RULES, points: 40, pointsLeft: 40, strength: 62, printLevel: 34, boostNow: 0.5, plan: 'month', boostLog: [{ ref: 'x', pts: 10, why: 'paid the Pool' }] } : { pointsLeft: 30, plan: b.text }));
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={work} />);
  expect(work).toHaveBeenCalledWith('c', { op: 'pool' });
  const n = () => Number(el.querySelector('[data-testid="bst-count"]').textContent.slice(1));
  const first = n(); expect(first).toBeGreaterThanOrEqual(1.5);
  await act(async () => { await new Promise(r => setTimeout(r, 450)); });
  expect(n()).toBeGreaterThan(first);
  expect(el.querySelector('[data-testid="bst-withdraw-off"]')).toBeTruthy(); expect(el.querySelector('[data-testid="bst-stream-s1"]').textContent).toContain('$6.80'); expect(el.querySelector('[data-testid="bst-lever-PRINT STRENGTH"]').textContent).toContain('62/100');
  await click(el.querySelector('[data-testid="bst-spend-s1"]')); expect(work).toHaveBeenCalledWith('c', { op: 'pool_spend', job: 's1', cap: 10 });
  await click(el.querySelector('[data-testid="bst-plan"] [data-testid="plan-week"]')); expect(work).toHaveBeenCalledWith('c', { op: 'pool_plan', text: 'week', on: false });
  await act(async () => root.unmount());
});
test('an agent with nothing sent says so and shows the split', async () => {
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={async () => ({ pool: { empty: true, owedUsd: 0, lockedUsd: 0, levers: {}, streams: [] }, rules: RULES })} />);
  expect(el.textContent).toContain('starts with its first proof');
  expect(el.querySelector('details').open).toBe(true);
  await act(async () => root.unmount());
});
test('the owner folder saves a slider and explains every row', async () => {
  const cfg = { ...RULES, capPct: 3, weekDays: 7, weekBack: 70, weekWeight: 1, weekRoom: 1, monthDays: 30, monthBack: 85, monthWeight: 2, monthRoom: 2, quarterDays: 90, quarterBack: 95, quarterWeight: 3, quarterRoom: 3, vaultWeight: 6, vaultRoom: 6 }; const bounds = Object.fromEntries(Object.keys(cfg).map(k => [k, [0, 1000]]));
  const view = { cfg, defaults: cfg, bounds, totals: { usd: { keep: 7, pot: 3, locked: 8, owed: 1 }, in: { deposit: 5, proofs: 2 }, agents: 1, ratePerSecUsd: 0 }, chain: { short: [], tokens: { SOL: { chain: 1e9, need: 1e8 }, USDC: { chain: 0, need: 0 } } }, agents: [{ id: 'a', name: 'Happy', sentUsd: 10, lockedUsd: 8, owedUsd: 1, levers: { weightX: 1 } }], log: [] };
  const call = jest.fn(async (u, o) => (o ? { ...view, cfg: { ...cfg, ...JSON.parse(o.body).cfg } } : view));
  const { el, root } = await mount(<CollectiveOwner call={call} />);
  expect(el.querySelector('[data-testid="cof-cover"]').textContent).toContain('FULLY COVERED');
  expect(el.querySelector('[data-testid="cof-tank-keep"]').textContent).toContain('$7.00');
  await click(el.querySelector('[data-testid="cof-tab-set"]'));
  expect(el.querySelector('[data-testid="cof-withdrawals"]').textContent).toContain('OFF');
  [...el.querySelectorAll('.cof-row')].forEach(r => expect(r.getAttribute('data-tip')).toBeTruthy());
  expect(el.querySelector('[data-testid="cof-save"]').disabled).toBe(true);
  await click(el.querySelector('[data-testid="cof-mode-rank"]'));
  expect(el.querySelector('[data-testid="cof-preview"]')).toBeTruthy();
  await click(el.querySelector('[data-testid="cof-save"]'));
  expect(JSON.parse(call.mock.calls.find(c => c[1])[1].body).cfg.boostMode).toBe('rank');
  await act(async () => root.unmount());
});
