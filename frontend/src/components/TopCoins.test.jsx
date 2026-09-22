import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import TopCoins from './TopCoins';
import { ECOSYSTEMS } from '../lib/ecosystems';

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
const selectableEcosystems = ECOSYSTEMS.filter(item => !item.isFeeless);

function renderFeeds(selectedEcosystem, results) {
  marketResults[`/feed?kind=trending&chain=${selectedEcosystem.chainId}`] = results.top;
  marketResults[`/feed?kind=new&chain=${selectedEcosystem.chainId}`] = results.new;
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<TopCoins ecosystem={selectedEcosystem} />));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  Object.keys(marketResults).forEach(path => delete marketResults[path]);
});

selectableEcosystems.forEach(selectedEcosystem => {
  test(`names ${selectedEcosystem.name} in loading states for both feeds`, () => {
    const { container, root } = renderFeeds(selectedEcosystem, {
      top: { data: undefined, loading: true },
      new: { data: undefined, loading: true },
    });

    expect(container.querySelector('[data-testid="globe-coins-trending-loading"]').textContent)
      .toBe(`Loading top coins for ${selectedEcosystem.name}…`);
    expect(container.querySelector('[data-testid="globe-coins-new-loading"]').textContent)
      .toBe(`Loading new coins for ${selectedEcosystem.name}…`);
    act(() => root.unmount());
  });

  test(`names ${selectedEcosystem.name} in empty states and keeps them focusable`, () => {
    const { container, root } = renderFeeds(selectedEcosystem, {
      top: { data: { pairs: [] }, loading: false },
      new: { data: { pairs: [] }, loading: false },
    });

    const topEmpty = container.querySelector('[data-testid="globe-coins-trending-empty"]');
    const newEmpty = container.querySelector('[data-testid="globe-coins-new-empty"]');
    expect(topEmpty.textContent).toBe(`No top coins available for ${selectedEcosystem.name} in this provider feed.`);
    expect(newEmpty.textContent).toBe(`No new coins available for ${selectedEcosystem.name} in this provider feed.`);
    expect(topEmpty.getAttribute('role')).toBe('status');
    expect(newEmpty.getAttribute('role')).toBe('status');
    expect(topEmpty.getAttribute('tabindex')).toBe('0');
    expect(newEmpty.getAttribute('tabindex')).toBe('0');

    act(() => topEmpty.focus());
    expect(document.activeElement).toBe(topEmpty);
    act(() => newEmpty.focus());
    expect(document.activeElement).toBe(newEmpty);
    act(() => root.unmount());
  });
});

test('names the ecosystem in loading and empty states for both feeds', () => {
  const { container, root } = renderFeeds(ecosystem, {
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
  const { container, root } = renderFeeds(ecosystem, {
    top: { data: undefined, loading: false, error: 'Provider unavailable', reload },
    new: { data: undefined, loading: false, error: 'Timed out', reload },
  });

  const topError = container.querySelector('[data-testid="globe-coins-trending-error"]');
  expect(topError.textContent).toContain('Unable to load top coins for Ethereum. Provider unavailable');
  expect(topError.getAttribute('role')).toBe('alert');
  expect(topError.getAttribute('tabindex')).toBe('0');
  expect(topError.querySelector('[data-testid="globe-coins-trending-error-retry"]').getAttribute('aria-label')).toBe('Retry top coins for Ethereum');
  const newError = container.querySelector('[data-testid="globe-coins-new-error"]');
  expect(newError.textContent).toContain('Unable to load new coins for Ethereum. Timed out');
  expect(newError.getAttribute('role')).toBe('alert');
  expect(newError.getAttribute('tabindex')).toBe('0');
  act(() => newError.focus());
  expect(document.activeElement).toBe(newError);
  expect(newError.querySelector('[data-testid="globe-coins-new-error-retry"]').getAttribute('aria-label')).toBe('Retry new coins for Ethereum');
  expect(container.querySelector('[data-testid="globe-coins-trending-empty"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-empty"]')).toBeNull();
  act(() => root.unmount());
});

test('recovers one feed after retry without disrupting the other feed', () => {
  const topPath = '/feed?kind=trending&chain=ethereum';
  const newPath = '/feed?kind=new&chain=ethereum';
  const recoveredTopPair = { pairAddress: 'recovered-top', baseToken: { symbol: 'TOP' } };
  const newPair = { pairAddress: 'available-new', baseToken: { symbol: 'NEW' } };
  const topReload = jest.fn(() => {
    marketResults[topPath] = { data: undefined, loading: true, reload: topReload };
  });

  const { container, root } = renderFeeds(ecosystem, {
    top: { data: undefined, loading: false, error: 'Provider unavailable', reload: topReload },
    new: { data: { pairs: [newPair] }, loading: false },
  });

  const retry = container.querySelector('[data-testid="globe-coins-trending-error-retry"]');
  expect(retry.tagName).toBe('BUTTON');
  expect(retry.getAttribute('aria-label')).toBe('Retry top coins for Ethereum');
  act(() => retry.focus());
  expect(document.activeElement).toBe(retry);
  expect(container.querySelector('[data-testid="token-card"]').textContent).toBe('NEW');

  act(() => retry.click());
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));

  expect(topReload).toHaveBeenCalledTimes(1);
  expect(container.querySelector('[data-testid="globe-coins-trending-error"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]').textContent)
    .toBe('Loading top coins for Ethereum…');
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).toBeNull();
  expect(container.querySelector('[data-testid="token-card"]').textContent).toBe('NEW');

  marketResults[topPath] = { data: { pairs: [recoveredTopPair] }, loading: false, reload: topReload };
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));

  expect(container.querySelector('[data-testid="globe-coins-trending-error"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).toBeNull();
  expect([...container.querySelectorAll('[data-testid="token-card"]')].map(card => card.textContent))
    .toEqual(['TOP', 'NEW']);
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).toBeNull();
  act(() => root.unmount());
});

test('keeps simultaneous top and new feed retries independent when responses return out of order', () => {
  const topPath = '/feed?kind=trending&chain=ethereum';
  const newPath = '/feed?kind=new&chain=ethereum';
  const topPair = { pairAddress: 'top-recovered', baseToken: { symbol: 'TOP' } };
  const newPair = { pairAddress: 'new-recovered', baseToken: { symbol: 'NEW' } };
  const topReload = jest.fn(() => {
    marketResults[topPath] = { data: undefined, loading: true, reload: topReload };
  });
  const newReload = jest.fn(() => {
    marketResults[newPath] = { data: undefined, loading: true, reload: newReload };
  });

  const { container, root } = renderFeeds(ecosystem, {
    top: { data: undefined, loading: false, error: 'Top provider unavailable', reload: topReload },
    new: { data: undefined, loading: false, error: 'New provider unavailable', reload: newReload },
  });

  const topRetry = container.querySelector('[data-testid="globe-coins-trending-error-retry"]');
  const newRetry = container.querySelector('[data-testid="globe-coins-new-error-retry"]');
  expect(topRetry).not.toBeNull();
  expect(newRetry).not.toBeNull();

  act(() => topRetry.click());
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).not.toBeNull();

  act(() => newRetry.click());
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  expect(topReload).toHaveBeenCalledTimes(1);
  expect(newReload).toHaveBeenCalledTimes(1);
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-trending-error"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).toBeNull();

  marketResults[newPath] = { data: { pairs: [newPair] }, loading: false, reload: newReload };
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-loading"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).toBeNull();
  expect([...container.querySelectorAll('[data-testid="token-card"]')].map(card => card.textContent)).toEqual(['NEW']);

  marketResults[topPath] = { data: { pairs: [topPair] }, loading: false, reload: topReload };
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-loading"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-trending-error"]')).toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-error"]')).toBeNull();
  expect([...container.querySelectorAll('[data-testid="token-card"]')].map(card => card.textContent)).toEqual(['TOP', 'NEW']);
  act(() => root.unmount());
});

selectableEcosystems.forEach(selectedEcosystem => {
  test(`names ${selectedEcosystem.name} in error states and keeps them focusable`, () => {
    const reload = jest.fn();
    const { container, root } = renderFeeds(selectedEcosystem, {
      top: { data: undefined, loading: false, error: 'Provider unavailable', reload },
      new: { data: undefined, loading: false, error: 'Timed out', reload },
    });

    const topError = container.querySelector('[data-testid="globe-coins-trending-error"]');
    const newError = container.querySelector('[data-testid="globe-coins-new-error"]');
    expect(topError.textContent).toContain(`Unable to load top coins for ${selectedEcosystem.name}. Provider unavailable`);
    expect(newError.textContent).toContain(`Unable to load new coins for ${selectedEcosystem.name}. Timed out`);
    expect(topError.getAttribute('role')).toBe('alert');
    expect(newError.getAttribute('role')).toBe('alert');
    expect(topError.getAttribute('tabindex')).toBe('0');
    expect(newError.getAttribute('tabindex')).toBe('0');

    act(() => topError.focus());
    expect(document.activeElement).toBe(topError);
    act(() => newError.focus());
    expect(document.activeElement).toBe(newError);
    act(() => root.unmount());
  });
});