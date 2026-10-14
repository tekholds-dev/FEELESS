import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every scene renders its own layers; default + retired draw nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const kinds = ['default', 'reactor', 'neon', 'rain', 'gutter', 'sonar', 'lava', 'vhs'];
  await act(async () => { createRoot(el).render(<>{kinds.map(k => <ChartBg key={k} kind={k} />)}<ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(6);
  const q = (k, c) => el.querySelectorAll(`[data-testid="chart-bg-${k}"] ${c}`).length;
  expect(q('neon', '.cbg-grid')).toBe(2);
  expect(q('rain', '.cbg-col')).toBe(14);
  const col = el.querySelector('[data-testid="chart-bg-rain"] .cbg-col');
  expect(col.querySelector('.is-bull').textContent).toBe('SENDIT'); expect(col.querySelector('.is-bear').textContent).toBe('JEET');   // bull words up, bear words on a red tick
  expect(q('gutter', '.cbg-ripple')).toBe(4); expect(q('gutter', '.cbg-gsign')).toBe(1);
  expect(q('sonar', '.cbg-ping')).toBe(3); expect(q('sonar', '.cbg-whale')).toBe(1);
  expect(q('lava', '.cbg-blob')).toBe(5); expect(q('vhs', '.cbg-track')).toBe(1);
  expect(el.querySelectorAll('.cbg-tide').length).toBe(12);   // every scene breathes with the real tick
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(7);
  await act(async () => { sel.value = 'gutter'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('gutter');
  setChartBg('default');
});
