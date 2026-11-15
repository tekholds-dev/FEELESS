import { shouldGoLite, setLite, liteMode } from './perfWatch';

test('goes lite on low fps or heavy main-thread blocking only', () => {
  expect(shouldGoLite({ fps: 30, longMs: 0 })).toBe(false);   // 🔋 battery 30 fps cap is not lag
  expect(shouldGoLite({ fps: 20, longMs: 0 })).toBe(true);
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

test('reports reach the server with a keepalive JSON POST (not a beacon Chrome rejects)', async () => {
  jest.useFakeTimers();
  const calls = [];
  window.fetch = jest.fn(async (url, opts) => { calls.push([String(url), opts]); return { json: async () => ({}) }; });
  window.PerformanceObserver = class { observe() {} };
  const { startPerfWatch } = require('./perfWatch');
  startPerfWatch();
  await window.fetch('/api/market/feed?x=1');
  jest.advanceTimersByTime(61000);
  const sent = calls.find(([u, o]) => u.includes('/api/reputation/perf') && o?.method === 'POST');
  expect(sent[1].keepalive).toBe(true);
  expect(JSON.parse(sent[1].body).api['/api/market/feed']).toHaveLength(1);
  jest.useRealTimers();
});

test('auto lite is told apart from a user-chosen lite mode', () => {
  const { isAutoLite } = require('./perfWatch');
  expect(isAutoLite('auto@1')).toBe(true); expect(isAutoLite('on')).toBe(false);
});

test('🎮 judge: two samples under 25 fps step quality down (to level 2 at most); 30 s at 45+ steps one back up', () => {
  const { judge, FLOOR_FPS } = require('./perfWatch');
  expect(FLOOR_FPS).toBe(25);
  expect(judge([60, 20], 0)).toBe(0); expect(judge([20, 22], 0)).toBe(1); expect(judge([30, 28], 0)).toBe(0);
  expect(judge([20, 22], 1)).toBe(2); expect(judge([20, 22], 2)).toBe(2);
  expect(judge([50, 50, 50, 50, 50], 1)).toBe(1); expect(judge([50, 50, 50, 50, 50, 50], 2)).toBe(1); expect(judge([50, 50, 30, 50, 50, 50], 1)).toBe(1);
});
