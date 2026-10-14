import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every neon scene renders its own layers; default draws nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const kinds = ['default', 'neon', 'reactor', 'helix', 'city', 'warp', 'rain', 'tunnel', 'storm'];
  await act(async () => { createRoot(el).render(<>{kinds.map(k => <ChartBg key={k} kind={k} />)}<ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(8);
  const q = (k, c) => el.querySelectorAll(`[data-testid="chart-bg-${k}"] ${c}`).length;
  expect(q('neon', '.cbg-grid')).toBe(2); expect(q('reactor', '.cbg-ring')).toBe(3); expect(q('helix', '.cbg-rung')).toBe(14);
  expect(q('city', '.cbg-sky')).toBe(2); expect(q('city', '.cbg-win')).toBe(24); expect(q('warp', '.cbg-streak')).toBe(16);
  expect(q('rain', '.cbg-col')).toBe(16); expect(el.querySelector('[data-testid="chart-bg-rain"] .cbg-col').textContent).toBe('SENDIT');
  expect(q('tunnel', '.cbg-frame')).toBe(6); expect(q('storm', '.cbg-bolt')).toBe(1);
  expect(el.querySelectorAll('.cbg-tide').length).toBe(16);   // every scene breathes with the real tick
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(9);
  await act(async () => { sel.value = 'city'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('city');
  setChartBg('default');
});
