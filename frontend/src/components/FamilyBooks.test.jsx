import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamilyBooks, bookSum, TOOLS } from './FamilyHQ';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const BOOK = [{ who: 'vito', address: 'V', symbol: 'WIF', ret: 0.5, usd: 50, holdMin: 31, at: 2, tx: 't1' }, { who: 'kid', address: 'K', symbol: 'BONK', ret: -0.2, usd: -4, holdMin: 6, at: 1, tx: 't2' },
  { who: 'vito', address: 'V', symbol: 'POPCAT', ret: 0.1, usd: 10, holdMin: 45, at: 0 }];

test('pure: the books sum the family and rank members', () => {
  const s = bookSum(BOOK);
  expect(s.usd).toBe(56); expect(s.n).toBe(3); expect(s.wonPct).toBe(67); expect(s.best.symbol).toBe('WIF');
  expect(s.members.map(m => [m.who, m.usd, m.n])).toEqual([['vito', 60, 2], ['kid', -4, 1]]);
  expect(bookSum([]).wonPct).toBeNull();
});

test('the family HQ rail carries the one-stop tools and the Books tape', async () => {
  expect(TOOLS.map(t => t[0])).toEqual(expect.arrayContaining(['books', 'pools', 'vault', 'trade', 'fee', 'fuse']));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<FamilyBooks book={BOOK} />); });
  expect(el.textContent).toContain('$WIF'); expect(el.textContent).toContain('-20%'); expect(el.querySelector('a[href="https://solscan.io/tx/t1"]')).not.toBeNull();
  await act(async () => { root.render(<FamilyBooks book={[]} />); });
  expect(el.textContent).toContain('No verified trades');
  await act(async () => { root.unmount(); });
});
