import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartToolsMenu } from './ChartTools';
import { getChartTools, toggleChartTool } from '../../lib/chartTools';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('chart tools menu: five one-click tools remembered for every chart; meta edge shows score + plan and opens its reasons', async () => {
  window.localStorage.clear(); getChartTools().slice().forEach(toggleChartTool);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const read = { fvg: [], magnets: [], gun: null, germ: null, edge: { score: 72, verdict: 'edge', plan: 'Dead under the germ.', why: ['trend up (higher highs + higher lows)', '9% off its high — a dip, not a top'] } };
  await act(async () => { root.render(<ChartToolsMenu read={null} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('chart-tools-pop')).toBeNull(); expect(q('chart-edge')).toBeNull();
  await act(async () => { q('chart-tools-btn').click(); });
  expect(q('chart-tools-pop').querySelectorAll('button').length).toBe(5);
  for (const t of ['FVG', 'Magnets', 'Gun line', 'Germ', 'Meta edge']) expect(q('chart-tools-pop').textContent).toContain(t);
  await act(async () => { q('chart-tool-fvg').click(); }); await act(async () => { q('chart-tool-edge').click(); });
  expect(getChartTools()).toEqual(['fvg', 'edge']); expect(q('chart-tool-edge').getAttribute('aria-checked')).toBe('true'); expect(q('chart-tools-btn').textContent).toContain('⚡');
  await act(async () => { root.render(<ChartToolsMenu read={read} />); });
  expect(q('chart-edge').textContent).toContain('72'); expect(q('chart-edge').textContent).toContain('EDGE'); expect(q('chart-edge').textContent).toContain('Dead under the germ.');
  await act(async () => { q('chart-edge').click(); });
  expect(q('chart-edge-why').textContent).toContain('a dip, not a top'); expect(q('chart-edge-why').textContent).toContain('not advice');
  await act(async () => { document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); }); expect(q('chart-tools-pop')).toBeNull();
  toggleChartTool('fvg'); toggleChartTool('edge'); await act(async () => { root.unmount(); });
});
