import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MarketAvailabilityNotice, TokenAvatar, tokenImageUrls } from './MarketPrimitives';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mount(pair) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<TokenAvatar pair={pair} />));
  return { host, root };
}

afterEach(() => {
  document.body.innerHTML = '';
});

test('uses provider image fields before the indexed token-image fallback', () => {
  const pair = {
    chainId: 'solana',
    baseToken: { address: 'mint-1', symbol: 'ALPHA', logoURI: 'https://provider.test/alpha.png' },
    info: { imageUrl: 'https://provider.test/alpha-info.png' },
  };
  expect(tokenImageUrls(pair)).toEqual([
    'https://provider.test/alpha-info.png',
    'https://provider.test/alpha.png',
    'https://dd.dexscreener.com/ds-data/tokens/solana/mint-1.png',
  ]);
  const { host, root } = mount(pair);
  expect(host.querySelector('img').getAttribute('src')).toBe('https://provider.test/alpha-info.png');
  act(() => root.unmount());
});

test('tries the indexed fallback before showing a neutral logo icon after image failure', () => {
  const { host, root } = mount({
    chainId: 'ethereum',
    baseToken: { address: '0xabc', symbol: 'BETA', logoURI: 'https://provider.test/beta.png' },
  });
  const image = host.querySelector('img');
  expect(image.getAttribute('src')).toBe('https://provider.test/beta.png');
  act(() => image.dispatchEvent(new Event('error')));
  expect(host.querySelector('img').getAttribute('src')).toBe('https://dd.dexscreener.com/ds-data/tokens/ethereum/0xabc.png');
  act(() => host.querySelector('img').dispatchEvent(new Event('error')));
  expect(host.querySelector('img')).toBeNull();
  expect(host.querySelector('.token-avatar-fallback svg')).toBeTruthy();
  expect(host.textContent).not.toContain('BE');
  act(() => root.unmount());
});

test('explains provider rate limits without hiding the available market snapshot', () => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<><MarketAvailabilityNotice
    data={{ provider: 'DexScreener', pairs: [{ pairAddress: 'fallback-pair' }], provider_warning: { provider: 'DexScreener', status: 429, rate_limited: true } }}
    id="market-rate-limit"
  /><span data-testid="fallback-row">fallback-pair</span></>));
  expect(host.querySelector('[data-testid="market-rate-limit"]').textContent).toMatch(/temporarily rate limited/i);
  expect(host.querySelector('[data-testid="market-rate-limit"]').textContent).toMatch(/next refresh/i);
  expect(host.querySelector('[data-testid="market-rate-limit"]').textContent).toMatch(/not a trading failure/i);
  expect(host.querySelector('[data-testid="fallback-row"]').textContent).toBe('fallback-pair');
  act(() => root.unmount());
});

test('explains provider-unavailable data when no fallback snapshot exists', () => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => root.render(<MarketAvailabilityNotice
    data={{ provider: 'Public providers', status: 'provider_unavailable' }}
    id="market-unavailable"
  />));
  expect(host.querySelector('[data-testid="market-unavailable"]').textContent).toMatch(/temporarily unavailable/i);
  expect(host.querySelector('[data-testid="market-unavailable"]').textContent).toMatch(/next refresh/i);
  act(() => root.unmount());
});