import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FpsMeters } from './LagCatcher';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.createElement('div'); const root = createRoot(el); await act(async () => { root.render(node); }); return el; };

test('pages show as meters against the 25 fps floor, worst first', async () => {
  const el = await mount(<FpsMeters pages={[{ page: '/terminal', fps: 52, fpsLow: 40, reports: 3, underFloor: 0, stepped: 0 }, { page: '/familia', fps: 18, fpsLow: 9, reports: 4, underFloor: 3, stepped: 2 }]} />);
  const m = el.querySelectorAll('[role="meter"]');
  expect(m[0].getAttribute('aria-label')).toBe('/familia 18 fps');
  expect(el.textContent).toContain('3/4 under 25 · stepped down 2×');
  expect(el.querySelector('.fpm-row.t-bad')).not.toBeNull();
});

test('no fps yet says so', async () => {
  const el = await mount(<FpsMeters pages={[{ page: '/x', fps: null }]} />);
  expect(el.textContent).toMatch(/No fps samples yet/);
});
