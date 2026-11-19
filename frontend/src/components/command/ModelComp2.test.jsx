import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { Gate } from './ModelComp2';

// 🚦 Slice 7: the gate says shipped / not shipped with the reason, the meter shows COMP vs the base vs always-guess, and the counts say what COMP
// learned from (real, judged proofs only) and what it dropped.
const ds = { only: 'real judged proofs', train: 41, valid: 7, test: 22, droppedN: 2458, dropped: { market_row: 1869, source_marker: 274, test: 25 },
  byKind: [{ kind: 'PoB', train: 14, valid: 2, test: 6 }, { kind: 'PoW', train: 6, valid: 2, test: 2 }], settledBy: { 'owner mark': 37, scoreboard: 19 } };

function mount(d) {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => { root.render(<Gate d={d} />); });
  return { el, done: () => { act(() => root.unmount()); el.remove(); } };
}

test('a COMP that does not beat the base says NOT SHIPPED and why', () => {
  const why = 'Not shipped: COMP got 11 of 22 right and the base 9B got 12 of 22.';
  const { el, done } = mount({ dataset: ds, exam: { ship: { ship: false, why, comp: 11, base: 12, baseline: 12, n: 22 } } });
  expect(el.querySelector('[data-testid="mc2-ship"]').textContent).toBe('NOT SHIPPED');
  expect(el.querySelector('[data-testid="mc2-ship-why"]').textContent).toBe(why);
  expect(el.querySelectorAll('.c2-gate-meter li')).toHaveLength(3);
  expect(el.querySelector('.c2-gate-meter li.is-comp').textContent).toContain('11/22');
  expect(el.textContent).toContain('real, judged proofs only'); expect(el.textContent).toContain('PoB 22 · PoW 10');
  expect(el.textContent).toContain('1869 market snapshots');
  done();
});

test('a shipped COMP says so; an old dataset asks for a retrain', () => {
  let m = mount({ dataset: ds, exam: { ship: { ship: true, why: 'Shipped: COMP got 15 of 22', comp: 15, base: 12, baseline: 12, n: 22 } } });
  expect(m.el.querySelector('[data-testid="mc2-gate"]').className).toContain('is-ship'); expect(m.el.querySelector('[data-testid="mc2-ship"]').textContent).toBe('SHIPPED'); m.done();
  m = mount({ dataset: { train: 99 }, exam: null });
  expect(m.el.textContent).toContain('NOT EXAMINED'); expect(m.el.textContent).toContain('train again'); m.done();
});
