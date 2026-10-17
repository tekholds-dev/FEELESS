import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { DuoSeat, podOf, sideOf, thinkOf } from './DuoSeat';

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

test('live thinking: elapsed vs its typical think time, the step it is on, the coins it reads', () => {
  expect(thinkOf(null, 1000, 0)).toBeNull();
  const t = thinkOf({ at: 100 }, 20000, 110);
  expect(t).toMatchObject({ el: 10, typ: 20, frac: 0.5, step: 2, over: false });
  expect(thinkOf({ at: 100 }, 20000, 140).over).toBe(true);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'OSSY', busy: true, live: { by: 'OSSY', at: now() - 3, pick: 'ABC',
    cands: [{ symbol: 'ABC', status: 'READY', move5m: 4, buyers: 60, germ: 6 }, { symbol: 'XYZ', status: 'CONTENDING', move5m: -2 }] }, log: [] }} />));
  expect(el.textContent).toContain('OSSY is thinking'); expect(el.querySelectorAll('.dso-cand').length).toBe(2);
  expect(el.querySelector('.dso-cand.is-pick').textContent).toContain('$ABC'); expect(el.querySelector('.dso-steps li.now')).toBeTruthy();
  act(() => root.unmount());
});

test('🔁 the turn stepper reads the server phase', () => {
  const { turnStep } = require('./DuoSeat');
  expect(turnStep({ phase: 'SEATS FULL' }).i).toBe(-1);
  expect(turnStep({ phase: 'HOLDING', holder: 'OSSY', holding: { symbol: 'A' } })).toMatchObject({ i: 2 });
  expect(turnStep({ phase: 'HUNTING', next: 'G4', fate: { why: 'seated — the keeper buys it next pass', symbol: 'B' } }).i).toBe(1);
  expect(turnStep({ phase: 'HUNTING', next: 'G4' }).word).toMatch(/G4's turn/);
});

test('👍👎 verdict dots read the 5m / 1h / 24h settlements', () => {
  const { verdictDots } = require('./DuoSeat');
  expect(verdictDots([[300, 1, 12.5, true], [3600, null, null, null]])).toEqual([{ w: '5m', ok: 1, move: 12.5, mine: true }, { w: '1h', ok: null, move: null, mine: null }, { w: '24h', ok: null, move: null, mine: null }]);
});

test('💹 seat core words: P&L %, $ in → $ now, peak + held', () => {
  const { seatWords } = require('./DuoSeat');
  const w = seatWords({ pct: 4.48, inUsd: 0.5, nowUsd: 0.522, pnlUsd: 0.022, peak: 6.9, heldMin: 12.2 });
  expect(w).toMatchObject({ pct: '+4.5%', tone: 'up', money: '$0.500 → $0.522 (+$0.022)', meta: 'peak +6.9% · 12m held' });
  expect(seatWords(null)).toBe(null);
});

test('👍👎 stay on screen with no live trade: the newest trade room opens by itself', () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const rows = [{ at: now(), model: 'OSSY', action: 'SELL', why: 'sellers lead', key: 'k1', votes: { up: 1, down: 0, mine: 0, by: {}, res: [] } }];
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'G4', log: [], rooms: [{ mint: 'm1', symbol: 'SWORD', model: 'OSSY', closed: true, pct: 0.7, rows }] }} call={() => Promise.resolve({})} />));
  expect(el.querySelector('[data-testid="dsb-up-k1"]')).toBeTruthy();
  act(() => root.unmount());
});

test('💬 the chime-in box shows with no live trade too', () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'OSSY', log: [], rooms: [{ mint: 'm1', symbol: 'MOMO', model: 'G4', closed: true, pct: -2.2, rows: [] }] }} call={() => Promise.resolve({})} />));
  expect(el.querySelector('[data-testid="duo-say"]')).toBeTruthy();
  act(() => root.unmount());
});
