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
