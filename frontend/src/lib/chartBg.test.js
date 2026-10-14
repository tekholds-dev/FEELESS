import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + six scenes, one remembered choice, retired / junk ids fall back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'neon', 'rain', 'gutter', 'sonar', 'lava', 'vhs']);
  expect(getChartBg()).toBe('default');
  setChartBg('sonar'); expect(getChartBg()).toBe('sonar'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('sonar');
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('reactor'); expect(getChartBg()).toBe('default');   // a retired scene falls back to the plain chart
});
