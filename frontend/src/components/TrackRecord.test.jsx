import { receiptLine } from './TrackRecord';

test('a closed trade, an open lot and a call each read as one honest line', () => {
  const t = receiptLine({ kind: 'trade', symbol: 'COIN', entryPx: 0.001, exitPx: 0.002, ret: 1, holdMin: 90, at: Date.now() / 1000 - 3600 });
  expect(t.title).toBe('$COIN'); expect(t.pct).toBe('+100%'); expect(t.up).toBe(true); expect(t.sub).toContain('held 1.5h'); expect(t.ico).toBe('✅');
  const loss = receiptLine({ kind: 'trade', symbol: 'X', entryPx: 2, exitPx: 1, ret: -0.5, holdMin: 5, at: Date.now() / 1000 });
  expect(loss.pct).toBe('-50.0%'); expect(loss.up).toBe(false);                      // a losing receipt is shown as losing
  const o = receiptLine({ kind: 'open', symbol: 'Y', entryPx: 1, exitPx: null, ret: null, at: Date.now() / 1000 });
  expect(o.pct).toBe('—'); expect(o.sub).toContain('now —'); expect(o.up).toBe(false);   // no live price → a dash, never a fake 0%
  const c = receiptLine({ kind: 'call', symbol: 'Z', entryPx: 1, exitPx: 0.4, ret: -0.6, peakX: 3, at: Date.now() / 1000 });
  expect(c.sub).toContain('peaked 3×'); expect(c.label).toBe('call');
});
