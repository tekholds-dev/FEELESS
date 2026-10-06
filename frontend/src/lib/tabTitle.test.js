import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { useTabTitle, chartTitle, cardTitle } from './tabTitle';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const T = ({ text }) => { useTabTitle(text); return null; };

test('the tab title shows the open chart / card, the last one wins and the page title comes back', async () => {
  document.title = 'FEELESS';
  expect(chartTitle({ baseToken: { symbol: 'IOF' }, priceUsd: 0.000234, marketCap: 4400000 })).toBe('$IOF $4.40M MC · $0.000234');
  expect(chartTitle({ baseToken: { symbol: 'X' }, priceUsd: 0 })).toBe('');
  expect(cardTitle('Prime Blaze', -3.31, -66.2)).toBe('▼ −$3.31 (-66.2%) · Prime Blaze');
  expect(cardTitle('Prime Blaze', 0.4, 8)).toBe('▲ +$0.40 (+8.0%) · Prime Blaze');
  const a = document.createElement('div'); const b = document.createElement('div');
  const ra = createRoot(a); const rb = createRoot(b);
  await act(async () => { ra.render(<T text="card" />); });
  expect(document.title).toBe('card');
  await act(async () => { rb.render(<T text="chart" />); });
  expect(document.title).toBe('chart');
  await act(async () => { rb.unmount(); });
  expect(document.title).toBe('card');
  await act(async () => { ra.unmount(); });
  expect(document.title).toBe('FEELESS');
});
