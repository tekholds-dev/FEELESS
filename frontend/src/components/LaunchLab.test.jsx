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

test('🚪 every launch type, platform and exclusive is a real door', async () => {
  const { DOOR } = require('./LaunchLab');
  expect(Object.keys(DOOR).sort()).toEqual(['amm', 'dbc', 'dlmm', 'launchlab', 'lock', 'pump']);
  expect(DOOR.pump[0]).toBe('/terminal/launch?setup=feeless&rail=pump');
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<LaunchLab />); });
  expect(el.querySelector('[data-testid="llb-door-pump"]').getAttribute('href')).toBe('/terminal/launch?setup=feeless&rail=pump');
  expect(el.querySelector('[data-testid="llb-plat-FEELESS"]').getAttribute('href')).toBe('/terminal/launch?setup=feeless');
  expect(el.querySelector('[data-testid="llb-plat-Raydium"]').getAttribute('target')).toBe('_blank');
  expect(el.querySelectorAll('.llb-exd').length).toBe(5);   // the HQ-only exclusive stays out of the public page
  await act(async () => { root.unmount(); });
});
