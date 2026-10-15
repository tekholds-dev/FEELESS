import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every scene renders its own layers; default + retired draw nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const kinds = ['default', 'reactor', 'gutter', 'hyper', 'casino', 'aurora', 'pulse', 'neon', 'rain'];
  await act(async () => { createRoot(el).render(<>{kinds.map(k => <ChartBg key={k} kind={k} />)}<ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(4);   // retired scenes draw nothing
  const q = (k, c) => el.querySelectorAll(`[data-testid="chart-bg-${k}"] ${c}`).length;
  expect(q('neon', '.cbg-grid')).toBe(2); expect(q('neon', '.cbg-sun')).toBe(0); expect(q('neon', '.cbg-streak')).toBe(0);   // neon trench cut back to a grid floor + horizon
  expect(q('aurora', '.cbg-veil')).toBe(3); expect(q('pulse', '.cbg-ring')).toBe(3); expect(q('pulse', '.cbg-scan')).toBe(1);
  expect(q('rain', '.cbg-col')).toBe(14); expect(q('rain', '.cbg-col.is-z0')).toBeGreaterThan(0); expect(q('rain', '.cbg-head')).toBe(14);
  const col = el.querySelector('[data-testid="chart-bg-rain"] .cbg-col');
  expect(col.querySelector('.is-bull').textContent).toBe('SENDIT'); expect(col.querySelector('.is-bear').textContent).toBe('JEET');   // bull words up, bear words on a red tick
  expect(el.querySelectorAll('.cbg-tide').length).toBe(8);   // every scene breathes with the real tick
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(5);
  await act(async () => { sel.value = 'aurora'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('aurora');
  setChartBg('casino'); expect(getChartBg()).toBe('default');   // over-designed scenes are retired
  setChartBg('gutter'); expect(getChartBg()).toBe('default');   // a retired id falls back
});
