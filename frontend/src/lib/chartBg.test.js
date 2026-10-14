import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + eight neon scenes, one remembered choice, retired / junk ids fall back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'neon', 'reactor', 'helix', 'city', 'warp', 'rain', 'tunnel', 'storm']);
  expect(getChartBg()).toBe('default');
  setChartBg('helix'); expect(getChartBg()).toBe('helix'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('helix');
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('sunset'); expect(getChartBg()).toBe('default');   // a retired calm scene falls back to the plain chart
});
