import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentAlert, agentAlerts, weakestSeat } from './ArenaPrime';

const go = (sym, extra = {}) => ({ mint: sym, pair: 'P' + sym, symbol: sym, px: 1, go: true, nums: { d5: 3, buy: 64, liq: 60000 }, why: { lean: 2.5, drivers: [['buyers', 1, 'buyers in charge']] }, trigger: ['enter', 'x'], devil: ['agree', 'no evidence against it'], ...extra });
const legs = [{ mint: 'A', pairAddress: 'PA', symbol: 'A', pnlPct: 12 }, { mint: 'B', pairAddress: 'PB', symbol: 'B', pnlPct: -8 }, { mint: 'F', pairAddress: 'PF', symbol: 'F', pnlPct: -30, frozen: true }];

test('alerts: only GO coins not on the card and not seen; the weakest swappable seat is the default; frozen never', () => {
  expect(agentAlerts([go('X'), go('A'), go('Y', { go: false }), go('Z')], legs, { Z: 1 }).map(x => x.symbol)).toEqual(['X']);
  expect(weakestSeat(legs).symbol).toBe('B');
});

test('one click: fill the empty seat, or swap the weakest coin now; dismissed alerts stay gone', async () => {
  localStorage.clear();
  const call = jest.fn(async () => ({ table: [go('GEM')] }));
  const fill = jest.fn(); const swap = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentAlert call={call} legs={legs} emptySeats={1} onFill={fill} onSwap={swap} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('aga-GEM').textContent).toContain('buyers in charge'); expect(q('aga-GEM').textContent).toContain('Devil');
  await act(async () => { q('aga-swap-GEM').click(); });
  expect(swap).toHaveBeenCalledWith(expect.objectContaining({ symbol: 'B' }), expect.objectContaining({ mint: 'GEM', pairAddress: 'PGEM' }), true);
  expect(q('aga-GEM')).toBeNull();                                            // once acted on, it is gone (and stays gone for an hour)
  await act(async () => { root.render(<AgentAlert call={async () => ({ table: [go('GEM'), go('NEW')] })} legs={legs} emptySeats={1} onFill={fill} onSwap={swap} />); });
  await act(async () => { root.unmount(); });
  const el2 = document.createElement('div'); document.body.appendChild(el2); const r2 = createRoot(el2);
  await act(async () => { r2.render(<AgentAlert call={async () => ({ table: [go('GEM'), go('NEW')] })} legs={legs} emptySeats={1} onFill={fill} onSwap={swap} />); });
  expect(q('aga-GEM')).toBeNull(); expect(q('aga-NEW')).not.toBeNull();
  await act(async () => { q('aga-fill-NEW').click(); });
  expect(fill).toHaveBeenCalledWith(expect.objectContaining({ mint: 'NEW' }));
  await act(async () => { r2.unmount(); });
});
