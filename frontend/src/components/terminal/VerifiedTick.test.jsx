import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TokenAvatar } from './MarketPrimitives';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const M1 = 'Good1111111111111111111111111111111111111111', M2 = 'Bad11111111111111111111111111111111111111111', M3 = 'Goad111111111111111111111111111111111111111';

test('one pooled request puts a green check on verified logos, gold on official, none on revoked', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ edge: { [M1]: { verify: { level: 'verified', score: 88 } }, [M2]: { verify: { level: 'revoked' } }, [M3]: { verify: { level: 'gold' } } } }) }));
  const el = document.createElement('div');
  const pair = m => ({ chainId: 'solana', baseToken: { address: m, symbol: 'X' } });
  await act(async () => { createRoot(el).render(<>{[M1, M2, M3].map(m => <TokenAvatar key={m} pair={pair(m)} size={34} />)}</>); });
  await act(async () => { await new Promise(r => setTimeout(r, 250)); });
  expect(global.fetch.mock.calls).toHaveLength(1);   // ONE coin-edge request carries verification + pulse for every logo
  expect(String(global.fetch.mock.calls[0][0])).toContain('/api/reputation/edge?mints=');
  const ticks = el.querySelectorAll('[data-testid="verified-tick"]');
  expect(ticks).toHaveLength(2);
  expect(ticks[0].className).toContain('vt-verified');
  expect(ticks[1].className).toContain('vt-gold');
});
