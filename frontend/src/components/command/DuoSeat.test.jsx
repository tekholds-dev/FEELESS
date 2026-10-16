import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { DuoSeat, podOf } from './DuoSeat';

test('G4 × OSSY: whose turn, each record, the open seat and the newest calls', () => {
  expect(podOf('G4', { G4: { n: 4, won: 50, med: 2 } })).toEqual({ name: 'G4', n: 4, won: 50, med: 2, fill: 0.5 });
  expect(podOf('OSSY', {}).fill).toBe(0);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'off' }} />));
  expect(el.textContent).toContain('seat off');
  act(() => root.render(<DuoSeat duo={{ mode: 'paper', next: 'OSSY', rec: { G4: { n: 4, won: 50, med: 2 } }, open: { symbol: 'A', by: 'lan', peak: 3 },
    log: [{ at: Date.now() / 1000, model: 'G4', action: 'BUY', symbol: 'A', why: 'buyers 70%' }] }} />));
  expect(el.querySelector('[data-testid="duo-pod-OSSY"]').className).toContain('is-turn');
  expect(el.querySelector('.dso').className).toContain('turn-ossy');
  expect(el.textContent).toContain('4 · 50% won · +2.0%'); expect(el.textContent).toContain('$A · opened by G4'); expect(el.textContent).toContain('BUY $A');
  act(() => root.unmount());
});
