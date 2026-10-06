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

test('🎯 Sniper shows what it buys and its checked proof; on a real card one tap also sets the selection', async () => {
  const sn = { key: 'sniper', name: '🎯 Sniper', why: 'w', cfg: { tp: '100', sl: '15', rideAt: '15', trail: '8', confirm: '4', minDrop: '10', age: '12', pool: '50', edge: '1' }, n: 40, medPct: 5.5, upPct: 60, windows: 5, windowsUp: 3, worstPct: -2.2, trades: 3, hours: 12, profitable: true };
  global.fetch = jest.fn(async () => ({ json: async () => ({ clock: 30, strategies: [sn], note: '' }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<StrategyPicks hours={0.5 + 0.001} current={{ rideAt: 15, rideTrail: 8, runnerMinLiqK: 0 }} selection onApply={() => {}} testid="sn" />); });
  await act(() => new Promise(r => setTimeout(r, 10)));
  expect(el.textContent).toContain('pool ≥ $50K · 12h+ old · 🧠 record-backed');
  expect(el.textContent).toContain('checked · 3/5 windows up');
  expect(el.querySelector('[data-testid="sn-sniper"]').className).not.toContain('is-on');   // same exits, but the pool rule is not on yet
  expect(stratPatch(sn.cfg, true)).toMatchObject({ runnerMinLiqK: 50, edgeGate: true, sl: 15 });
  expect(stratPatch(sn.cfg)).not.toHaveProperty('runnerMinLiqK');
});
