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
