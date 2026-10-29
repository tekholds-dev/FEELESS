import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { IntakeBand } from './IntakeBand';
import { intakeDots, laneCounts, splashFacts } from '../../lib/intakeBand';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
// the tank itself is LiveTank (its own tests); here it is a stub that shows what IntakeBand hands it
jest.mock('../LiveTank', () => ({ LiveTank: ({ title, marks, extra, selected }) => <div data-testid="tank" data-title={title} data-selected={selected}>
  {[...(marks || new Map())].map(([m, st]) => <i key={m} data-testid={`mark-${m}`}>{st}</i>)}{extra ? extra({ mint: 'C1', sym: 'CON' }) : null}{extra ? <div data-testid="other">{extra({ mint: 'Z9', sym: 'ZZZ' })}</div> : null}</div> }));

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

test('ONE intake: the ALL LEVELS tank only (no agents-only view), the agents\' coins ringed on it, owner orders in its popup', async () => {
  const call = jest.fn(async () => ({}));
  const o = { kernel: { candidates: C, metrics: { uniqueMintsPerMin: 7 } }, positions: [{ mint: 'H1' }], policy: { band: { min: 12000, max: 300000 } } };
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<IntakeBand o={o} mint="R1" call={call} isOwner onPick={jest.fn()} />); });
  expect(el.querySelectorAll('[data-testid="tank"]')).toHaveLength(1); expect(el.querySelector('[data-testid="tank"]').dataset.title).toBe('ALL LEVELS');
  expect(el.querySelector('[data-testid^="ib-view-"]')).toBeNull();                                             // the AGENTS | ALL LEVELS toggle is gone
  expect(el.querySelector('[data-testid="tank"]').dataset.selected).toBe('R1');
  expect(['H1', 'R1', 'C1'].map(m => el.querySelector(`[data-testid="mark-${m}"]`)?.textContent)).toEqual(['picked', 'ready', 'contending']);
  expect(el.querySelector('[data-testid="mark-T1"]')).toBeNull();                                               // plain intake coins wear no ring
  expect(el.querySelector('[data-testid="ib-funnel"]').textContent).toContain('1PICKED');
  expect(el.querySelector('[data-testid="ib-orders"]').textContent).toContain('CONTENDING');
  expect(el.querySelector('[data-testid="other"]').textContent).toContain("not on the agents' desk yet");      // a tank coin the agents haven't reached
  await act(async () => { el.querySelector('[data-testid="ib-act-arm"]').click(); });
  expect(JSON.parse(call.mock.calls[0][1].body)).toEqual({ owner: { mint: 'C1', action: 'arm' } });
  await act(async () => { root.unmount(); });
});
