import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CandleFx } from './CandleFx';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('⚡ candle fx draws one aura, one tick ring, one open flash and six sparks — and never asks the page for input', async () => {
  const ref = v => ({ current: v });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CandleFx seriesRef={ref(null)} chartRef={ref(null)} lastBarRef={ref(null)} shownRef={ref(null)} container={ref(null)} />); });
  const fx = el.querySelector('[data-testid="candle-fx"]');
  expect(fx.getAttribute('aria-hidden')).toBe('true');
  expect(fx.querySelectorAll('.cfk-aura, .cfk-ring, .cfk-open').length).toBe(3);
  expect(fx.querySelectorAll('.cfk-spark b').length).toBe(6);
  await act(async () => { root.unmount(); });
});
