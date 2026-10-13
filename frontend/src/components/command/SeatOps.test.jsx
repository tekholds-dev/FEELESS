import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';

test('the kernel board: four hunter lanes, Devil warnings never read as a block, market vs decision freshness apart', async () => {
  const { KernelBoard } = require('./SeatOps');
  const el = document.createElement('div'); document.body.appendChild(el);
  const o = { kernel: { lanes: [{ lane: 1, state: 'HELD', symbol: 'AAA' }, { lane: 2, state: 'ARMED', symbol: 'BBB' }, { lane: 3, state: 'HUNTING', symbol: 'CCC' }, { lane: 4, state: 'HUNTING' }],
    candidates: [{ mint: 'b', symbol: 'BBB', pair: 'Pb', status: 'READY', rank: 180, narrative: 'HOT EARLY MOVE', trigger: 'ENTER', devil: [['rug_signs', 'STRONG_WARNING', 'x'], ['identity', 'WARNING', 'no site']], size: 0.75, courier: true,
      unknown: ['holders'], decidedAgo: 4, ages: { price: 2, research: null } }] } };
  await act(async () => { createRoot(el).render(<KernelBoard o={o} />); });
  expect(el.querySelectorAll('[data-testid^="hunter-"]')).toHaveLength(4);
  expect(el.querySelector('[data-testid="hunter-2"]').textContent).toContain('ARMED · $BBB');
  const dv = el.querySelector('[data-testid="kc-devil-BBB"]').textContent;
  expect(dv).toContain('⚠ DEVIL WARNS'); expect(dv).not.toContain('VETO'); expect(el.textContent).not.toContain('BLOCKED');
  expect(el.querySelector('[data-testid="kc-fresh-BBB"]').textContent).toContain('decision 4s ago'); expect(el.querySelector('[data-testid="kc-fresh-BBB"]').textContent).toContain('market 2s ago');
});
