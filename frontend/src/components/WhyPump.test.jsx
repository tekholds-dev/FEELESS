import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import WhyPump, { mintOf, hostOf } from './WhyPump';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const MINT = 'J49Y17m7PYYYs6WfCZAJjiu6F633dNDMtL3t8UXPgxga';

test('a pasted link or CA becomes the mint; hosts read clean', () => {
  expect(mintOf(`https://pump.fun/coin/${MINT}`)).toBe(MINT);
  expect(mintOf('hello')).toBe(null);
  expect(hostOf('https://www.coindesk.com/a')).toBe('coindesk.com');
});

test('the checker shows the moving list and an answer with sourced drivers', async () => {
  const ans = { mint: MINT, headline: '$PKMN pumped 14.3x in 24 hours', verdict: 'CALLERS', by: 'model', move: ['24 hours', 1327],
    numbers: { symbol: 'PKMN', cap: 400000, vol1h: 150000, buyShare: 70, callers: 4, top10: 22 },
    drivers: [{ why: 'a Nintendo rumor on X', source: 'https://x.com/a/status/1' }, { why: '$150K traded in an hour', source: 'ENGINE' }], sources: [{ title: 'post', url: 'https://x.com/a/status/1' }], risk: 'rumor dies' };
  global.fetch = jest.fn(u => Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('board') ? { moving: [{ mint: MINT, symbol: 'PKMN', chg: 1327 }], recent: [], free: 5 } : ans) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<WhyPump />); });
  expect(el.textContent).toContain('MOVING RIGHT NOW');
  await act(async () => { el.querySelector(`[data-testid="wp-why-${MINT}"]`).click(); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelector('[data-testid="wp-verdict"]').textContent).toContain('CALLERS');
  expect(el.textContent).toContain('$PKMN pumped 14.3x');
  expect(el.querySelector('.wp-src').getAttribute('href')).toBe('https://x.com/a/status/1');
  expect(el.textContent).toContain('our numbers');
});
