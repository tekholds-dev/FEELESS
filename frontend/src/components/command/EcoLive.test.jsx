import { flowOf } from './EcoLive';
jest.mock('../../lib/adminCall', () => ({ useAdmin: () => ({}) }));

test('💸 the money flow balances and shows the pocket only when fees did not cover the models', () => {
  const f = flowOf({ kpi: { feesUsd: 2, feeBackPaidUsd: 0.5, spendUsd: 7.5 }, byModel: [{ k: 'Sonnet 5.5', usd: 6 }, { k: 'Hy4', usd: 1 }] });
  const into = f.links.filter(l => l.target === 2).reduce((a, l) => a + l.value, 0); const outOf = f.links.filter(l => l.source === 2).reduce((a, l) => a + l.value, 0);
  expect(into).toBeCloseTo(outOf); expect(into).toBeCloseTo(8);
  expect(f.nodes.map(n => n.name)).toEqual(['Fees in', 'Your pocket', 'FEELESS', 'FeeBack paid', 'Sonnet 5.5', 'Hy4', 'Other models']);
  const kept = flowOf({ kpi: { feesUsd: 10, spendUsd: 3 }, byModel: [{ k: 'm', usd: 3 }] });
  expect(kept.nodes.at(-1)).toMatchObject({ name: 'Kept' }); expect(kept.links.some(l => l.source === 1)).toBe(false);   // no pocket when fees cover it
  expect(flowOf({ kpi: {} })).toBeNull();   // no money moved → no chart, never a placeholder
});
