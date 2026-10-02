import React, { useState } from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CardPlan, planBody } from './FuseLab';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('card plan: each coin can be frozen, get its own replace clock and stop mode — sent with the plan', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({}) }));
  let latest = null;
  const Host = () => { const [plan, setPlan] = useState({ risk: 'custom', at: 50, onProfit: 'collect', mode: 'swap', rotateHours: 24, slMode: 'sell', legs: {} }); latest = plan;
    return <CardPlan legs={[{ pairAddress: 'P1', symbol: 'AAA', runner: true }]} plan={plan} setPlan={setPlan} />; };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<Host />); });
  act(() => el.querySelector('[data-testid="coinx-frz-P1"]').click());
  act(() => el.querySelector('[data-testid="coinx-rot-15m-P1"]').click());
  act(() => el.querySelector('[data-testid="coinx-sl-park-P1"]').click());
  expect(planBody(latest).coins).toEqual({ P1: { frozen: true, rotateHours: 0.25, slMode: 'park' } });
  expect(el.querySelector('[data-testid="coinx-frz-P1"]').className).toContain('is-on');
});
