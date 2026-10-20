import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every scene renders its own layers; default + retired draw nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const kinds = ['default', 'reactor', 'gutter', 'hyper', 'casino', 'aurora', 'pulse', 'moon', 'pills', 'tape', 'neon', 'city', 'warp', 'orbit', 'rain'];
  await act(async () => { createRoot(el).render(<>{kinds.map(k => <ChartBg key={k} kind={k} />)}<ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(4);   // retired scenes draw nothing
  const q = (k, c) => el.querySelectorAll(`[data-testid="chart-bg-${k}"] ${c}`).length;
  expect(q('neon', '.cbg-grid')).toBe(2); expect(q('neon', '.cbg-sun img')).toBe(1); expect(q('neon', '.cbg-word')).toBe(1);   // the FEELESS mark is neon trench's sun
  expect(q('city', '.cbg-skyline')).toBe(2); expect(q('city', '.cbg-sign')).toBe(2); expect(q('warp', '.cbg-gate')).toBe(9); expect(q('warp', '.cbg-ray')).toBe(14);
    expect(q('rain', '.cbg-col')).toBe(18); expect(q('rain', '.cbg-col.is-z0')).toBeGreaterThan(0);
  const col = el.querySelector('[data-testid="chart-bg-rain"] .cbg-col');
  expect(col.querySelector('.is-bull').textContent.length).toBeGreaterThan(8); expect(col.querySelector('.is-bear').textContent).toBe('JEET');   // bull words up, bear words on a red tick
  expect(el.querySelectorAll('.cbg-tide').length).toBe(8);   // every scene breathes with the real tick
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(5);
  await act(async () => { sel.value = 'warp'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('warp');
  setChartBg('casino'); expect(getChartBg()).toBe('default');   // over-designed scenes are retired
  setChartBg('gutter'); expect(getChartBg()).toBe('default');   // a retired id falls back
});
