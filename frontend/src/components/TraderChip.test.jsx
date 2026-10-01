import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { TraderChip } from './TraderChip';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const A = 'Aaaa1111111111111111111111111111111111111111'; const B = 'Bbbb1111111111111111111111111111111111111111';

test('trader chips: ONE batched request for every chip, score + medals + battles, tap opens the trader page', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ ids: { [A]: { score: 64, medals: { 1: 1, 2: 0, 3: 1 }, battles: { w: 3, l: 1 }, catWins: 1 }, [B]: { score: 0, medals: {}, battles: {} } } }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<><TraderChip address={A} /><TraderChip address={B} compact /><TraderChip address={A} compact /></>); });
  await act(() => new Promise(r => setTimeout(r, 350)));
  expect(global.fetch).toHaveBeenCalledTimes(1); expect(global.fetch.mock.calls[0][0]).toContain(`addrs=${A},${B}`);
  const a = el.querySelector(`[data-testid="tchip-${A}"]`);
  expect(a.textContent).toContain('64'); expect(a.textContent).toContain('🥇2'); expect(a.textContent).toContain('⚔ 3-1');
  expect(a.getAttribute('data-tip')).toContain('beat FeeCat ×1');
  const pop = jest.fn(); window.addEventListener('popstate', pop);
  await act(async () => { a.click(); });
  expect(window.location.pathname).toBe(`/terminal/profile/${A}`); expect(pop).toHaveBeenCalled();
});
