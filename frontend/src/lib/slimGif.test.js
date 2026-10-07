import { gifPlan } from './slimGif';

test('a light GIF is left alone; a big or fast one is shrunk to its box, 20 fps, 96 frames', () => {
  expect(gifPlan({ w: 750, h: 250, frames: 36, durMs: 8000 }, [1200, 400])).toBeNull();           // already small + slow
  const big = gifPlan({ w: 3000, h: 1000, frames: 300, durMs: 10000 }, [1200, 400]);
  expect(big.w).toBe(1200); expect(big.h).toBe(400); expect(big.frames.length).toBe(96); expect(big.delay).toBe(104);
  expect(big.frames[0]).toBe(0); expect(big.frames[95]).toBeLessThan(300);
  const fast = gifPlan({ w: 256, h: 256, frames: 100, durMs: 2000 }, [256, 256]);                  // 50 fps → 20
  expect(fast.w).toBe(256); expect(fast.frames.length).toBe(40);
  const tall = gifPlan({ w: 1000, h: 2000, frames: 10, durMs: 2000 }, [256, 256]);                 // still covers a square box
  expect(tall.w).toBe(256); expect(tall.h).toBe(512);
  expect(gifPlan({ w: 500, h: 500, frames: 1, durMs: 0 }, [256, 256])).toBeNull();
});
