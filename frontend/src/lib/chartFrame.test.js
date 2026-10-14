import { addChartJob, bumpChart, chartJobCount } from './chartFrame';

test('one shared frame: a job runs when ITS chart changed, not every frame', () => {
  const frames = []; global.requestAnimationFrame = fn => { frames.push(fn); return frames.length; };
  const a = { current: document.createElement('div') }; const b = { current: document.createElement('div') };
  const ran = { a: 0, b: 0 };
  const sa = addChartJob(a, () => { ran.a += 1; }); const sb = addChartJob(b, () => { ran.b += 1; });
  frames.shift()(10);                     // first frame: both draw once
  expect(ran).toEqual({ a: 1, b: 1 });
  bumpChart(a.current); frames.shift()(50);   // only chart a changed
  expect(ran).toEqual({ a: 2, b: 1 });
  expect(frames.length).toBe(0);              // nothing changed → no frame is even asked for
  sa(); sb(); expect(chartJobCount()).toBe(0);
});
