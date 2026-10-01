import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CardRules } from './FuseAdminSettings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RULES = { yieldLevels: [25, 50, 100], yieldDefault: 50, swapDropPct: 25, topTierPct: 50, fbHolderPct: 20, fbHoldHours: 24, fbLoyaltyPct: 10, fbLoyaltyDays: 7,
  fbArenaPct: 10, fbCapPct: 50, netFeeUsdPerLeg: 0.01, copyPct: 10, seasonBoostPct: 10 };

test('card rules: every field has a $ example, the Fee-Back story adds up, tapping a level makes it the default', async () => {
  const call = jest.fn(async (p, o) => (o ? { rules: JSON.parse(o.body) } : { rules: RULES, defaults: RULES, feeback: { rows: [], owedUsd: 1.5, earnedUsd: 4 } }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CardRules call={call} />); });
  expect(el.textContent).toContain('A $20 coin slice → alert at $15');
  expect(el.textContent).toContain('$100 card → top tier at $150');
  expect(el.querySelector('[data-testid="cr-story"]').textContent).toMatch(/\$0\.20 back.*\$0\.30.*\$0\.40.*best case \$0\.50/);
  await act(async () => { [...el.querySelectorAll('.cr-levels .m-chip')].find(b => b.textContent.startsWith('+100')).click(); });
  await act(async () => { el.querySelector('[data-testid="cr-save"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toMatchObject({ yieldDefault: 100, yieldLevels: [25, 50, 100] });
});
