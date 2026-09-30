import { shouldGoLite, setLite, liteMode } from './perfWatch';

test('goes lite on low fps or heavy main-thread blocking only', () => {
  expect(shouldGoLite({ fps: 30, longMs: 0 })).toBe(true);
  expect(shouldGoLite({ fps: 58, longMs: 2000 })).toBe(true);
  expect(shouldGoLite({ fps: 58, longMs: 200 })).toBe(false);
  expect(shouldGoLite({ fps: null, longMs: 0 })).toBe(false);
});

test('lite mode toggles the body class and persists', () => {
  setLite('manual');
  expect(document.body.classList.contains('fx-lite')).toBe(true);
  expect(liteMode()).toBe('manual');
  setLite('');
  expect(document.body.classList.contains('fx-lite')).toBe(false);
});
