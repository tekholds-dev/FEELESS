import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import TopCoins from './TopCoins';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const marketResults = {};

jest.mock('../hooks/useMarket', () => ({
  useMarket: path => marketResults[path],
}));

jest.mock('./terminal/MarketPrimitives', () => ({
  DataStatus: ({ data, id }) => <span data-testid={id}>{data ? 'LIVE' : 'CONNECTING'}</span>,
  MarketError: ({ error, reload, id, focusable, retryLabel }) => (
    <div data-testid={id} role="alert" tabIndex={focusable ? 0 : undefined}>
      <span>{error}</span>
      {reload && <button data-testid={`${id}-retry`} aria-label={retryLabel} onClick={reload}>Retry</button>}
    </div>
  ),
}));

jest.mock('./TokenCard', () => ({ pair }) => <div data-testid="token-card">{pair.baseToken.symbol}</div>);

const ecosystem = { id: 'ethereum', name: 'Ethereum', chainId: 'ethereum' };

function renderFeeds(results) {
  marketResults['/feed?kind=trending&chain=ethereum'] = results.top;
  marketResults['/feed?kind=new&chain=ethereum'] = results.new;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  delete marketResults['/feed?kind=trending&chain=ethereum'];
  delete marketResults['/feed?kind=new&chain=ethereum'];
});

test('names the ecosystem in loading and empty states for both feeds', () => {
  const { container, root } = renderFeeds({
    top: { data: undefined, loading: true },
    new: { data: { pairs: [] }, loading: false },
  });

  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]').textContent).toBe('Loading top coins for Ethereum…');
  const empty = container.querySelector('[data-testid="globe-coins-new-empty"]');
  expect(empty.textContent).toBe('No new coins available for Ethereum in this provider feed.');
  expect(empty.getAttribute('role')).toBe('status');
  expect(empty.getAttribute('tabindex')).toBe('0');
  act(() => root.unmount());
});

test('shows an ecosystem-specific, keyboard-reachable error without an empty state', () => {
  const reload = jest.fn();
  const { container, root } = renderFeeds({
    top: { data: undefined, loading: false, error: 'Provider unavailable', reload },
    new: { data: undefined, loading: false, error: 'Timed out', reload },
  });

  const topError = container.querySelector('[data-testid="globe-coins-trending-error"]');
  expect(topError.textContent).toContain('Unable to load top coins for Ethereum. Provider unavailable');
  expect(topError.getAttribute('role')).toBe('alert');
  expect(topError.getAttribute('tabindex')).toBe('0');
  expect(topError.querySelector('[data-testid="globe-coins-trending-error-retry"]').getAttribute('aria-label')).toBe('Retry top coins for Ethereum');
  expect(container.querySelector('[data-testid="globe-coins-trending-empty"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-empty"]')).toBeNull();
  act(() => root.unmount());
});