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

jest.mock('./TokenCard', () => ({ pair, screenerLabel }) => {
  const signals = pair.signals || {};
  if (!signals.score_label && !screenerLabel) return <div data-testid="token-card">{pair.baseToken.symbol}</div>;
  return <div data-testid="token-card">
    <span data-testid="token-card-symbol">{pair.baseToken.symbol}</span>
    <span data-testid="token-card-label">{signals.score_label || screenerLabel || 'Unavailable'}</span>
    <span data-testid="token-card-score">{signals.screener_score}</span>
    <span data-testid="token-card-reasons">{(signals.score_reasons || []).join(' · ') || 'Observed reasons unavailable'}</span>
  </div>;
});

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

test('updates every radar coin label, score, and observed reasons for each screener mode', () => {
  const modes = [
    { value: 'quality', api: 'quality', label: 'Best observed setups', disclosure: 'quality disclosure' },
    { value: 'momentum', api: 'momentum', label: 'Momentum', disclosure: 'momentum disclosure' },
    { value: 'volume', api: 'volume', label: 'Volume leaders', disclosure: 'volume disclosure' },
    { value: 'new', api: 'new', label: 'Fresh with activity', disclosure: 'fresh disclosure' },
  ];
  const paths = mode => ({
    top: `/feed?kind=trending&chain=ethereum${mode.api === 'quality' ? '' : `&screen=${mode.api}`}`,
    fresh: `/feed?kind=new&chain=ethereum${mode.api === 'new' || mode.api === 'quality' ? '' : `&screen=${mode.api}`}`,
  });
  const response = (mode, symbol) => ({
    data: {
      screener: mode.api,
      screener_label: mode.label,
      screener_disclosure: mode.disclosure,
      pairs: [{
        pairAddress: `${mode.api}-${symbol}`,
        baseToken: { symbol },
        signals: {
          screener: mode.api,
          screener_score: mode.api === 'quality' ? 41.1 : mode.api === 'momentum' ? 72.2 : mode.api === 'volume' ? 83.3 : 94.4,
          score_label: mode.label,
          score_reasons: [`${mode.api} liquidity`, `${mode.api} volume`, `${mode.api} activity`],
        },
      }],
    },
    loading: false,
  });

  modes.forEach(mode => {
    const modePaths = paths(mode);
    marketResults[modePaths.top] = response(mode, 'TOP');
    const freshMode = mode.value === 'quality' ? modes[3] : mode;
    marketResults[modePaths.fresh] = response(freshMode, 'NEW');
  });

  const initial = renderFeeds(ecosystem, {
    top: marketResults[paths(modes[0]).top],
    new: marketResults[paths(modes[0]).fresh],
  });
  const select = initial.container.querySelector('[data-testid="coin-screener"]');

  modes.forEach(mode => {
    act(() => {
      select.value = mode.value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    const cards = [...initial.container.querySelectorAll('[data-testid="token-card"]')];
    expect(cards).toHaveLength(2);
    const freshMode = mode.value === 'quality' ? modes[3] : mode;
    expect(cards.map(card => card.querySelector('[data-testid="token-card-label"]').textContent)).toEqual([mode.label, freshMode.label]);
    const score = value => value.api === 'quality' ? '41.1' : value.api === 'momentum' ? '72.2' : value.api === 'volume' ? '83.3' : '94.4';
    expect(cards.map(card => card.querySelector('[data-testid="token-card-score"]').textContent)).toEqual(
      [score(mode), score(freshMode)],
    );
    expect(cards.map(card => card.querySelector('[data-testid="token-card-reasons"]').textContent)).toEqual([
      `${mode.api} liquidity · ${mode.api} volume · ${mode.api} activity`,
      `${freshMode.api} liquidity · ${freshMode.api} volume · ${freshMode.api} activity`,
    ]);
    expect(initial.container.querySelector('.provider-note').textContent).toContain(mode.value === 'quality' ? mode.disclosure : mode.disclosure);
  });
  act(() => initial.root.unmount());
});

test('does not show the previous radar mode while the next mode is refreshing', () => {
  const quality = {
    data: {
      screener: 'quality',
      screener_label: 'Best observed setups',
      pairs: [{ pairAddress: 'quality-pair', baseToken: { symbol: 'QUALITY' }, signals: { score_label: 'Best observed setups', screener_score: 40, score_reasons: ['quality reason'] } }],
    },
    loading: false,
  };
  const momentum = {
    data: {
      screener: 'quality',
      screener_label: 'Best observed setups',
      pairs: quality.data.pairs,
    },
    loading: false,
    refreshing: true,
  };
  const momentumReady = {
    data: {
      screener: 'momentum',
      screener_label: 'Momentum',
      pairs: [{ pairAddress: 'momentum-pair', baseToken: { symbol: 'MOMENTUM' }, signals: { score_label: 'Momentum', screener_score: 80, score_reasons: ['momentum reason'] } }],
    },
    loading: false,
  };
  const momentumPaths = {
    top: '/feed?kind=trending&chain=ethereum&screen=momentum',
    fresh: '/feed?kind=new&chain=ethereum&screen=momentum',
  };
  marketResults[momentumPaths.top] = momentum;
  marketResults[momentumPaths.fresh] = momentum;
  const { container, root } = renderFeeds(ecosystem, { top: quality, new: quality });
  const select = container.querySelector('[data-testid="coin-screener"]');

  act(() => {
    select.value = 'momentum';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="globe-coins-new-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="token-card"]')).toBeNull();

  marketResults[momentumPaths.top] = momentumReady;
  marketResults[momentumPaths.fresh] = momentumReady;
  act(() => root.render(<TopCoins ecosystem={ecosystem} />));
  expect(container.querySelector('[data-testid="token-card-label"]').textContent).toBe('Momentum');
  expect(container.querySelector('[data-testid="token-card-reasons"]').textContent).toBe('momentum reason');
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