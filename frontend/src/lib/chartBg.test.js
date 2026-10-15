import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + four calm scenes, one remembered choice, retired / junk ids fall back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'aurora', 'pulse', 'neon', 'rain']);
  expect(getChartBg()).toBe('default');
  setChartBg('aurora'); expect(getChartBg()).toBe('aurora'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('aurora');
  setChartBg('hyper'); expect(getChartBg()).toBe('default');   // over-designed scenes are retired
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('sonar'); expect(getChartBg()).toBe('default');   // a retired scene falls back to the plain chart
});
