import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FamilyOps, opsSums } from './FamilyOps';
import LIVE from '../dev/liveBlocks.json';

// The five readers' real reads (mainnet, 2026-11-13): marginfi $32.2K net / $9.1K owed, Save $2.5K, Phoenix 2 seats, PumpSwap LP $44.3K, Meteora $46.3K.
test('Familia ops sums the real reads: net, owed, errands; a building with no $ read shows its position count, never a number', async () => {
  const bl = { buildings: LIVE.buildings };
  const s = opsSums(bl);
  expect(s.rows).toHaveLength(5); expect(Math.round(s.debt)).toBe(9108); expect(Math.round(s.net)).toBe(Math.round(32170.38 + 2499.75 + 44306.6 + 46346.77));
  expect(s.errands).toBe(2);
  const el = document.createElement('div'); document.body.appendChild(el);
  const pick = jest.fn();
  await act(async () => { createRoot(el).render(<FamilyOps bl={bl} onPick={pick} />); });
  const t = el.querySelector('[data-testid="family-ops"]').textContent;
  expect(t).toContain('$125.3K'); expect(t).toContain('$9.1K'); expect(t).toContain('owes $9.1K'); expect(t).toContain('2 pos');
  await act(async () => { el.querySelector('[data-testid="fop-meteora"]').click(); });
  expect(pick).toHaveBeenCalledWith({ blk: 'meteora' });
});

test('the worst loan reads its liquidation line; an empty block says how to build, with no number', async () => {
  expect(opsSums({ buildings: [{ key: 'save', name: 'Save', state: 'built', usd: 10, debt: 90, risk: 0.86 }] }).worst.risk).toBe(0.86);
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FamilyOps bl={{ buildings: [{ key: 'save', state: 'empty' }] }} />); });
  expect(el.textContent).toContain('No building stands on a real position yet');
});
