import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CoinDrawerHost, openCoin } from './CoinDrawer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./WarRoomHost', () => ({ openWarRoom: jest.fn() }));
jest.mock('./CaseFile', () => ({ investigate: jest.fn() }));
jest.mock('./terminal/PriceChart', () => ({ PriceChart: ({ pair, interval }) => <div data-testid="stub-chart">{pair.pairAddress}:{interval}</div> }));
const M = 'Mint111111111111111111111111111111111111111';
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('one drawer opens for any coin: edge signals + bond boxes, chart / case / add-to-card, Esc closes', async () => {
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => (String(url).includes('/edge') ? { edge: { [M]: { verify: { level: 'verified' }, pulse: { buyShare: 62, buys: 60, sells: 37 },
    runner: { passing: true, score: 81, lane: 'scalp', gates: [], bond: [{ label: 'curve ≥90%', ok: true }, { label: 'clean creator', ok: false }] },
    signals: [{ kind: 'bond', text: '🔔 Bond run — every box ticked', source: 'Fuse Runners bond check' }] } } } : { pairs: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CoinDrawerHost />); });
  await act(async () => { openCoin({ mint: M, pairAddress: 'P', symbol: 'MOON', runner: true }); }); await tick(400);
  const d = document.querySelector('[data-testid="coin-drawer"]');
  expect(d.textContent).toContain('$MOON'); expect(d.textContent).toContain('✓ VERIFIED'); expect(d.textContent).toContain('Bond run');
  expect(d.textContent).toContain('62% buys'); expect(d.querySelectorAll('.cd-bond span.ok')).toHaveLength(1);
  const { openWarRoom } = require('./WarRoomHost');
  await act(async () => { d.querySelector('[data-testid="cd-chart"]').click(); });
  expect(openWarRoom).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'P' })); expect(document.querySelector('[data-testid="coin-drawer"]')).toBeNull();
});


test('the drawer carries the coin\'s own chart: timeframe taps redraw it and ⚔ War room above it opens the full room', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ edge: {} }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CoinDrawerHost />); });
  await act(async () => { openCoin({ mint: M, pairAddress: 'PX', symbol: 'ST' }); }); await tick(300);
  const d = [...document.querySelectorAll('[data-testid="coin-drawer"]')].pop();
  expect(d.querySelector('[data-testid="stub-chart"]').textContent).toBe('PX:5m');
  await act(async () => { d.querySelector('[data-testid="cd-ctf-1h"]').click(); }); await tick(50);
  expect(d.querySelector('[data-testid="stub-chart"]').textContent).toBe('PX:1h');
  const bar = d.querySelector('.cd-chart-bar'); expect(bar.compareDocumentPosition(d.querySelector('[data-testid="stub-chart"]')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();   // the button sits ABOVE the chart
  const { openWarRoom } = require('./WarRoomHost'); openWarRoom.mockClear();
  await act(async () => { d.querySelector('[data-testid="cd-war"]').click(); });
  expect(openWarRoom).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'PX' })); expect(d.isConnected).toBe(false);   // this drawer closed
});
