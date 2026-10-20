import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + five scenes, one remembered choice, retired / junk ids fall back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'neon', 'rain', 'pit', 'tape']);
  expect(getChartBg()).toBe('default');
  setChartBg('pit'); expect(getChartBg()).toBe('pit'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('pit');
  setChartBg('hyper'); expect(getChartBg()).toBe('default');   // over-designed scenes are retired
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('sonar'); expect(getChartBg()).toBe('default');   // a retired scene falls back to the plain chart
});
