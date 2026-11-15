import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MoneyCockpit, verdictOf } from './MoneyCockpit';
import { bestByLane } from './OwnerFolders';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mount = async node => { const el = document.body.appendChild(document.createElement('div')); await act(async () => { createRoot(el).render(node); }); return el; };
const ROWS = [{ id: 'u', name: 'USDC on kamino', kind: 'lend', risk: 'none', tvl: 5e7, per1k24: 0.22, yearPct: 8, venue: 'kamino' },
  { id: 'j', name: 'JitoSOL', kind: 'stake', tvl: 9e8, per1k24: 0.19, yearPct: 7.1, venue: 'jito' },
  { id: 'p', name: 'SOL-USDC', kind: 'pool', tvl: 3e7, per1k24: 1.1, yearPct: 40, venue: 'orca' },
  { id: 'm', name: 'MEME-SOL', kind: 'pool', tvl: 2e5, per1k24: 94, yearPct: 3000, venue: 'meteora' }];

// Owner 2026-11-15: "money folder in agents need a complete redo". One verdict, one ring, three facts, risk lanes as meters, one pick.
test('the verdict reads the real ledger and the plan', () => {
  expect(verdictOf({ best: ROWS[0] })).toContain('Nothing placed yet. The safest lane leads with USDC on kamino');
  expect(verdictOf({ staked: 120, placedPct: 30, reservePct: 10 })).toBe('$120 in. 30% of the plan is placed, 10% is held back, 60% is free to place.');
  expect(verdictOf({ staked: 5, placedPct: 95, reservePct: 10 })).toContain('Over-planned');
});

test('the steady lane leads; picking a lane swaps the pick; a pool never gets Add to plan', async () => {
  const added = [];
  const el = await mount(<MoneyCockpit st={{ stakedUsd: 0 }} lanes={bestByLane(ROWS)} rows={ROWS} onPlan={r => added.push(r.id)} inPlan={() => false} payOf={() => ({ month: 6.6, agents: 1, piece: 0.5 })} />);
  expect(el.querySelector('[data-testid="mck-pick"]').textContent).toContain('USDC on kamino');
  await act(async () => { el.querySelector('[data-testid="money-plan-steady"]').click(); });
  expect(added).toEqual(['u']);
  await act(async () => { el.querySelector('[data-testid="money-lane-hot"]').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 300)); });
  expect(el.querySelector('[data-testid="mck-pick"]').textContent).toContain('MEME-SOL');
  expect(el.querySelector('[data-testid="money-plan-hot"]')).toBeNull();   // a pool opens on its venue, by hand
});
