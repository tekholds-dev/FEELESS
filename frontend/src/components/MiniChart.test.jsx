import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./terminal/PriceChart', () => ({ PriceChart: ({ pair, interval, fuse, userEntry, metric }) => <div data-testid="stub-chart" data-metric={metric} data-fuse={fuse?.entry || ''} data-me={userEntry || ''}>{pair.pairAddress}:{interval}</div> }));
jest.mock('./terminal/TrenchChart', () => ({ useMyPosition: pair => [pair.pairAddress === 'PX' ? { tokensHeld: 5, avgEntry: 0.001, trades: [{ ts: 1, side: 'buy' }] } : null, false] }));
jest.mock('./ArenaPrime', () => ({ usePrime: () => ({ cfg: { sl: 15, rideAt: 15 }, cards: [{ label: '🔥 Prime Blaze', legs: [{ pairAddress: 'PX', entry: 0.0011 }] }] }),
  fuseLevels: (l, cf, label) => ({ card: label, entry: l.entry, stop: l.entry * 0.85, lock: l.entry * 1.15 }) }));
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => <i /> }));
jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map([['PX', { price: 0.00123, m5: 4.2, mc: 1230000 }]]) }));
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
  // it opens on MARKET CAP (like the war room): header + chart + the strip's levels all read in MC; one tap shows price
  expect(m().textContent).toContain('$1.23M MC'); expect(m().querySelector('[data-testid="stub-chart"]').dataset.metric).toBe('marketCap');
  expect(m().querySelector('[data-testid="mch-strip"]').textContent).toContain('$1.10M');
  await act(async () => { m().querySelector('[data-testid="mch-metric"]').click(); }); await tick(20);
  expect(m().querySelector('[data-testid="stub-chart"]').dataset.metric).toBe('price');
  expect(closed).toHaveBeenCalled(); expect(m().textContent).toContain('$ST'); expect(m().textContent).toContain('$0.00123'); expect(m().textContent).toContain('+4.2%');
  expect(m().querySelector('[data-testid="stub-chart"]').textContent).toBe('PX:5m');
  // the mini chart draws the Fuse card's lines (found on the live cards by coin) AND your own trade entry, and says where you stand
  expect(m().querySelector('[data-testid="stub-chart"]').dataset.fuse).toBe('0.0011'); expect(m().querySelector('[data-testid="stub-chart"]').dataset.me).toBe('0.001');
  const strip = m().querySelector('[data-testid="mch-strip"]').textContent;
  for (const x of ['⚛', '$0.0011', '+11.8%', '🛑', '❄', '👤', '$0.001', '+23.0%']) expect(strip).toContain(x);
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
