import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { DuoSeat, podOf, sideOf } from './DuoSeat';

const now = () => Date.now() / 1000;

test('each fighter\'s live numbers come from its own calls', () => {
  expect(podOf('G4', { G4: { n: 4, won: 50, med: 2 } })).toEqual({ name: 'G4', n: 4, won: 50, med: 2, fill: 0.5 });
  expect(podOf('OSSY', {}).fill).toBe(0);
  const log = [{ model: 'G4', action: 'BUY', ms: 4000, conf: 80, at: 3 }, { model: 'G4', action: 'NO ANSWER', ms: 9000, at: 2 },
    { model: 'OSSY', action: 'WAIT', ms: 30000, conf: 60, at: 1 }, { model: 'AGENTS', action: 'BUY', at: 0 }];
  const g = sideOf('G4', log);
  expect(g).toMatchObject({ calls: 2, answered: 1, missed: 1, rate: 50, buys: 1, medMs: 4000, conf: 80 });
  expect(g.bars.map(b => b.act)).toEqual(['noanswer', 'buy']);            // oldest → newest
  expect(g.bars[1].h).toBeCloseTo(4000 / 30000);                           // latency against the slowest call on the board
  expect(sideOf('OSSY', []).rate).toBeNull();
});

test('OSSY ⚔ G4: the turn, the seat core, the beam from the last caller, agents backup', () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'off' }} />));
  expect(el.textContent).toContain('seat off');
  act(() => root.render(<DuoSeat duo={{ mode: 'paper', next: 'OSSY', busy: true, rec: { G4: { n: 4, won: 50, med: 2 } }, open: { symbol: 'A', by: 'lan', peak: 3 },
    log: [{ at: now(), model: 'G4', action: 'BUY', symbol: 'A', why: 'buyers 70%', ms: 4000 }, { at: now() - 60, model: 'AGENTS', action: 'WAIT', why: 'no model answered', miss: 'lan BUSY' }] }} />));
  expect(el.querySelector('[data-testid="duo-pod-OSSY"]').className).toContain('is-busy');
  expect(el.textContent).toContain('THINKING'); expect(el.textContent).toContain('STANDBY');
  expect(el.textContent).toContain('4 closed · 50% won · +2.0%'); expect(el.textContent).toContain('$A'); expect(el.textContent).toContain('BUY $A');
  expect(el.querySelector('.dso-beam').className).toContain('from-l');
  expect(el.querySelector('.dso-beam').className).toContain('a-buy');
  expect(el.textContent).toContain('agents backed up 1');
  expect(el.querySelector('.dso-log li.by-agents')).toBeTruthy();
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'G4', fate: { symbol: 'PONK', why: 'keeper pre-check refused: thin pool', at: now() }, log: [] }} />));
  expect(el.querySelector('[data-testid="duo-fate"]').className).toContain('no'); expect(el.textContent).toContain('$PONK: keeper pre-check refused');
  act(() => root.unmount());
});
