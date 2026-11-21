import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

const mockTrades = { trades: [] };
jest.mock('../../lib/tradeStream', () => ({ useTradeStream: () => mockTrades }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { address: 'MeWa11et' } }) }));
// eslint-disable-next-line import/first
import { TradeTape, whaleCut } from './TradeTape';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const ts = new Date().toISOString();

test('whales are ≥ $1K and ≥ 5× the median trade', () => {
  expect(whaleCut([{ usd: 10 }, { usd: 20 }, { usd: 30 }])).toBe(1000);
  expect(whaleCut([{ usd: 900 }, { usd: 1000 }, { usd: 1100 }])).toBe(5000);
});

test('tape flags whales, marks your trade, and opens any other wallet\'s case file', () => {
  mockTrades.trades = [
    { tx: 't1', kind: 'buy', usd: 25000, price: 0.01, wallet: 'Wha1eWa11et99', ts },
    { tx: 't2', kind: 'sell', usd: 40, price: 0.01, wallet: 'MeWa11et', ts },
    { tx: 't3', kind: 'buy', usd: 60, price: 0.01, wallet: 'Sma11Wa11et77', ts },
  ];
  const opened = [];
  window.addEventListener('feeless:investigate', e => opened.push(e.detail));
  const host = document.createElement('div'); document.body.appendChild(host);
  act(() => createRoot(host).render(<TradeTape pair={{ chainId: 'solana', pairAddress: 'P' }} />));
  const rows = [...host.querySelectorAll('[data-testid="tape-row"]')];
  expect(rows[0].className).toContain('is-whale');
  expect(rows[2].className).not.toContain('is-whale');
  expect(rows[1].className).toContain('is-mine');
  expect(rows[1].querySelector('.tape-case')).toBeNull();
  expect(rows[0].querySelector('a').getAttribute('href')).toBe('https://solscan.io/tx/t1');
  expect(host.querySelector('.trade-tape-head small').textContent).toContain('100% buys');
  act(() => rows[0].querySelector('.tape-case').click());
  expect(opened).toEqual(['Wha1eWa11et99']);
});

test('🔁 the tape card flips to the Flow read (same trades) with 60s / 5m / 15m, and remembers the side', () => {
  localStorage.removeItem('feeless.tapeFace'); localStorage.removeItem('feeless.flowWin');
  mockTrades.trades = [{ tx: 'f1', kind: 'buy', usd: 50, price: 0.01, wallet: 'AAAAwallet', ts }, { tx: 'f2', kind: 'sell', usd: 30, price: 0.01, wallet: 'BBBBwallet', ts }];
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<TradeTape pair={{ chainId: 'solana', pairAddress: 'P' }} />));
  expect(host.querySelectorAll('[data-testid="tape-row"]')).toHaveLength(2); expect(host.querySelector('[data-testid="trench-pulse"]')).toBeNull();
  act(() => host.querySelector('[data-testid="tape-flip"]').click());
  expect(host.querySelector('[data-testid="trench-pulse"]')).not.toBeNull(); expect(host.querySelector('[data-testid="tpl-word"]').textContent).toContain('THIN');
  act(() => host.querySelector('[data-testid="flow-win-900"]').click());
  expect(localStorage.getItem('feeless.flowWin')).toBe('900'); expect(host.textContent).toContain('PRICE 15m');
  act(() => root.unmount());
  const again = createRoot(host); act(() => again.render(<TradeTape pair={{ chainId: 'solana', pairAddress: 'P' }} />));
  expect(host.querySelector('[data-testid="trench-pulse"]')).not.toBeNull();   // it opens on the side you left it
  act(() => host.querySelector('[data-testid="tape-flip"]').click()); expect(host.querySelectorAll('[data-testid="tape-row"]')).toHaveLength(2);
  act(() => again.unmount()); host.remove();
});

test('📡 a dead trade feed says so on both faces, never a calm "QUIET"', () => {
  localStorage.removeItem('feeless.tapeFace'); mockTrades.trades = []; mockTrades.feed = { state: 'down', error: 'provider unavailable' };
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<TradeTape pair={{ chainId: 'solana', pairAddress: 'P' }} />));
  expect(host.querySelector('.trade-tape-head small').textContent).toBe('trade feed down (provider unavailable): no trades shown');
  act(() => host.querySelector('[data-testid="tape-flip"]').click());
  expect(host.querySelector('[data-testid="flow-dead"]').textContent).toContain('calls nothing'); expect(host.querySelector('[data-testid="tpl-word"]')).toBeNull();
  act(() => root.unmount()); host.remove(); delete mockTrades.feed;
});
