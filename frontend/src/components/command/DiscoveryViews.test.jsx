import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PumpRadarCard, PumpRadarView } from './DiscoveryViews';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockMarketResponses = {};
const mockEcosystem = {
  id: 'pump',
  name: 'Pump.fun',
  chainId: 'solana',
  color: '#34efad',
  isLaunchpad: true,
};

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}), { virtual: true });

jest.mock('../../hooks/useMarket', () => ({
  useMarket: path => path?.startsWith('/graduations')
    ? mockMarketResponses.graduations
    : mockMarketResponses[path],
}));

jest.mock('../../hooks/useWorkspace', () => ({
  useWorkspace: () => ({ ecosystem: mockEcosystem, watchlist: [] }),
}));

jest.mock('./WorkspaceChrome', () => ({
  useClock: () => 1_700_000_000_000,
}));

const basePair = {
  chainId: 'solana',
  dexId: 'raydium',
  pairAddress: 'market-pair-1',
  pairCreatedAt: Date.now() - 3600000,
  baseToken: { address: 'Mint123', symbol: 'GRAD', name: 'Graduated Coin' },
  priceUsd: '1.25',
  priceChange: { h24: 12.4 },
  liquidity: { usd: 250000 },
  volume: { h24: 88000 },
  fdv: 1200000,
};

describe('PumpRadarCard graduation destination', () => {
  let host;
  let root;

  beforeEach(() => {
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  test('links the reported migration pool without using the market pair address', () => {
    act(() => root.render(
      <PumpRadarCard
        pair={{ ...basePair, graduation: { status: 'graduated', pool_address: 'RaydiumMigrationPool789' } }}
        rank={1}
        onSelect={() => {}}
      />,
    ));

    const link = host.querySelector('[data-testid="pump-radar-migration-solana-market-pair-1"] a');
    expect(link).not.toBeNull();
    expect(link.getAttribute('href')).toBe('https://solscan.io/account/RaydiumMigrationPool789');
    expect(link.textContent).toContain('Provider-reported destination');
    expect(link.textContent).toContain('Raydiu…l789');
    expect(link.getAttribute('aria-label')).toContain('RaydiumMigrationPool789');
  });

  test('shows an unavailable state when Pump.fun has no migration pool', () => {
    act(() => root.render(
      <PumpRadarCard
        pair={{ ...basePair, graduation: { status: 'graduated', pool_address: null } }}
        rank={1}
        onSelect={() => {}}
      />,
    ));

    expect(host.querySelector('[data-testid="pump-radar-migration-solana-market-pair-1"] a')).toBeNull();
    expect(host.querySelector('[data-testid="pump-radar-migration-unavailable-solana-market-pair-1"]').textContent)
      .toBe('Unavailable from Pump.fun');
  });
});

describe('PumpRadarView graduation status boundary', () => {
  let host;
  let root;

  beforeEach(() => {
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
    mockMarketResponses['/feed?kind=new&chain=solana&page=1&scope=pump'] = {
      data: {
        provider: 'Pump.fun',
        pairs: [
          { ...basePair, pairAddress: 'complete-pool', launchpadId: 'pump', baseToken: { address: 'MintComplete', symbol: 'DONE', name: 'Complete Coin' }, marketStage: 'new' },
          { ...basePair, pairAddress: 'pending-pool', launchpadId: 'pump', baseToken: { address: 'MintPending', symbol: 'WAIT', name: 'Pending Coin' }, marketStage: 'new' },
          { ...basePair, pairAddress: 'failed-pool', launchpadId: 'pump', baseToken: { address: 'MintFailed', symbol: 'FAIL', name: 'Failed Coin' }, marketStage: 'new' },
        ],
      },
      loading: false,
      refreshing: false,
      error: null,
      reload: jest.fn(),
    };
    mockMarketResponses['/feed?kind=trending&chain=solana&page=1&scope=pump'] = {
      data: { provider: 'Pump.fun', pairs: [] },
      loading: false,
      refreshing: false,
      error: null,
      reload: jest.fn(),
    };
    mockMarketResponses.graduations = {
      data: {
        provider: 'Pump.fun',
        source_label: 'Pump.fun public coin status · complete=true',
        fetched_at: '2026-09-22T12:34:56+00:00',
        status: 'verified',
        error: 'MintFailed: Pump.fun returned 503',
        graduations: [
          { mint: 'MintComplete', status: 'graduated', pool_address: 'ObservedPool' },
          { mint: 'MintPending', status: 'pending' },
          { mint: 'MintFailed', status: 'error' },
          { mint: 'MintNotObserved', status: 'graduated' },
        ],
      },
      loading: false,
      refreshing: false,
      error: null,
      reload: jest.fn(),
    };
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    Object.keys(mockMarketResponses).forEach(key => delete mockMarketResponses[key]);
  });

  test('shows only completed observed pools and preserves mixed status provenance', () => {
    act(() => root.render(<PumpRadarView newFeed={mockMarketResponses['/feed?kind=new&chain=solana&page=1&scope=pump']} trendingFeed={mockMarketResponses['/feed?kind=trending&chain=solana&page=1&scope=pump']} onSelect={() => {}} />));
    act(() => host.querySelector('[data-testid="pump-radar-stage-graduated"]').click());

    expect(host.querySelector('[data-testid="pump-radar-card-solana-complete-pool"]')).not.toBeNull();
    expect(host.querySelector('[data-testid="pump-radar-card-solana-pending-pool"]')).toBeNull();
    expect(host.querySelector('[data-testid="pump-radar-card-solana-failed-pool"]')).toBeNull();
    expect(host.querySelectorAll('[data-testid^="pump-radar-card-"]')).toHaveLength(1);

    const source = host.querySelector('[data-testid="pump-radar-graduation-source"]').textContent;
    expect(source).toContain('Pump.fun public coin status · complete=true');
    expect(source).toContain('Error: MintFailed: Pump.fun returned 503');
    expect(source).toContain('Observed');
    expect(host.querySelector('.pump-radar-summary').textContent).toContain('STATUS OBSERVED');
  });
});
