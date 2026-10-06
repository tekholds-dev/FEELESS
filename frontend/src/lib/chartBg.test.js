import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + four live scenes, one remembered choice, junk falls back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'reactor', 'warp', 'helix', 'cat']);
  expect(getChartBg()).toBe('default');
  setChartBg('helix'); expect(getChartBg()).toBe('helix'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('helix');
  setChartBg('nope'); expect(getChartBg()).toBe('default');
});
