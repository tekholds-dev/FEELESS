import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TokenFocus } from './TokenFocus';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseMarket = jest.fn();
jest.mock('../../hooks/useMarket', () => ({
  useMarket: (...args) => mockUseMarket(...args),
}));
jest.mock('../../hooks/useWorkspace', () => ({
  useWorkspace: () => ({ selectPair: jest.fn() }),
}));
jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}), { virtual: true });
jest.mock('./ChartBoundary', () => ({ ChartBoundary: ({ children }) => <>{children}</> }));
jest.mock('./PriceChart', () => ({ PriceChart: ({ metric }) => <div data-testid="mock-price-chart" data-metric={metric} /> }));
jest.mock('./MarketPrimitives', () => ({
  Change: () => <span />,
  Metric: ({ label, value, id }) => <span data-testid={id}>{label}:{value}</span>,
  TokenAvatar: () => <span />,
  DataStatus: () => <span />,
  MarketAvailabilityNotice: () => null,
  MarketError: () => null,
  TokenContextMeta: () => <span />,
  CreatorProfile: () => <span />,
  getRankingContext: (pair, fallback = {}) => {
    const signals = pair?.signals || {};
    const context = pair?.rankingContext || {};
    return {
      label: signals.score_label || context.label || pair?.screener_label || fallback.label || null,
      score: signals.screener_score ?? context.score ?? null,
      reasons: (signals.score_reasons || context.reasons || []).slice(0, 3),
      provider: context.provider || fallback.provider || null,
      sourceLabel: context.sourceLabel || fallback.sourceLabel || null,
      stale: context.stale ?? fallback.stale ?? null,
    };
  },
}));

function mount(pair) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<TokenFocus pair={pair} has={() => false} toggle={() => {}} />));
  return { host, root };
}

beforeEach(() => {
  mockUseMarket.mockReturnValue({ data: undefined, error: undefined, loading: false, reload: jest.fn() });
});

afterEach(() => {
  document.body.innerHTML = '';
  mockUseMarket.mockReset();
});

test('switches to provider-supplied market cap without changing candle data', () => {
  const mounted = mount({
    chainId: 'solana',
    pairAddress: 'pool-1',
    baseToken: { symbol: 'ALPHA', name: 'Alpha' },
    marketCap: '1000000',
    fdv: '1200000',
  });

  const toggle = mounted.host.querySelector('[data-testid="chart-metric-switch"]');
  expect(toggle.disabled).toBe(false);
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('price');
  act(() => toggle.click());
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('marketCap');
  act(() => toggle.click());
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('fdv');
  act(() => toggle.click());
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('price');
  expect(mounted.host.querySelector('[data-testid="token-analytics-snipers"]').textContent).toContain('Unavailable');
  act(() => mounted.root.unmount());
});

test('shows the FEELESS Edge Score from real pair data', () => {
  const mounted = mount({
    chainId: 'ethereum',
    pairAddress: 'pool-3',
    baseToken: { symbol: 'GAMMA', name: 'Gamma' },
    txns: { h1: { buys: 80, sells: 20 }, h24: { buys: 900, sells: 600 } },
    priceChange: { h1: 5, h6: 12 },
    liquidity: { usd: 500000 },
    marketCap: 2000000,
  });
  const edge = mounted.host.querySelector('[data-testid="edge-score"]');
  expect(edge).not.toBeNull();
  expect(edge.textContent).toContain('80% buys in the last hour');
  expect(edge.textContent).toContain('25.0% of market cap');
  expect(edge.textContent).toContain('Not financial advice');
  act(() => mounted.root.unmount());
});

test('computeEdge excludes missing signals instead of guessing and zeroes flagged creators', () => {
  const { computeEdge } = require('./EdgeScore');
  const empty = computeEdge({ chainId: 'base' }, null, null, null);
  expect(empty.total).toBeNull();
  expect(empty.factors.every(f => f[2] == null)).toBe(true);
  const flagged = computeEdge({ chainId: 'base', txns: { h1: { buys: 90, sells: 10 } } }, { score: 70, badge: 'flagged', tokenCount: 5 }, null, null);
  expect(flagged.factors.find(f => f[0] === 'Creator trust')[2]).toBe(0);
  expect(flagged.factors.find(f => f[0] === 'Order flow')[2]).toBe(100);
  const dead = computeEdge({ chainId: 'base', priceChange: { h1: 0, h6: 0, h24: -98 }, liquidity: { usd: 5000 }, marketCap: 4500, txns: { h24: { buys: 9000, sells: 9000 } } }, null, null, null);
  expect(dead.total).toBeLessThanOrEqual(30);
  expect(dead.factors.find(f => f[0] === 'Liquidity depth')[2]).toBe(15);
});

test('disables unsupported chart metrics instead of estimating them', () => {
  const mounted = mount({
    chainId: 'solana',
    pairAddress: 'pool-2',
    baseToken: { symbol: 'BETA', name: 'Beta' },
  });

  expect(mounted.host.querySelector('[data-testid="chart-metric-switch"]').disabled).toBe(true);
  expect(mounted.host.querySelector('[data-testid="chart-metric-active"]').textContent).toMatch(/price/i);
  expect(mounted.host.querySelector('[data-testid="edge-score"]').textContent).toContain('n/a');
  expect(mounted.host.querySelector('[data-testid="token-analytics-holders"]').textContent).toContain('Unavailable');
  act(() => mounted.root.unmount());
});

test('shows the external Pump action only for valid Solana token addresses', () => {
  const mint = '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump';
  const solana = mount({
    chainId: 'solana', pairAddress: 'pool-4',
    baseToken: { address: mint, symbol: 'FEE', name: 'FEELESS' },
  });
  const pump = solana.host.querySelector('[data-testid="selected-token-pump-link"]');
  expect(pump?.getAttribute('href')).toBe(`https://pump.fun/coin/${mint}`);
  expect(pump?.getAttribute('rel')).toContain('noopener');
  act(() => solana.root.unmount());
  solana.host.remove();

  const otherChain = mount({
    chainId: 'ethereum', pairAddress: 'pool-5',
    baseToken: { address: mint, symbol: 'FEE' },
  });
  expect(otherChain.host.querySelector('[data-testid="selected-token-pump-link"]')).toBeNull();
  act(() => otherChain.root.unmount());
  otherChain.host.remove();

  const invalid = mount({
    chainId: 'solana', pairAddress: 'pool-6',
    baseToken: { address: 'not-a-token', symbol: 'BAD' },
  });
  expect(invalid.host.querySelector('[data-testid="selected-token-pump-link"]')).toBeNull();
  act(() => invalid.root.unmount());
});
