import { tweenClose } from './tween';

test('the 30fps candle ease starts where it is drawn and ends EXACTLY on the real tick, never past it', () => {
  expect(tweenClose(1, 2, 0)).toBe(1);
  expect(tweenClose(1, 2, 1)).toBe(2); expect(tweenClose(1, 2, 3)).toBe(2);
  const mid = tweenClose(1, 2, 0.5); expect(mid).toBeGreaterThan(1.5); expect(mid).toBeLessThan(2);   // ease-out: most of the move early
  expect(tweenClose(2, 1, 0.5)).toBeLessThan(1.5);
  expect(tweenClose(NaN, 3, 0.2)).toBe(3);
});
