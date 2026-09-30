import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useMoneyPulse, refreshPulse, circleFor, _resetPulse } from './moneyPulse';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('many cards, one request', async () => {
  _resetPulse();
  const call = jest.fn(async () => ({ circle: { wallets: [{ address: 'R', name: 'Reserve' }] }, checks: [] }));
  const seen = [];
  const Card = () => { const p = useMoneyPulse(call); seen.push(p.data); return null; };
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<><Card /><Card /><Card /></>); });
  expect(call).toHaveBeenCalledTimes(1);
  expect(circleFor(seen[seen.length - 1], 'R').name).toBe('Reserve');
  await act(async () => { await refreshPulse(true); });
  expect(call).toHaveBeenLastCalledWith('/admin/money-pulse?fresh=1');
  act(() => root.unmount());
});
