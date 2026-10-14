import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeStamp, moveWord } from './FeeStamp';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('the $FEE stamp: live 24h move on the arc, tone follows it, links to $FEE', async () => {
  expect(moveWord(12.34)).toBe('▲ +12.3% · 24H'); expect(moveWord(-4)).toBe('▼ -4.0% · 24H'); expect(moveWord(null)).toBe('LIVE · $FEE');
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FeeStamp change24h={-4} />); });
  const a = el.querySelector('[data-testid="fee-stamp"]');
  expect(a.className).toContain('is-dn'); expect(a.getAttribute('href')).toBe('/terminal/fee');
  expect(el.querySelector('[data-testid="fee-stamp-move"]').textContent).toBe('▼ -4.0% · 24H');
  expect(el.querySelector('textPath').textContent).toContain('ZERO FEE TO BUY');
});
