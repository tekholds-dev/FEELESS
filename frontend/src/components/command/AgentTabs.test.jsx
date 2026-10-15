import { deckMeters } from './AgentCockpit';

test('deck tab meters come from the payload: trades won share, agents active share, feed freshness; missing = no meter', () => {
  const o = { tradeTape: { rows: [{ result: 4 }, { result: -2 }, { result: 1 }, {}] }, generations: [{ status: 'ACTIVE' }, { status: 'ACTIVE' }, { status: 'PROBATION' }, { status: 'ACTIVE' }],
    tape: [{ at: 1000 }] };
  const out = deckMeters(o, [['live', '⚡ Feed', 1, null], ['tape', '🎬 Trades', 4, null], ['agents', '🧩 Desk', 4, null], ['brain', '🧠 Brain', null, null]], 1030);
  const by = Object.fromEntries(out.map(t => [t[0], t]));
  expect(by.tape[4]).toBeCloseTo(2 / 3); expect(by.tape[5]).toBe('2 of 3 closed real trades won');
  expect(by.agents[4]).toBe(0.75); expect(by.live[4]).toBe(1); expect(by.brain[4]).toBeNull(); expect(by.brain[5]).toBeNull();
  expect(deckMeters({ tape: [{ at: 1 }] }, [['live', '⚡ Feed', 1, null]], 1 + 600)[0][4]).toBe(0);   // ten quiet minutes = an empty meter
});


test('the trades meter reads the tape result object ({pct}) — it once read every trade as lost', () => {
  const out = deckMeters({ tradeTape: { rows: [{ result: { pct: 2.9 } }, { result: { pct: -10.6 } }, { open: true }] } }, [['tape', '🎬 Trades', 2, null]], 0);
  expect(out[0][4]).toBe(0.5); expect(out[0][5]).toBe('1 of 2 closed real trades won');
});

import { moneyOf, exitTags } from '../../lib/cockpit';

test("💵 the money strip: card value, today's closed real trades (not yesterday's), the held seats, the night state", () => {
  const now = new Date(2026, 9, 15, 14, 0, 0).getTime(); const mid = new Date(2026, 9, 15, 0, 0, 0).getTime() / 1000;
  const d = { office: { mission: { value: 2, putIn: 40 }, nightGuard: { night: true, paused: false, lines: { draw: 8, streak: 3 } },
    tradeTape: { rows: [{ at: mid + 100, open: false, sells: [{ at: mid + 200 }], result: { pct: 10, usd: 0.05 } }, { at: mid + 300, open: false, sells: [{ at: mid + 400 }], result: { pct: -5, usd: -0.02 } },
      { at: mid - 900, open: false, sells: [{ at: mid - 100 }], result: { pct: 50, usd: 9 } }, { at: mid + 500, open: true, sells: [] }] } } };
  const m = moneyOf(d, [{ seat: 1, open: false, symbol: 'A', mint: 'a', pct: 3, pnlUsd: 0.01, why: '🛫 runway: a green coin…' }, { seat: 2, open: true }], now);
  expect(m.value).toBe(2); expect(m.netPct).toBeCloseTo(-95);
  expect(m.today).toMatchObject({ n: 2, won: 1 }); expect(m.today.usd).toBeCloseTo(0.03);
  expect(m.open).toHaveLength(1); expect(m.open[0].tags.map(t => t.k)).toEqual(['runway']); expect(m.seats).toBe(2);
  expect(m.night.state).toBe('night');
  expect(moneyOf({ office: { nightGuard: { night: true, paused: true, why: '3 losses', leftMin: 40 } } }, [], now).night.word).toContain('GUARD PAUSED');
  expect(moneyOf({ office: {} }, [], now).today.usd).toBeNull();   // no closed trade today = no number, never a fake $0
});

test('🛫 💰 🔁 exit chips come from Reaper\'s own words only', () => {
  expect(exitTags({ rule: 'R6h half banked' }).map(t => t.k)).toEqual(['half']);
  expect(exitTags({ action: 'trim' }).map(t => t.k)).toEqual(['half']);
  expect(exitTags({ tag: '🤖 agents · 🔁 comeback' }).map(t => t.k)).toEqual(['comeback']);
  expect(exitTags({ rule: 'R10 hold', why: 'thesis still good' })).toEqual([]);
});
