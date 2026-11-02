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

test('idle overlays wait five seconds while the candle clock can still tick each second', () => {
  const frames = []; global.requestAnimationFrame = fn => { frames.push(fn); return frames.length; };
  let beat; const timer = jest.spyOn(global, 'setInterval').mockImplementation(fn => { beat = fn; return 1; });
  const box = { current: document.createElement('div') }; const ran = { overlay: 0, clock: 0 };
  const stopOverlay = addChartJob(box, () => { ran.overlay += 1; });
  const stopClock = addChartJob(box, () => { ran.clock += 1; }, 1000);
  frames.shift()(100);
  beat(); frames.shift()(1200);
  expect(ran).toEqual({ overlay: 1, clock: 2 });
  beat(); frames.shift()(5200);
  expect(ran).toEqual({ overlay: 2, clock: 3 });
  stopOverlay(); stopClock();
  expect(chartJobCount()).toBe(0);
  timer.mockRestore();
});
