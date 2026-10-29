import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { PriceGaps, gapWord } from './PriceGaps';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../lib/sharedJson', () => ({ sharedJson: jest.fn(), _resetShared: () => {} }));
const { sharedJson } = require('../lib/sharedJson');

const P = (dex, at, px) => ({ dex, pair: `P${dex}`, px, liq: 200000, vs: 'USDC', at });
const OPEN = { mint: 'A', sym: 'JTO', n: 3, lo: P('raydium', 0, 2.0), hi: P('orca', 1.2, 2.024), gapPct: 1.2, netPct: 0.6, open: true, openSec: 120, pools: [P('raydium', 0, 2.0), P('meteora', 0.4, 2.008), P('orca', 1.2, 2.024)] };
const SHUT = { mint: 'B', sym: 'BONK', n: 2, lo: P('raydium', 0, 1e-5), hi: P('orca', 0.2, 1.0002e-5), gapPct: 0.2, netPct: -0.4, open: false, openSec: 0, pools: [P('raydium', 0, 1e-5), P('orca', 0.2, 1.0002e-5)] };

test('📐 every token is a rail: cheap + rich lamps, the gap and its net after costs; an OPEN gap lights up with its clock', async () => {
  sharedJson.mockResolvedValue({ gaps: [OPEN, SHUT], tokens: 18, open: 1, cost: 0.3 });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<PriceGaps />); });
  const rows = el.querySelectorAll('[data-testid="gp-row"]');
  expect(rows).toHaveLength(2); expect(rows[0].className).toContain('is-open'); expect(rows[1].className).not.toContain('is-open');
  expect(rows[0].textContent).toContain('$JTO'); expect(rows[0].textContent).toContain('raydium → orca'); expect(rows[0].textContent).toContain('⏱ 2m 0s');
  expect(rows[0].querySelector('em.is-lo')).not.toBeNull(); expect(rows[0].querySelector('em.is-hi').style.left).toBe('100%');
  expect(rows[1].textContent).toContain('in costs');
  expect(el.querySelector('[data-testid="price-gaps"]').textContent).toContain('18');
  expect(gapWord(OPEN)).toContain('buy side raydium'); expect(gapWord({ ...SHUT, netPct: 0.1 })).toContain('confirming');
  await act(async () => { root.unmount(); });
});

test('📐 a failed read says so — never a blank panel', async () => {
  sharedJson.mockRejectedValue(new Error('down'));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<PriceGaps />); });
  expect(el.textContent).toContain('did not answer');
  await act(async () => { root.unmount(); });
});
