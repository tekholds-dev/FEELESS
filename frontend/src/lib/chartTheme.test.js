import { CHART_THEMES, chartColors, chartThemeId, setChartTheme } from './chartTheme';

test('🎨 a chart theme pick is stored, broadcast, and every theme has a readable night + day pair', () => {
  const seen = []; window.addEventListener('feeless:chart-theme', e => seen.push(e.detail));
  setChartTheme('cb'); expect(chartThemeId()).toBe('cb'); expect(seen).toEqual(['cb']);
  setChartTheme('nope'); expect(chartThemeId()).toBe('cb');
  Object.keys(CHART_THEMES).forEach(k => { const n = chartColors(false, k); const d = chartColors(true, k); expect(n.up).not.toBe(n.down); expect(d.up).not.toBe(d.down); });
  expect(chartColors(true, 'feeless').up).toBe('#08764e');
});
