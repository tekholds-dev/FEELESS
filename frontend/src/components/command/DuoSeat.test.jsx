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

test('🏁 a closed trade never reads "running $?": SOLD keeps it in the seat with the cash it put back; the deck shows the seat\'s vitals', () => {
  const { turnStep, deckOf } = require('./DuoSeat');
  const rooms = [{ mint: 'M', symbol: 'MOON', model: 'OSSY', closed: true, pct: -8.8, usd: -0.033, inUsd: 0.375, back: 0.342 }];
  expect(turnStep({ phase: 'HOLDING', next: 'G4', rooms })).toMatchObject({ i: 3 });                 // stale HOLDING with no coin = it closed
  expect(turnStep({ phase: 'SOLD', next: 'G4', rooms }).word).toMatch(/\$MOON closed -8\.8% · \$0\.342 back in card cash — OSSY reviews it, then G4 picks/);
  const d = deckOf({ next: 'G4', rooms, seats: { used: 2, max: 4 }, hunt: { by: 'G4', since: 100, turnSec: 600 }, live: { cands: [{ symbol: 'ABC', buyers: 61 }] },
    totals: { G4: { n: 4, won: 1, usd: -1.2 }, OSSY: { n: 6, won: 3, usd: 0.4 } }, log: [{ model: 'AGENTS' }, { model: 'G4' }] }, 280);
  const k = Object.fromEntries(d.map(t => [t.k, t]));
  expect(k.last).toMatchObject({ val: '$MOON -8.8%', tone: 'dn' }); expect(k.last.sub).toBe('$0.375 in → $0.342 back · card cash ✔');
  expect(k.seats).toMatchObject({ val: '2/4', fill: 0.5 }); expect(k.clock).toMatchObject({ val: '3:00', fill: 0.3 });
  expect(k.table.sub).toBe('top $ABC · buy 61%'); expect(k.rec).toMatchObject({ val: '−$0.800', tone: 'dn', fill: 0.4 });
  expect(k.agents).toMatchObject({ val: '1', fill: 0.5 });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'G4', phase: 'SOLD', rooms, seats: { used: 0, max: 4 }, log: [] }} />));
  expect(el.querySelector('.dso-hex').className).toContain('is-sold'); expect(el.querySelector('.dso-hex').textContent).toContain('$MOON');
  expect(el.querySelectorAll('[data-testid="duo-deck"] .dso-tile').length).toBe(6);
  expect(el.querySelector('[data-testid="duo-turn"]').dataset.step).toBe('3');
  act(() => root.unmount());
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

test('💬 between trades the talk shows in the room', () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'OSSY', log: [], rooms: [], between: [{ at: now(), model: 'G4', action: 'TALK', view: 'HOLD', talk: true, why: 'on $X: HOLD — buyers 70%', key: 'b1' }] }} call={() => Promise.resolve({})} />));
  expect(el.textContent).toMatch(/between trades/);
  expect(el.textContent).toMatch(/buyers 70%/);
  expect(el.querySelector('[data-testid="duo-say"]')).toBeTruthy();
  act(() => root.unmount());
});

test('💬 a coin on the card has its own room, and its chime-in names that coin', () => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const sent = [];
  const call = (_p, o) => { sent.push(JSON.parse(o.body)); return Promise.resolve({}); };
  act(() => root.render(<DuoSeat duo={{ mode: 'real', next: 'OSSY', log: [], rooms: [], holding: { symbol: 'Kimchi' }, trade: [],
    coinRooms: [{ mint: 'eM', symbol: 'ELON', who: 'you', rows: [{ at: now(), model: 'G4', action: 'TALK', view: 'HOLD', talk: true, why: 'ELON buyers strong', key: 'e1' }] }] }} call={call} />));
  act(() => { el.querySelector('[data-testid="duo-coin-ELON"]').click(); });
  expect(el.textContent).toMatch(/ELON buyers strong/);
  const inp = el.querySelector('[data-testid="duo-say"]');
  const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
  act(() => { set.call(inp, 'hold elon'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  act(() => { el.querySelector('.dso-say').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
  expect(sent[0]).toEqual({ comment: 'hold elon', mint: 'eM' });
  act(() => root.unmount());
});

test('🔁 strict turns by default: the switch posts the guards; a weak record only warns', async () => {
  const posts = [];
  const call = jest.fn(async (path, o) => { posts.push([path, JSON.parse(o.body)]); return { ok: true, guards: true }; });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const duo = { mode: 'real', next: 'G4', guards: false, bench: { G4: { benched: true, n: 150, median: -0.8, upPct: 40 }, OSSY: { benched: false } }, log: [] };
  await act(async () => { root.render(<DuoSeat duo={duo} call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('duo-guards').textContent).toBe('🔁 STRICT TURNS'); expect(q('duo-bench-warn').textContent).toContain("G4's last 150 FAVOR calls settled -0.8% median, 40% up — it still takes its turn");
  await act(async () => { q('duo-guards').click(); }); expect(posts[0]).toEqual(['/admin/ai/seat', { guards: true }]);
  await act(async () => { root.render(<DuoSeat duo={{ ...duo, guards: true }} call={call} />); });
  expect(q('duo-guards').textContent).toBe('🪑 GUARDS ON'); expect(q('duo-bench-warn')).toBeNull();
  act(() => root.unmount());
});
