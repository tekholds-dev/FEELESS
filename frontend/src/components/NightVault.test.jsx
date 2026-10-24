import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { NightVault, sleepEarn, usd0 } from './NightVault';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const RISK = { contract: 1, depeg: 1, il: 0, liq: 0, note: 'n' };
const SLEEP = { kamino: true, rows: [{ id: 'p1', kind: 'stake', sym: 'JUPSOL', apy: 7.2, tvl: 9e8, hold: 'jup', proto: 'Jupiter' }, { id: 'p3', kind: 'lend', sym: 'USDC', apy: 6.1, tvl: 5e8, stable: true, proto: 'Jupiter Lend', project: 'jupiter-lend', mints: ['usdc'] }],
  strategies: [{ key: 'lst', name: '🥩 STAKE STACK', sub: 's', risk: RISK, rows: ['p1'], apy: 7.2, top: 'JUPSOL' }, { key: 'stable', name: '💵 STABLE SLEEP', sub: 's', risk: RISK, rows: ['p3'], apy: 6.1, top: 'USDC' },
    { key: 'loop', name: '🔁 LOOP IT', sub: 's', risk: { ...RISK, liq: 3 }, rows: [], apy: 9.1, top: 'JUPSOL ×2', loops: [{ id: 'p1', sym: 'JUPSOL', lstApy: 7.2, borrow: 5.3, maxLtv: 0.65, app: 'https://app.kamino.finance/multiply',
      plays: [{ x: 1.5, apy: 8.15, ltv: 0.333, cushion: 0.487 }, { x: 2, apy: 9.1, ltv: 0.5, cushion: 0.231 }] }] }] };

test('pure: simple interest for a nap', () => {
  expect(sleepEarn(1000, 7.3, 365)).toBeCloseTo(73); expect(sleepEarn(1000, 7.3, 30)).toBeCloseTo(6); expect(usd0(100000)).toBe('$100.0K');
});

test('the Night Vault: strategies with risk meters, the calculator moves every number, the loop shows LTV + cushion', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(SLEEP), text: () => Promise.resolve(JSON.stringify(SLEEP)) }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<NightVault />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('night-vault').textContent).toContain('THE NIGHT VAULT'); expect(q('nv-lst').textContent).toContain('7.20%');
  expect(q('nv-lst').querySelectorAll('.nv-risk p').length).toBe(4);
  expect(q('nv-picks-lst')).not.toBeNull(); expect(q('nv-go-lst').textContent).toContain('PUT IT TO WORK'); expect(q('nv-earn-lst')).not.toBeNull();   // top picks + ONE pop-out + the live ticker (no row wall)
  await act(async () => { q('nv-loop').querySelector('.nv-head').click(); });
  const loopCard = q('nv-loopcard');
  expect(loopCard.textContent).toContain('9.10%'); expect(q('nv-cushion').textContent).toContain('23%');
  await act(async () => { q('nv-x-1.5').click(); });
  expect(q('nv-cushion').textContent).toContain('49%');
  await act(async () => { root.unmount(); });
});
