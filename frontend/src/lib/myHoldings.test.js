import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'MeWa11et' } }) }));
// eslint-disable-next-line import/first
import { HeldChip } from './myHoldings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('one shared request for many cards; only coins you hold get the chip with their $ value', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ tokens: [{ mint: 'HELD', holding: 1000 }, { mint: 'SOLD', holding: 0 }] }) }));
  const coin = (mint, price) => ({ baseToken: { address: mint, symbol: mint }, priceUsd: String(price) });
  const host = document.createElement('div'); document.body.appendChild(host);
  const root = createRoot(host);
  await act(async () => { root.render(<>{[coin('HELD', 0.0124), coin('SOLD', 1), coin('OTHER', 1), coin('HELD', 0.0124)].map((c, i) => <HeldChip key={i} pair={c} />)}</>); });
  await act(async () => { await Promise.resolve(); });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(global.fetch.mock.calls[0][0]).toContain('/api/reputation/pnl/MeWa11et');
  const chips = [...host.querySelectorAll('[data-testid="held-chip"]')].map(c => c.textContent);
  expect(chips).toEqual(['YOU HOLD · $12.40', 'YOU HOLD · $12.40']);
  act(() => root.unmount());
});
