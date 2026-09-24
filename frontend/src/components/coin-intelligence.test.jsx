import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import TopCoins from './TopCoins';
import EcosystemPlatforms from './EcosystemPlatforms';
import { LAUNCHPADS, launchpadEcosystem } from '../lib/launchpads';

const mockMarketResponses = {};
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../hooks/useMarket', () => ({
  useMarket: path => mockMarketResponses[path],
}));

jest.mock('./TokenCard', () => function MockTokenCard({ pair, screenerLabel }) {
  return <div data-testid={`mock-token-${pair.baseToken?.symbol}`}><span>{pair.baseToken?.symbol}</span><small>{screenerLabel || 'Unavailable'}</small></div>;
});

jest.mock('./terminal/MarketPrimitives', () => ({
  DataStatus: ({ id }) => <span data-testid={id}>status</span>,
  MarketAvailabilityNotice: ({ id }) => <span data-testid={id} />,
  MarketError: ({ error, id }) => <div data-testid={id}>{error}</div>,
}));

function mount(element) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(element));
  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = '';
  Object.keys(mockMarketResponses).forEach(key => delete mockMarketResponses[key]);
});

const ecosystem = { id: 'solana', name: 'Solana', chainId: 'solana', isLaunchpad: false };

test('renders top and new provider feeds under the ecosystem intelligence view', () => {
  mockMarketResponses['/feed?kind=trending&chain=solana'] = {
    data: { pairs: [{ pairAddress: 'top-1', baseToken: { symbol: 'TOP' } }] },
    loading: false,
    error: '',
    reload: jest.fn(),
  };
  mockMarketResponses['/feed?kind=new&chain=solana'] = {
    data: { pairs: [{ pairAddress: 'new-1', baseToken: { symbol: 'NEW' }, info: { imageUrl: 'https://logo.test/new.png' } }] },
    loading: false,
    error: '',
    reload: jest.fn(),
  };

  const { container } = mount(<TopCoins ecosystem={ecosystem} />);

  expect(container.querySelector('[data-testid="globe-coins-trending"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="globe-coins-new"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-token-TOP"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="mock-token-NEW"]')).toBeTruthy();
});

test('passes each feed screener label to its coin cards', () => {
  mockMarketResponses['/feed?kind=trending&chain=solana'] = {
    data: { pairs: [{ pairAddress: 'top-1', baseToken: { symbol: 'TOP' } }], screener_label: 'Momentum' },
    loading: false,
    error: '',
  };
  mockMarketResponses['/feed?kind=new&chain=solana'] = {
    data: { pairs: [{ pairAddress: 'new-1', baseToken: { symbol: 'NEW' }, info: { imageUrl: 'https://logo.test/new.png' } }] },
    loading: false,
    error: '',
  };

  const { container } = mount(<TopCoins ecosystem={ecosystem} />);

  expect(container.querySelector('[data-testid="mock-token-TOP"] small').textContent).toBe('Momentum');
  expect(container.querySelector('[data-testid="mock-token-NEW"] small').textContent).toBe('Unavailable');
});

test('keeps provider loading, error, and empty states explicit', () => {
  mockMarketResponses['/feed?kind=trending&chain=solana'] = {
    data: undefined,
    loading: true,
    error: '',
    reload: jest.fn(),
  };
  mockMarketResponses['/feed?kind=new&chain=solana'] = {
    data: undefined,
    loading: false,
    error: 'Provider unavailable',
    reload: jest.fn(),
  };

  const { container } = mount(<TopCoins ecosystem={ecosystem} />);

  expect(container.querySelector('[data-testid="globe-coins-trending-loading"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="globe-coins-new-error"]').textContent).toContain('Provider unavailable');
});

test('does not crash when a launchpad has no configured platform URL', () => {
  const pump = LAUNCHPADS.find(pad => pad.id === 'pump');
  const { container } = mount(<EcosystemPlatforms ecosystem={launchpadEcosystem(pump)} />);

  expect(container.querySelector('[data-testid="ecosystem-official-unavailable-pump"]')).toBeTruthy();
  expect(container.querySelector('[data-testid="ecosystem-platform-unavailable-pump-0"]')).toBeTruthy();
});