import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { CompWatch } from './CompWatch';

const W = { at: 1700000000, lean: { won: 1, lost: 1, flat: 0 }, totals: { won: 3, lost: 1, flat: 9, rows: 4, collects: 7 },
  board: [{ pair: 'p1', symbol: 'MOON', dex: 'pumpswap', move: 31.2, call: 'won', left: 90, ageMin: 4 }, { pair: 'p2', symbol: 'RUG', dex: 'raydium', move: null, gone: true, call: 'lost', left: 30 }, { pair: 'p3', symbol: 'WAIT', dex: 'x', move: null, call: null, left: 10 }],
  minds: { unit: 'min', calls: 2, fail: 1, usd: 0.01, perMin: [{ m: 0, ok: 1, fail: 1, ms: 900 }], tape: [{ at: 1699999990, model: 'qwen', kind: 'pow', ms: 900, ok: true }] },
  settled: [{ title: 'Hold $A for 1 hour', outcome: 'won', at: 1 }] };

test('👁 COMP watch shows every held coin with its real move, a gone pool as lost, an unpriced one as —, the minds tape and the learner record', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const call = jest.fn(async () => W);
  await act(async () => { root.render(<CompWatch call={call} />); });
  expect(call).toHaveBeenCalledWith('/admin/model-lab/watch');
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('cw-coin-p1').textContent).toMatch(/\+31\.2%/); expect(q('cw-coin-p1').textContent).toMatch(/WON/);
  expect(q('cw-coin-p2').textContent).toMatch(/pool gone/); expect(q('cw-coin-p2').textContent).toMatch(/LOST/);
  expect(q('cw-coin-p3').textContent).toMatch(/—/);
  expect(q('cw-tape').textContent).toMatch(/qwen/);
  expect(el.textContent).toMatch(/75%/);   // 3 won of 4 decided
  await act(async () => { root.unmount(); });
});
