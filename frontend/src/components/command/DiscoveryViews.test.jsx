import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PumpRadarCard } from './DiscoveryViews';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}), { virtual: true });

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