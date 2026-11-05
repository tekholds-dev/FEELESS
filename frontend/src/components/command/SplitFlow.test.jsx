import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { SplitFlow, splitOf } from './SplitFlow';
import { BoostFolder } from './BoostFolder';
import { CollectiveOwner } from './CollectiveOwner';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RULES = { skimPct: 20, splitPct: 75, splitMaxPct: 78, halfLifeDays: 30, halfLifeMinDays: 15, potPct: 30, weightMaxX: 2, depositPct: 10, firstMinUsd: 50, txnSmallPct: 5, txnMidPct: 3, txnBigPct: 1, txnSmallUsd: 10, txnBigUsd: 100, boostMode: 'payout' };
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(node); }); return { el, root }; };
const click = async n => act(async () => { n.dispatchEvent(new MouseEvent('click', { bubbles: true })); });

test('the owner example: $10 sent is $2 kept, $6 back, $2 on release', () => {
  expect(splitOf(RULES, 10)).toMatchObject({ kept: 2, locked: 8, back: 6, house: 2, split: 75, days: 30, floor: 0.6 });
  const full = splitOf(RULES, 10, 1); expect(full.split).toBe(78); expect(full.days).toBe(15); expect(full.back).toBeCloseTo(6.24);
  expect(splitOf({ ...RULES, boostMode: 'rank' }, 10, 1).split).toBe(75);
});
test('the picture follows the win, the share and the boost', async () => {
  const { el, root } = await mount(<SplitFlow rules={RULES} />);
  expect(el.querySelector('[data-testid="spf-send"]').textContent).toContain('$10.00');
  expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$6.00');
  expect(el.querySelector('[data-testid="spf-meter"]').textContent).toContain('60¢');
  expect(el.querySelector('[data-testid="spf-meter"]').textContent).toContain('not promised');
  await click(el.querySelector('[data-testid="spf-boost"]'));
  expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('$6.24');
  expect(el.querySelector('[data-testid="spf-back"]').textContent).toContain('78%');
  expect(el.querySelector('[data-testid="spf-pot"]').getAttribute('data-tip')).toContain('never promised');
  await act(async () => root.unmount());
});
test('a rule the server changes moves the picture', async () => {
  const { el, root } = await mount(<SplitFlow rules={{ ...RULES, skimPct: 30 }} />);
  expect(el.querySelector('[data-testid="spf-kept"]').textContent).toContain('$3.00');
  await act(async () => root.unmount());
});
test('the boost folder counts up and says withdrawals are off', async () => {
  const work = jest.fn(async () => ({ pool: { owedUsd: 1.5, ratePerSecUsd: 0.5, lockedUsd: 8, sentUsd: 10, earnedUsd: 0.2, levers: { splitPct: 75 } }, rules: RULES, points: 10, printLevel: 34, boostNow: 0.5, boostLog: [{ ref: 'x', pts: 10, why: 'paid the Pool' }] }));
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={work} />);
  expect(work).toHaveBeenCalledWith('c', { op: 'pool' });
  const n = () => Number(el.querySelector('[data-testid="bst-count"]').textContent.slice(1));
  const first = n(); expect(first).toBeGreaterThanOrEqual(1.5);
  await act(async () => { await new Promise(r => setTimeout(r, 450)); });
  expect(n()).toBeGreaterThan(first);
  expect(el.querySelector('[data-testid="bst-withdraw-off"]')).toBeTruthy();
  expect(el.querySelector('[data-testid="bst-lever-SPLIT"]').textContent).toContain('76.5 / 23.5');
  await act(async () => root.unmount());
});
test('an agent with nothing sent says so and shows the split', async () => {
  const { el, root } = await mount(<BoostFolder cat={{ id: 'c' }} work={async () => ({ pool: { empty: true, owedUsd: 0, lockedUsd: 0, levers: {} }, rules: RULES })} />);
  expect(el.textContent).toContain('starts with its first proof');
  expect(el.querySelector('details').open).toBe(true);
  await act(async () => root.unmount());
});
test('the owner folder saves a slider and explains every row', async () => {
  const cfg = { ...RULES, potHalfLifeDays: 30, capPct: 3, earnRoomX: 1, boostFadeDays: 60 }; const bounds = Object.fromEntries(Object.keys(cfg).map(k => [k, [0, 1000]]));
  const view = { cfg, defaults: cfg, bounds, totals: { usd: { keep: 7, pot: 3, locked: 8, owed: 1 }, in: { deposit: 5, proofs: 2 }, agents: 1, ratePerSecUsd: 0 }, chain: { short: [], tokens: { SOL: { chain: 1e9, need: 1e8 }, USDC: { chain: 0, need: 0 } } }, agents: [{ id: 'a', name: 'Happy', sentUsd: 10, lockedUsd: 8, owedUsd: 1, levers: { splitPct: 75 } }], log: [] };
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
