import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every chart scene renders its own layers with the FEELESS mark / FeeCat; default draws nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><ChartBg kind="default" /><ChartBg kind="reactor" /><ChartBg kind="warp" /><ChartBg kind="helix" /><ChartBg kind="cat" /><ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(4);
  expect(el.querySelectorAll('[data-testid="chart-bg-reactor"] .cbg-ring').length).toBe(3);
  expect(el.querySelector('[data-testid="chart-bg-warp"]').textContent).toContain('FUSE');
  expect(el.querySelectorAll('[data-testid="chart-bg-helix"] .cbg-rung').length).toBe(14);
  expect(el.querySelector('[data-testid="chart-bg-cat"] img.cbg-cat').getAttribute('src')).toContain('feecat');
  expect(el.querySelector('[data-testid="chart-bg-reactor"] img.cbg-mark').getAttribute('src')).toContain('feeless-logo');
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(5);
  await act(async () => { sel.value = 'cat'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('cat'); expect(sel.value).toBe('cat');
  setChartBg('default');
});
