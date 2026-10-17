import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { DuoSeat, podOf, tankOf, whaleOf } from './DuoSeat';

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

test('the water tank rises with wins and drains with losses', () => {
  expect(tankOf(null)).toMatchObject({ level: 50, tone: 'flat', n: 0 });
  const t = tankOf({ n: 2, level: 75, net: 6, drops: [{ pct: 9 }, { pct: -3 }] });
  expect(t.tone).toBe('good'); expect(t.drops.map(d => d.good)).toEqual([true, false]); expect(t.drops[0].r).toBeGreaterThan(t.drops[1].r);
  expect(tankOf({ n: 3, level: 20 }).tone).toBe('bad');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'paper', next: 'G4', water: { n: 2, level: 75, net: 6, drops: [{ pct: 9 }, { pct: -3 }] },
    log: [{ at: Date.now() / 1000, model: 'AGENTS', action: 'BUY', symbol: 'B', why: 'agents pick', miss: 'lan BUSY' }] }} />));
  expect(el.querySelectorAll('.dso-drop.up').length).toBe(1); expect(el.querySelectorAll('.dso-drop.dn').length).toBe(1);
  expect(el.querySelector('.dso-log li').className).toContain('by-agents'); expect(el.textContent).toContain('75% won water');
  act(() => root.unmount());
});

test('a whale per model: winning swims high, losing sinks belly-down, the turn glows', () => {
  const win = whaleOf(podOf('G4', { G4: { n: 9, won: 70, med: 4 } }), true), lose = whaleOf(podOf('OSSY', { OSSY: { n: 4, won: 20, med: -6 } }), false);
  expect(win.top).toBeLessThan(lose.top); expect(win.mood).toBe('happy'); expect(lose.mood).toBe('sad'); expect(win.scale).toBeGreaterThan(lose.scale);
  expect(whaleOf(podOf('G4', {}), false)).toMatchObject({ mood: 'new', top: 44 });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'OSSY', rec: { G4: { n: 9, won: 70, med: 4 } }, log: [] }} />));
  expect(el.querySelector('[data-testid="duo-whale-OSSY"]').className).toContain('is-turn');
  expect(el.querySelector('[data-testid="duo-whale-G4"]').className).toContain('m-happy');
  act(() => root.unmount());
});
