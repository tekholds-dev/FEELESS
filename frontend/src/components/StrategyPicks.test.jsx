import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { StrategyPicks, stratPatch } from './StrategyPicks';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('3 strategies for the card clock, the one in use marked, one tap applies its exits', async () => {
  const S = (key, rideAt, trail) => ({ key, name: key, why: 'w', cfg: { tp: '100', sl: '20', rideAt: String(rideAt), trail: String(trail), confirm: '2', minDrop: '10' }, n: 9, medPct: 1.2, upPct: 55 });
  global.fetch = jest.fn(async () => ({ json: async () => ({ clock: 5, strategies: [S('steady', 50, 15), S('engine', 15, 8), S('hunt', 25, 5)], note: '' }) }));
  const on = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<StrategyPicks hours={5 / 60} current={{ rideAt: 15, rideTrail: 8 }} onApply={on} testid="sp" />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  expect(el.textContent).toContain('3 STRATEGIES · 5m ROUNDS');
  expect(el.querySelector('[data-testid="sp-engine"]').className).toContain('is-on');
  await act(async () => { el.querySelector('[data-testid="sp-apply-hunt"]').click(); });
  expect(on.mock.calls[0][0].key).toBe('hunt');
  expect(stratPatch(on.mock.calls[0][0].cfg)).toEqual({ rideAt: 25, rideTrail: 5, rotateMinDrop: 10, rotateConfirm: 2, tp: 100, sl: 20 });
});
