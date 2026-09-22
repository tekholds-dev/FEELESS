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
  MarketError: () => null,
  TokenContextMeta: () => <span />,
  CreatorProfile: () => <span />,
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

  expect(mounted.host.querySelector('[data-testid="chart-metric-marketCap"]').disabled).toBe(false);
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('price');
  act(() => mounted.host.querySelector('[data-testid="chart-metric-marketCap"]').click());
  expect(mounted.host.querySelector('[data-testid="mock-price-chart"]').getAttribute('data-metric')).toBe('marketCap');
  expect(mounted.host.querySelector('[data-testid="token-analytics-snipers"]').textContent).toContain('Unavailable');
  act(() => mounted.root.unmount());
});

test('disables unsupported chart metrics instead of estimating them', () => {
  const mounted = mount({
    chainId: 'solana',
    pairAddress: 'pool-2',
    baseToken: { symbol: 'BETA', name: 'Beta' },
  });

  expect(mounted.host.querySelector('[data-testid="chart-metric-marketCap"]').disabled).toBe(true);
  expect(mounted.host.querySelector('[data-testid="chart-metric-fdv"]').disabled).toBe(true);
  expect(mounted.host.querySelector('[data-testid="token-analytics-holderConcentration"]').textContent).toContain('Unavailable');
  act(() => mounted.root.unmount());
});