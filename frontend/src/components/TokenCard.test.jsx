import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import TokenCard from './TokenCard';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('./terminal/MarketPrimitives', () => ({
  TokenAvatar: () => <span data-testid="token-avatar" />,
  withRankingContext: (pair, fallback = {}) => ({
    ...pair,
    rankingContext: { ...(pair.rankingContext || {}), label: pair.signals?.score_label || fallback.label || null },
  }),
}));

function mount(pair, props = {}) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<TokenCard pair={pair} testId="coin-card" {...props} />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
});

test('shows the screener label, score, and no more than three observed reasons', () => {
  const { container } = mount({
    chainId: 'solana',
    pairAddress: 'pair-1',
    baseToken: { symbol: 'TEST' },
    signals: {
      score_label: 'Momentum',
      screener_score: 81.4,
      score_reasons: ['92 liquidity', '88 volume', '300 reported txns', '2h old'],
    },
  });

  expect(container.querySelector('[data-testid="coin-card-score-label"]').textContent).toBe('Momentum');
  expect(container.querySelector('[data-testid="coin-card-score"]').textContent).toBe('81.4');
  expect(container.querySelector('[data-testid="coin-card-score-reasons"]').textContent)
    .toBe('92 liquidity · 88 volume · 300 reported txns');
});

test('marks screener evidence unavailable when provider signals are missing', () => {
  const { container } = mount({ chainId: 'solana', pairAddress: 'pair-2', baseToken: { symbol: 'UNKNOWN' } }, { screenerLabel: 'Volume leaders' });

  expect(container.querySelector('[data-testid="coin-card-score-label"]').textContent).toBe('Volume leaders');
  expect(container.querySelector('[data-testid="coin-card-score-reasons"]').textContent).toBe('Observed reasons unavailable');
});

test('carries the feed label into the selected pair', () => {
  const onSelect = jest.fn();
  const { container } = mount(
    { chainId: 'solana', pairAddress: 'pair-3', baseToken: { symbol: 'SELECTED' } },
    { screenerLabel: 'Volume leaders', onSelect },
  );

  act(() => container.querySelector('[data-testid="coin-card"]').click());
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({
    rankingContext: expect.objectContaining({ label: 'Volume leaders' }),
  }));
});