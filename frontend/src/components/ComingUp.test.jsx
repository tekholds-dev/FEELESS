import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ComingUp } from './ArenaPrime';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('coming up: ready coins first with their place in line, then coins being watched with the reason — never a blank list', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const p = { up: [{ mint: 'A', pairAddress: 'pa', symbol: 'RDY', chg1h: 31, vol1h: 82000, tag: '🧲 dip bought, trend up' },
    { mint: 'B', pairAddress: 'pb', symbol: 'NEW', chg1h: 60, vol1h: 120000, tag: '🆕 no chart yet', wait: 'chart too short to read' },
    { mint: 'C', pairAddress: 'pc', symbol: 'DWN', chg1h: 12, vol1h: 40000, wait: 'trending down' }] };
  const swaps = [];
  await act(async () => { createRoot(el).render(<ComingUp p={p} legs={[{ symbol: 'OLD', pairAddress: 'po' }]} onSwap={(l, r) => swaps.push([l.symbol, r.symbol])} />); });
  const t = el.textContent;
  expect(t).toContain('1 READY'); expect(t).toContain('2 WATCHING');
  expect(el.querySelector('[data-testid="up-RDY"]').textContent).toContain('NEXT');
  expect(el.querySelector('[data-testid="up-NEW"]').textContent).toContain('watching — chart too short to read');
  expect(el.querySelector('[data-testid="up-DWN"]').closest('li').className).toContain('is-wait');
  const sel = el.querySelector('[data-testid="up-swap-NEW"]');                 // the owner can still put a watched coin in by hand
  await act(async () => { sel.value = 'po'; sel.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(swaps).toEqual([['OLD', 'NEW']]);
  const e2 = document.createElement('div'); document.body.appendChild(e2);
  await act(async () => { createRoot(e2).render(<ComingUp p={{ up: [] }} />); });
  expect(e2.textContent).toContain('which filter is holding them');
});
