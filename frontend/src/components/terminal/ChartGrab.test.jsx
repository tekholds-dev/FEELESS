import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChartGrab } from './ChartGrab';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const ptr = (el, type, y) => { const e = new MouseEvent(type, { bubbles: true, cancelable: true, clientY: y }); el.dispatchEvent(e); };

test('grab a Fuse coin\'s stop on its chart: the tab follows the drag in 1% steps and letting go asks the card (nothing on a no-move drop)', async () => {
  // a fake price axis: y = 400 − price × 200  (price 1.00 → y 200, 0.80 → y 240)
  const seriesRef = { current: { series: { priceToCoordinate: p => 400 - p * 200, coordinateToPrice: y => (400 - y) / 200 } } };
  const container = { current: { offsetTop: 0, getBoundingClientRect: () => ({ top: 0 }) } };
  const fuse = { tpl: 'degen', pairAddress: 'PA', symbol: 'SK', entry: 1, slPct: 15, lockPct: 15, trailPct: 15, riding: false };
  const asked = []; const on = e => asked.push(e.detail); window.addEventListener('feeless:fuse-level', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<ChartGrab seriesRef={seriesRef} container={container} fuse={fuse} />); });
  const tab = k => el.querySelector(`[data-testid="grab-${k}"]`);
  expect(tab('stop').textContent).toContain('−15%'); expect(tab('lock').textContent).toContain('+15%'); expect(tab('trail')).toBeNull();
  expect(tab('stop').parentElement.style.transform).toBe('translateY(230px)');             // 0.85 on the axis
  await act(async () => { ptr(tab('stop'), 'pointerdown', 230); }); await act(async () => { ptr(tab('stop'), 'pointermove', 234); });   // dragged to 0.83
  expect(tab('stop').textContent).toContain('−17%'); expect(tab('stop').parentElement.className).toContain('is-drag');
  expect(tab('stop').parentElement.style.transform).toBe('translateY(234px)');             // 1% steps: −17% = 0.83
  await act(async () => { ptr(tab('stop'), 'pointerup', 234); });
  expect(asked).toEqual([{ tpl: 'degen', pairAddress: 'PA', symbol: 'SK', kind: 'stop', pct: 17 }]);
  await act(async () => { ptr(tab('lock'), 'pointerdown', 170); }); await act(async () => { ptr(tab('lock'), 'pointerup', 170); });
  expect(asked.length).toBe(1);                                                             // dropped where it was = no question
  await act(async () => { root.render(<ChartGrab seriesRef={seriesRef} container={container} fuse={{ ...fuse, tpl: '' }} />); });
  expect(el.querySelector('[data-testid="chart-grab"]')).toBeNull();                        // not opened from a card = nothing to grab
  window.removeEventListener('feeless:fuse-level', on); await act(async () => { root.unmount(); });
});
