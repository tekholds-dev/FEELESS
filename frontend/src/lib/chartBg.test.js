import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + four scenes, one remembered choice, retired / junk ids fall back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'neon', 'rain', 'hyper', 'casino']);
  expect(getChartBg()).toBe('default');
  setChartBg('hyper'); expect(getChartBg()).toBe('hyper'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('hyper');
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('sonar'); expect(getChartBg()).toBe('default');   // a retired scene falls back to the plain chart
});
