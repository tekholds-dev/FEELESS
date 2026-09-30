import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TokenAvatar } from './MarketPrimitives';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const M1 = 'Good1111111111111111111111111111111111111111', M2 = 'Bad11111111111111111111111111111111111111111', M3 = 'Goad111111111111111111111111111111111111111';

test('one pooled request puts a green check on verified logos, gold on official, none on revoked', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ verify: { [M1]: { level: 'verified', score: 88 }, [M2]: { level: 'revoked' }, [M3]: { level: 'gold' } } }) }));
  const el = document.createElement('div');
  const pair = m => ({ chainId: 'solana', baseToken: { address: m, symbol: 'X' } });
  await act(async () => { createRoot(el).render(<>{[M1, M2, M3].map(m => <TokenAvatar key={m} pair={pair(m)} size={34} />)}</>); });
  await act(async () => { await new Promise(r => setTimeout(r, 250)); });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  const ticks = el.querySelectorAll('[data-testid="verified-tick"]');
  expect(ticks).toHaveLength(2);
  expect(ticks[0].className).toContain('vt-verified');
  expect(ticks[1].className).toContain('vt-gold');
});
