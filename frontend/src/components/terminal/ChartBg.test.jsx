import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartBg, ChartBgPicker } from './ChartBg';
import { getChartBg, setChartBg } from '../../lib/chartBg';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('every chart scene renders its own layers with the FEELESS mark; default draws nothing; the picker sets it for every chart', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><ChartBg kind="default" /><ChartBg kind="reactor" /><ChartBg kind="helix" /><ChartBg kind="sunset" /><ChartBg kind="aurora" /><ChartBgPicker /></>); });
  expect(el.querySelectorAll('.cbg').length).toBe(4);
  expect(el.querySelectorAll('[data-testid="chart-bg-reactor"] .cbg-ring').length).toBe(3);
  expect(el.querySelectorAll('[data-testid="chart-bg-helix"] .cbg-rung').length).toBe(14);
  expect(el.querySelectorAll('[data-testid="chart-bg-sunset"] .cbg-sun').length).toBe(1); expect(el.querySelectorAll('[data-testid="chart-bg-sunset"] .cbg-glint').length).toBe(7);
  expect(el.querySelectorAll('[data-testid="chart-bg-aurora"] .cbg-star').length).toBe(18); expect(el.querySelectorAll('[data-testid="chart-bg-aurora"] .cbg-veil').length).toBe(3);
  expect(el.querySelector('[data-testid="chart-bg-reactor"] img.cbg-mark').getAttribute('src')).toContain('feeless-logo');
  const sel = el.querySelector('[data-testid="chart-bg-pick"]'); expect(sel.options.length).toBe(5);
  await act(async () => { sel.value = 'sunset'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(getChartBg()).toBe('sunset'); expect(sel.value).toBe('sunset');
  setChartBg('default');
});
