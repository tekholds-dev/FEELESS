import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { IntakeBand } from './IntakeBand';
import { intakeDots, laneCounts, splashFacts } from '../../lib/intakeBand';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const C = [{ mint: 'R1', symbol: 'RDY', status: 'READY', rank: 150, price: 0.0001, supply: 1e9, ageMin: 30, move5m: 4, buyShare: 64, liq: 15000, trigger: 'ENTER' },
  { mint: 'C1', symbol: 'CON', status: 'CONTENDING', rank: 90, price: 0.00003, supply: 1e9, ageMin: 8, move5m: -9, buyShare: 41, liq: 6000 },
  { mint: 'T1', symbol: 'TRK', status: 'TRACKING', rank: 20, price: 0.00002, supply: 1e9 },
  { mint: 'H1', symbol: 'HLD', status: 'HELD', rank: 0, price: 0.0002, supply: 1e9 },
  { mint: 'X1', symbol: 'NOCAP', status: 'READY', rank: 200 }];

test('🛰 every coin the kernel reads is a dot: across = its MC, up = how far the agents took it; picked + ready first', () => {
  const d = intakeDots(C, ['H1'], { min: 12000, max: 300000 });
  expect(d.map(x => [x.mint, x.stage])).toEqual([['H1', 'picked'], ['R1', 'ready'], ['C1', 'contending'], ['T1', 'in']]);   // no cap = not drawn
  expect(d.find(x => x.mint === 'T1').inside).toBe(true); expect(d[0].x).toBeGreaterThan(d.find(x => x.mint === 'T1').x);
  expect(laneCounts(d)).toMatchObject({ picked: 1, ready: 1, contending: 1, in: 1, total: 4 });
  const f = Object.fromEntries(splashFacts(C[1]).map(([k, v, cls]) => [k, [v, cls]]));
  expect(f['5M']).toEqual(['-9.0%', 'is-bad']); expect(f.BUYERS[1]).toBe('is-bad'); expect(f.AGE[1]).toBe('is-warn'); expect(f.POOL[1]).toBe('is-bad');
});

test('tap a dot → its vitals splash; ⚡ ARM sends the owner review order; Esc closes', async () => {
  const call = jest.fn(async () => ({}));
  const o = { kernel: { candidates: C, metrics: { uniqueMintsPerMin: 7 } }, positions: [{ mint: 'H1' }], policy: { band: { min: 12000, max: 300000 } } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<IntakeBand o={o} mint="R1" call={call} isOwner onPick={jest.fn()} />); });
  expect(el.querySelectorAll('.ib-dot')).toHaveLength(4);
  expect(el.querySelector('[data-testid="ib-funnel"]').textContent).toContain('1PICKED');
  await act(async () => { el.querySelector('[data-testid="ib-dot-C1"]').click(); });
  const sp = el.querySelector('[data-testid="ib-splash"]');
  expect(sp.textContent).toContain('$CON'); expect(sp.textContent).toContain('CONTENDING'); expect(sp.textContent).toContain('BUYERS');
  await act(async () => { el.querySelector('[data-testid="ib-act-arm"]').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ owner: { mint: 'C1', action: 'arm' } });
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(el.querySelector('[data-testid="ib-splash"]')).toBeNull();
  await act(async () => { root.unmount(); });
});
