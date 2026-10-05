import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SwapPicker, PICK_LENSES } from './ArenaPrime';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const tick = () => act(() => new Promise(r => setTimeout(r, 20)));

test('the real-card swap picker has every Lab lens + search, flags thin pools and lookalikes, and picks with its pool', async () => {
  const urls = [];
  global.fetch = jest.fn(async u => { urls.push(String(u));
    if (String(u).includes('search')) return { ok: true, json: async () => ({ pools: [{ baseAddress: 'BTC', pairAddress: 'pb', symbol: 'cbBTC', priceUsd: 60000, liquidityUsd: 9e6, real: true }, { baseAddress: 'FAKE', pairAddress: 'pf', symbol: 'BTC', priceUsd: 1, liquidityUsd: 9e6, impostor: true }] }) };
    if (String(u).includes('/fuses/trench')) return { ok: true, json: async () => ({ floor: 8000, checked: [{}, {}], rules: 'strict', rows: [{ mint: 'TR', pairAddress: 'ptr', symbol: 'TRN', price: 0.001, liq: 9000, holders: 512, score: 74, trench: true }, { mint: 'TT', pairAddress: 'ptt', symbol: 'TTHIN', price: 0.001, liq: 4000, trench: true }] }) };
    if (String(u).includes('contenders')) return { ok: true, json: async () => ({ divisions: [{ key: 'dip', rows: [{ mint: 'D', pairAddress: 'pd', symbol: 'DIP', price: 1, liq: 80000, score: 70 }] }] }) };
    return { ok: true, json: async () => ({ pools: [{ baseAddress: 'P', pairAddress: 'pp', symbol: 'POP', priceUsd: 2, liquidityUsd: 400000, change24h: 5 }, { baseAddress: 'T', pairAddress: 'pt', symbol: 'THIN', priceUsd: 2, liquidityUsd: 5000 }] }) }; });
  const picks = [];
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<SwapPicker out={{ symbol: 'WIF' }} have={[]} minLiq={20000} onPick={r => picks.push(r)} onClose={() => {}} />); });
  await tick();
  expect(PICK_LENSES.map(x => x[0])).toEqual(['popular', 'majors', 'risers', 'yield', 'deep', 'runners', 'volume', 'trench', 'new', 'dip', 'paid']);
  expect(urls[0]).toContain('/fuses/discover?lens=popular');
  expect(el.querySelector('[data-testid="sp-pick-THIN"]').disabled).toBe(true);
  await act(async () => { el.querySelector('[data-testid="sp-pick-POP"]').click(); });
  expect(picks[0]).toMatchObject({ mint: 'P', pairAddress: 'pp' });
  await act(async () => { el.querySelector('[data-testid="sp-lens-dip"]').click(); }); await tick();
  expect(el.textContent).toContain('$DIP');
  // 🗑 trench lens: its own pool floor ($9K passes the $8K trench floor even though the card's floor is $20K), holders shown
  await act(async () => { el.querySelector('[data-testid="sp-lens-trench"]').click(); }); await tick();
  expect(el.querySelector('[data-testid="sp-trench-note"]').textContent).toContain('2 checked');
  expect(el.textContent).toContain('512 holders');
  expect(el.querySelector('[data-testid="sp-pick-TRN"]').disabled).toBe(false);
  expect(el.querySelector('[data-testid="sp-pick-TTHIN"]').disabled).toBe(true);
  await act(async () => { const i = el.querySelector('[data-testid="sp-search"]'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, 'btc'); i.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(() => new Promise(r => setTimeout(r, 400)));
  expect(urls.some(u => u.includes('/fuses/search?q=btc'))).toBe(true);
  expect(el.querySelector('[data-testid="sp-pick-BTC"]').disabled).toBe(true);   // lookalike can't be picked
  expect(el.querySelector('[data-testid="sp-pick-cbBTC"]').disabled).toBe(false);
});
