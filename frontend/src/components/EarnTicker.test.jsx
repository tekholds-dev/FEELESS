import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { EarnTicker, perSecond } from './EarnTicker';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('💸 the money ticks up every second at the live rate — $100 at 36.5 % = $0.10 a day', async () => {
  expect(perSecond(100, 36.5) * 86400).toBeCloseTo(0.1, 6); expect(perSecond(0, 10)).toBe(0);
  jest.useFakeTimers();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<EarnTicker usd={100} apy={36.5} testid="t" />); });
  expect(el.querySelector('[data-testid="t"]').textContent).toContain('$0.1000 a day');
  const t0 = el.querySelector('b').textContent;
  await act(async () => { jest.advanceTimersByTime(5000); });
  expect(el.querySelector('b').textContent).not.toBe(t0);                                              // it moved
  await act(async () => { root.render(<EarnTicker perYear={0} testid="t" />); });
  expect(el.querySelector('[data-testid="t"]').className).not.toContain('is-on');
  act(() => root.unmount()); el.remove(); jest.useRealTimers();
});
