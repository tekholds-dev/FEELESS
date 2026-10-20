import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LaunchLab, TYPES, PLATFORMS } from './LaunchLab';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../lib/launchRail', () => ({ fetchLaunchRail: () => Promise.resolve({ ready: true, tab: { maxDevBuySol: 5 }, costs: { pumpSlippagePct: 1 } }) }));

test('every type has a demo, and switching types plays its own story', async () => {
  expect(TYPES.length).toBeGreaterThanOrEqual(6); expect(PLATFORMS.some(p => p.feeless)).toBe(true);
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchLab />); });
  expect(el.querySelector('.llb-curve')).toBeTruthy(); expect(el.textContent).toContain('dev buy up to 5 SOL');
  expect(el.textContent).not.toContain('House config');
  act(() => el.querySelector('[data-testid="llb-amm"]').click());
  expect(el.textContent).toContain('x · y = k'); expect(el.querySelector('.llb-pile')).toBeTruthy();
  act(() => el.querySelector('[data-testid="llb-dlmm"]').click());
  expect(el.querySelectorAll('.llb-bin')).toHaveLength(11);
  act(() => root.unmount());
});

test('HQ sees the house config extra and can open on pools', async () => {
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchLab hq start="amm" />); });
  expect(el.textContent).toContain('House config'); expect(el.querySelector('[data-testid="llb-amm"]').getAttribute('aria-selected')).toBe('true');
  act(() => root.unmount());
});
