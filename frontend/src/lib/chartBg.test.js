import { CHART_BGS, getChartBg, setChartBg } from './chartBg';

test('chart backgrounds: default + two Fuse scenes + five calm ones, one remembered choice, junk falls back to default', () => {
  expect(CHART_BGS.map(([k]) => k)).toEqual(['default', 'reactor', 'helix', 'sunset', 'aurora', 'peaks', 'sakura', 'deep']);
  expect(getChartBg()).toBe('default');
  setChartBg('helix'); expect(getChartBg()).toBe('helix'); expect(window.localStorage.getItem('feeless.chartBg')).toBe('helix');
  setChartBg('nope'); expect(getChartBg()).toBe('default');
  setChartBg('warp'); expect(getChartBg()).toBe('default');   // a retired scene falls back to the plain chart
});
