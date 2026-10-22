import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamiliaOverwatch, owSort } from './FamiliaOverwatch';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const fam = (id, tag, extra) => ({ id, tag, name: `${tag} family`, power: 10, bankMp: 100, chest: 50, seats: 5, record: { wins: 1, losses: 0 }, members: [{ address: `${id}-don-wallet-xyz`, name: 'don', don: true, trades: 2, usd: 12 }],
  week: { trades: 2, usd: 12, pct: 4 }, turf: [], pools: [], paidUsd: 0, payments: 0, badge: { c1: '#d4af37' }, owner: { name: 'don' }, creator: false, ...extra });
const OW = { families: [fam('c2', 'BNK', { power: 90, bankMp: 5000 }), fam('c1', 'SIC', { creator: true, pools: [{ block: 'fee-3', name: 'JLP', apy: 21.4 }], week: { trades: 3, usd: -40, pct: -8 } })],
  totals: { families: 2, members: 2, bankMp: 5100, trades7d: 5, usd7d: -28, paidUsd: 25, turf: 0, pools: 1 }, pricing: { createUsd: 25, packUsd: 5, badgeUsd: 5, baseSeats: 5 }, limits: { familiesPerWallet: 2 }, custody: 'custody pending.' };

test('pure: the creator family stays first whatever the sort', () => {
  expect(owSort(OW.families, 'power').map(f => f.tag)).toEqual(['SIC', 'BNK']);
  expect(owSort([fam('a', 'A', { bankMp: 1 }), fam('b', 'B', { bankMp: 9 })], 'bankMp').map(f => f.tag)).toEqual(['B', 'A']);
});

test('overwatch: every family as a dossier, members on tap, totals + prices', async () => {
  const call = jest.fn(() => Promise.resolve(OW));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<FamiliaOverwatch call={call} />); });
  expect(call).toHaveBeenCalledWith('/admin/familia/overwatch');
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('familia-overwatch').textContent).toContain('OVERWATCH'); expect(q('ow-fam-c1').className).toContain('is-creator');
  expect(q('ow-fam-c1').textContent).toContain('JLP · 21.4%'); expect(q('ow-fam-c1').textContent).toContain('-$40.00');
  await act(async () => { q('ow-open-c2').click(); });
  expect(q('ow-fam-c2').textContent).toContain('c2-d…-xyz');
  expect(el.textContent).toContain('custody pending.'); expect(el.textContent).toContain('$25.00');
  await act(async () => { root.unmount(); });
});
