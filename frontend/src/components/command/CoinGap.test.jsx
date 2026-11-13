import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CoinGap, routeHitsCheap } from './CoinGap';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/sharedJson', () => ({ sharedJson: jest.fn(), _resetShared: () => {} }));
const { sharedJson } = require('../../lib/sharedJson');

const P = (dex, at, px) => ({ dex, pair: `P${dex}${at}`, px, liq: 200000, vs: 'SOL', at });
const GAP = { mint: 'JUP', sym: 'JUP', n: 3, lo: P('raydium', 0, 0.2524), hi: P('meteora', 0.71, 0.2542), gapPct: 0.713, netPct: 0.113, open: false, openSec: 0,
  pools: [P('raydium', 0, 0.2524), P('orca', 0.04, 0.2525), P('meteora', 0.71, 0.2542)] };
const mount = async ui => { const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); await act(async () => { root.render(ui); }); return { el, root }; };

test('📐 SITE-11: the coin being bought is drawn across its real pools before you buy, and the open quote is checked against the cheap pool', async () => {
  sharedJson.mockResolvedValue({ mint: 'JUPmint', gap: GAP, pools: 30, realPools: 3, cost: 0.3, answered: true });
  const quote = { routePlan: [{ swapInfo: { label: 'Raydium CLMM' } }] };
  const { el, root } = await mount(<CoinGap mint="JUPmint" quote={quote} />);
  expect(sharedJson.mock.calls[0][0]).toBe('/api/reputation/price-gap/JUPmint');
  expect(el.querySelectorAll('[data-testid="gp-row"]')).toHaveLength(1);
  expect(el.textContent).toContain('3/30'); expect(el.textContent).toContain('raydium → meteora');
  expect(el.querySelector('[data-testid="coin-gap-route"]').textContent).toContain('goes through raydium');
  act(() => root.unmount());
});

test('📐 one real pool = an honest "no gap", SOL itself shows nothing, and a route that skips the cheap DEX says so', async () => {
  sharedJson.mockResolvedValue({ mint: 'X', gap: null, pools: 4, realPools: 1, cost: 0.3, answered: true });
  const { el, root } = await mount(<CoinGap mint="Xmint" />);
  expect(el.querySelector('[data-testid="coin-gap-wait"]').textContent).toContain('One real pool');
  act(() => root.unmount());
  const sol = await mount(<CoinGap mint="So11111111111111111111111111111111111111112" />);
  expect(sol.el.querySelector('[data-testid="coin-gap"]')).toBeNull();
  expect(routeHitsCheap(GAP, { routePlan: [{ label: 'Whirlpool' }] })).toBe(false);
  expect(routeHitsCheap(GAP, null)).toBeNull();
});
