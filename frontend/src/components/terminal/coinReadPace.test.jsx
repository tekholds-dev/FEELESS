import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useCoinRead, paceMs } from './ChartVitals';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('vitals follow the coin\'s activity: its own pace, and a price move re-reads at once (never faster than half the pace)', async () => {
  jest.useFakeTimers();
  expect(paceMs({ pace: { everyMs: 5000 } })).toBe(5000); expect(paceMs(null)).toBe(20000); expect(paceMs({ pace: { everyMs: 100 } })).toBe(4000);
  let n = 0;
  global.fetch = jest.fn(async () => { n += 1; return { ok: true, json: async () => ({ mint: 'M', n, pace: { key: 'hot', everyMs: 5000 } }) }; });
  let got = null; const Probe = ({ k }) => { got = useCoinRead('M', k); return null; };
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<Probe k={1} />); }); await act(async () => { await Promise.resolve(); });
  expect(n).toBe(1); expect(got.pace.key).toBe('hot');
  await act(async () => { jest.advanceTimersByTime(5100); }); await act(async () => { await Promise.resolve(); });
  expect(n).toBe(2);   // hot coin: re-read after 5s, not 20s
  await act(async () => { jest.advanceTimersByTime(3000); root.render(<Probe k={2} />); }); await act(async () => { await Promise.resolve(); });
  expect(n).toBe(3);   // price moved, 3s ≥ half its pace → re-read now
  await act(async () => { root.render(<Probe k={3} />); }); expect(n).toBe(3);   // a second move straight after waits
  await act(async () => { root.unmount(); }); jest.useRealTimers();
});
