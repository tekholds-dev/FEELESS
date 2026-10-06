import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./terminal/PriceChart', () => ({ PriceChart: ({ pair, interval }) => <div data-testid="stub-chart">{pair.pairAddress}:{interval}</div> }));
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => <i /> }));
jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map([['PX', { price: 0.00123, m5: 4.2 }]]) }));
jest.mock('./WarRoomHost', () => ({ openWarRoom: jest.fn() }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('mini chart: opens from any chart, closes the room it came from, survives a remount (any page), reopens the war room, and closes', async () => {
  window.localStorage.clear();
  const { MiniChartHost, openMiniChart } = require('./MiniChart'); const { openWarRoom } = require('./WarRoomHost');
  const closed = jest.fn(); window.addEventListener('feeless:mini-chart', closed);      // what EcosystemWorld listens to
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<MiniChartHost />); });
  expect(document.querySelector('[data-testid="mini-chart"]')).toBeNull();
  await act(async () => { openMiniChart({ chainId: 'solana', pairAddress: 'PX', baseToken: { address: 'MX', symbol: 'ST' } }); }); await tick(50);
  const m = () => document.querySelector('[data-testid="mini-chart"]');
  expect(closed).toHaveBeenCalled(); expect(m().textContent).toContain('$ST'); expect(m().textContent).toContain('$0.001230'); expect(m().textContent).toContain('+4.2%');
  expect(m().querySelector('[data-testid="stub-chart"]').textContent).toBe('PX:5m');
  await act(async () => { m().querySelector('[data-testid="mch-tf-1m"]').click(); }); await tick(20);
  expect(m().querySelector('[data-testid="stub-chart"]').textContent).toBe('PX:1m');
  await act(async () => { root.unmount(); });                                             // leave the page…
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<MiniChartHost />); }); await tick(50);
  expect(m().textContent).toContain('$ST');                                               // …the chart is still there on the next one
  await act(async () => { m().querySelector('[data-testid="mch-war"]').click(); });
  expect(openWarRoom).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'PX' }));
  await act(async () => { m().querySelector('[data-testid="mch-close"]').click(); });
  expect(m()).toBeNull(); expect(window.localStorage.getItem('feeless.miniChart')).toBeNull();
});
