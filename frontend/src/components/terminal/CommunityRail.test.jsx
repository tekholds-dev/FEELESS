import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ChatRoom } from './CommunityRail';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockUseMarket = jest.fn();

jest.mock('react-router-dom', () => {
  const mockReact = require('react');
  return {
    Link: ({ children, ...props }) => mockReact.createElement('a', props, children),
  };
}, { virtual: true });

jest.mock('../../hooks/useMarket', () => ({
  useMarket: (...args) => mockUseMarket(...args),
}));

jest.mock('../../hooks/useWorkspace', () => ({
  useWorkspace: () => ({ ecosystem: { id: 'solana', name: 'Solana' } }),
}));

jest.mock('../EcosystemChat', () => () => <div data-testid="ecosystem-chat" />);
jest.mock('../command/WorkspaceChrome', () => ({ AlphaTape: () => null }));
jest.mock('./TokenFocus', () => ({ TokenFocus: () => null }));
jest.mock('./MarketPrimitives', () => ({
  TokenAvatar: ({ pair }) => <span>{pair.baseToken?.symbol}</span>,
  Change: ({ value }) => <span>{value ?? '—'}</span>,
}));

describe('The Trenches pools tab', () => {
  let root;
  let host;

  beforeEach(() => {
    mockUseMarket.mockReturnValue({
      data: {
        provider: 'DexScreener',
        pairs: [{
          chainId: 'solana',
          pairAddress: 'pool-1',
          baseToken: { symbol: 'ALPHA', name: 'Alpha Coin' },
          priceUsd: '1.25',
          priceChange: { h24: 4.5 },
          liquidity: { usd: 125000 },
          volume: { h24: 42000 },
        }],
      },
      loading: false,
      refreshing: false,
      error: undefined,
    });
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    mockUseMarket.mockReset();
  });

  test('shows live pool metrics and selects a realtime coin from its own tab', () => {
    const onSelect = jest.fn();
    act(() => root.render(<ChatRoom pairs={[]} onSelect={onSelect} />));

    act(() => host.querySelector('[data-testid="chat-tab-pools"]').click());

    expect(host.querySelector('[data-testid="live-pools-panel"]')).not.toBeNull();
    expect(host.querySelector('[data-testid="live-pools-count"]').textContent).toBe('1');
    expect(host.querySelector('[data-testid="live-pools-status"]').textContent).toContain('DexScreener');
    expect(host.querySelector('[data-testid="live-pool-solana-pool-1"]')).not.toBeNull();

    act(() => host.querySelector('[data-testid="live-pool-solana-pool-1"]').click());
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'pool-1' }));
  });
});