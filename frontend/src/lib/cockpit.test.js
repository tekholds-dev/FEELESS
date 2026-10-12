import { seatCards, focusMint, chartModel, chartMarkers, decisionOf, tapeOf, tapeTone, lastByMint, mcFrom, supplyFrom, reviewQueue, bucketCounts, inBucket, supplyWord,
  seatState, pnlUsdOf, missionTiles, letterMarkers, freshWord, inputsOf, traceOf, newEvents, maxIdByAgent, queueStatus, queueMc } from './cockpit';
import { easedAt, EASE_MS } from './easedNumber';
import { applyDelta, TAPE_KEEP } from './agentHub';

import { D, PUMP } from '../components/command/__fixtures__/cockpit';

test('seats: the real card as cards — live %, entry / now in market cap, Reaper\'s ruling, the newest REAL tape line; an open seat says what could fill it', () => {
  const s = seatCards(D, new Map([['P1', { price: 0.0011, at: Date.now() }]]));
  expect(s).toHaveLength(3);
  expect(s[0]).toMatchObject({ seat: 1, symbol: 'CARLO', badge: 'PROTECT', entryMc: 857000, rule: 'R7 trail', usd: 0.42, heldMin: 4 });
  expect(s[0].mc).toBeCloseTo(1_100_000);                                                    // the LIVE price × the kernel's supply
  expect(s[0].last).toMatchObject({ id: 3, agent: 'reaper' });                               // newest line by id, not array order
  expect(s[1]).toMatchObject({ symbol: 'BEAR', badge: 'ORDER PENDING', entryMc: null, mc: null });   // unknown stays unknown — never 0
  expect(s[2]).toMatchObject({ open: true, badge: 'OPEN' }); expect(s[2].why).toBe('1 READY candidate on the desk this pass');   // a count, never a promise
  const w = seatCards({ ...D, office: { ...D.office, seat: { seats: [{ seat: 3, code: 'OFFICE NOT LIVE', reason: 'waits for LIVE — 1 of 2 agent passes since the restart' }] } } });
  expect(w[2]).toMatchObject({ badge: 'OFFICE NOT LIVE', why: 'waits for LIVE — 1 of 2 agent passes since the restart' });   // the server's own reason first
});

test('market cap = price × the resolved supply; nothing known → null (the chart says UNAVAILABLE, never a price chart)', () => {
  expect(mcFrom(0.0004, 1e9)).toBe(400000); expect(mcFrom(0.002, null, 0, 'PLAINMINT')).toBeNull();
  expect(mcFrom(0.00002, null, 0, PUMP)).toBeCloseTo(20000);                                 // a launchpad mint: its fixed 1B
  expect(mcFrom(0.002, null, 300000, 'PLAINMINT')).toBe(300000);                             // the live record's own cap
  expect(supplyFrom(0.002, null, 300000, 'X')).toBeCloseTo(150_000_000); expect(supplyFrom(0.002, null, 0, 'X')).toBeNull();
  expect(chartModel(D, 'MINTPLAIN').mc).toBeNull();
  const z = chartModel(D, 'MINTZYN'); expect(z.mc).toBe(400000); expect(z.lines).toEqual([]); expect(z.supplySrc).toBe('kernel');   // a candidate: no invented levels
  expect(chartModel({ office: { kernel: { candidates: [{ mint: PUMP, pair: 'PX', price: 0.00002 }] } } }, PUMP).supplySrc).toBe('launchpad');
  expect(supplyWord(1e9)).toBe('1B'); expect(supplyWord(250e6)).toBe('250M'); expect(supplyWord(null)).toBe('UNKNOWN');
});

test('the chart: the position\'s levels + REAL markers (ledger fills at their fill price, decisions on their candle)', () => {
  const m = chartModel(D, PUMP);
  expect(m.lines.map(l => l.title)).toEqual(['entry', 'take +50%', 'stop -15%']);
  expect(m.lines[1].px).toBeCloseTo(0.000857 * 1.5); expect(m.lines[2].px).toBeCloseTo(0.000857 * 0.85);
  expect(m.markers.map(x => x.text)).toEqual(['⏱ ENTER', 'BUY $0.36', '☠ PROTECT']);
  expect(m.markers[1]).toMatchObject({ time: 1000, position: 'atPriceBottom', price: 0.000857, shape: 'arrowUp' });
  expect(chartMarkers([{ id: 9, agent: 'courier', action: 'FILLED BUY', at: 5 }], [])).toEqual([]);   // fills come from the ledger, not the tape (never twice)
  expect(chartMarkers([{ agent: 'trigger', action: 'ENTER' }], [])).toEqual([]);                     // no time → not drawn
});

test('focus, decisions, tape, review queue', () => {
  expect(focusMint(D, null)).toBe(PUMP); expect(focusMint(D, 'MINTZYN')).toBe('MINTZYN'); expect(focusMint(D, 'GONE')).toBe(PUMP);
  const z = decisionOf(D, 'MINTZYN');
  expect(z).toMatchObject({ kind: 'candidate', verdict: '🟢 READY', state: 'go' }); expect(z.kernel.devil.verdict).toBe('warn'); expect(z.market).toMatchObject({ ageMin: 3, vol5m: 9000 });
  expect(decisionOf(D, PUMP)).toMatchObject({ kind: 'position', verdict: 'PROTECT', rule: 'R7 trail' });
  expect(decisionOf(D, 'MINTREV')).toMatchObject({ kind: 'review', verdict: 'RESOLVING', owner: 'track' });
  expect(decisionOf(D, 'NOPE')).toBeNull();
  expect(tapeOf(D.office.tape).map(r => r.id)).toEqual([4, 3, 2, 1]); expect(tapeOf(D.office.tape, { agent: 'reaper' }).map(r => r.id)).toEqual([3]);
  expect(lastByMint(D.office.tape)[PUMP].id).toBe(3);
  expect(['HARD VETO', 'FILLED BUY', 'WARNING', 'CANDIDATE'].map(a => tapeTone({ action: a }))).toEqual(['is-bad', 'is-good', 'is-warn', 'is-good']);
  expect(reviewQueue(D.office.kernel.candidates).map(c => c.symbol)).toEqual(['ZYN', 'PLAIN', 'OLD']);   // newest first; unknown age last
  expect(bucketCounts(D.office.kernel.candidates)).toMatchObject({ all: 3, '0-5': 1, '15-60': 1, '60-180': 0 });
  expect(inBucket({ ageMin: null }, '0-5')).toBe(false);
});

test('🎞 display easing stops EXACTLY on the real value and never overshoots it', () => {
  for (const [a, b] of [[100, 140], [140, 100], [0.5, -2]]) {
    const xs = [0, 60, 120, 240, 400, EASE_MS, EASE_MS * 3].map(t => easedAt(a, b, t));
    expect(xs[0]).toBe(a); expect(xs[xs.length - 2]).toBe(b); expect(xs[xs.length - 1]).toBe(b);
    xs.forEach(x => { expect(x).toBeGreaterThanOrEqual(Math.min(a, b)); expect(x).toBeLessThanOrEqual(Math.max(a, b)); });
  }
  expect(easedAt(null, 5, 10)).toBe(5); expect(easedAt(3, null, 10)).toBeNull();
});

test('hub deltas: a decision line is appended once by id (bounded), the owner\'s list is replaced', () => {
  let raw = { office: { tape: [{ id: 1 }] } };
  raw = applyDelta(raw, { kind: 'decision', data: { id: 2, agent: 'trigger', action: 'ENTER' } });
  expect(raw.office.tape.map(r => r.id)).toEqual([1, 2]);
  expect(applyDelta(raw, { kind: 'decision', data: { id: 2 } })).toBe(raw);                   // the same line twice = no change
  for (let i = 3; i < TAPE_KEEP + 20; i += 1) raw = applyDelta(raw, { kind: 'decision', data: { id: i } });
  expect(raw.office.tape).toHaveLength(TAPE_KEEP); expect(raw.office.tape[raw.office.tape.length - 1].id).toBe(TAPE_KEEP + 19);
  expect(applyDelta(raw, { kind: 'owner_update', data: [{ mint: 'M', mode: 'arm' }] }).office.ownerReview).toEqual([{ mint: 'M', mode: 'arm' }]);
});

test('seat states in the reference vocabulary + the seat\'s $ P&L from its own value and %', () => {
  const s = seatCards(D);
  expect(s.map(x => seatState(x, 1))).toEqual(['PROTECT', 'ARMED', 'HUNTING']);
  expect(seatState(s[2], 0)).toBe('OPEN');
  expect(seatState({ ...s[0], reaper: 'EXIT INVALIDATED' })).toBe('EXITING'); expect(seatState({ ...s[0], reaper: 'HOLD', rotate: true })).toBe('ROTATE');
  expect(seatState({ ...s[0], reaper: 'HOLD 5 MORE' })).toBe('HELD');
  expect(s[0].pnlUsd).toBeCloseTo(0.42 - 0.42 / 1.1739, 6); expect(pnlUsdOf(null, 5)).toBeNull(); expect(pnlUsdOf(1, null)).toBeNull();
});

test('mission ribbon: every tile is the card\'s own number, unknown = —', () => {
  const t = Object.fromEntries(missionTiles(D, seatCards(D)).map(x => [x.k, x]));
  expect(Object.keys(t)).toEqual(['putin', 'equity', 'net', 'phase', 'be', 'lives', 'occ', 'cycle', 'last', 'cash', 'keeper', 'exec']);
  expect(t.net.val).toBeCloseTo(1.88 - 32.5); expect(t.net.cls).toBe('m-neg'); expect(t.occ.text).toBe('2 / 3'); expect(t.lives.text).toBe('7 / 9');
  expect(t.cash.val).toBe(1.02); expect(t.keeper.text).toBe('1 ACTIVE'); expect(t.exec.text).toBe('HEALTHY'); expect(t.last.text).toBe('FILL $CARLO');
  const cold = Object.fromEntries(missionTiles({ office: {} }, []).map(x => [x.k, x]));
  expect(cold.putin.val).toBeNull(); expect(cold.net.val).toBeNull(); expect(cold.phase.text).toBe('—'); expect(cold.occ.text).toBe('—');
});

test('chart markers: ONE letter per REAL event (T D W B R X), fills from the ledger only when the tape has no courier line', () => {
  const rows = [{ id: 1, at: 10, agent: 'trigger', action: 'ENTER' }, { id: 2, at: 11, agent: 'devil', action: 'WARNING', why: 'no site' }, { id: 3, at: 12, agent: 'warden', action: 'SIZE $0.20' },
    { id: 4, at: 13, agent: 'courier', action: 'FILLED BUY', px: 0.001 }, { id: 5, at: 14, agent: 'reaper', action: 'PROTECT' }, { id: 6, at: 15, agent: 'reaper', action: 'EXIT' },
    { id: 7, at: 16, agent: 'sherlock', action: 'HOLDERS READ' }, { id: 8, agent: 'trigger', action: 'ENTER' }];
  const m = letterMarkers(rows, [{ at: 13, side: 'buy', px: 0.001 }]);
  expect(m.map(x => x.text)).toEqual(['T', 'D', 'W', 'B', 'R', 'X']);                       // no Sherlock marker; no time → not drawn; the fill is not drawn twice
  expect(m[3]).toMatchObject({ position: 'atPriceBottom', price: 0.001, agent: 'courier' });
  expect(letterMarkers([], [{ at: 20, side: 'sell', px: 0.002, usd: 0.5 }])[0]).toMatchObject({ text: 'X', price: 0.002 });
});

test('inputs: freshness words from real ages — never "live" for something never read', () => {
  expect([3, 60, 300, 4000].map(x => freshWord(x))).toEqual(['LIVE', 'FRESH', 'PARTIAL', 'STALE']);
  expect(freshWord(null)).toBe('UNAVAILABLE'); expect(freshWord(null, { pending: true })).toBe('PENDING'); expect(freshWord(5, { partial: true })).toBe('PARTIAL');
  const now = 2000 * 1000; const c = { times: { price: 1995, market: 1990, holders: null }, unknown: ['holders'], ageMin: 3 };
  const rows = Object.fromEntries(inputsOf({ c, pos: null, live: null, mc: 400000, nowMs: now }).map(r => [r[0], r]));
  expect(rows.price[1]).toBe('LIVE'); expect(rows.holders[1]).toBe('PENDING'); expect(rows['market cap'][1]).toBe('LIVE'); expect(rows['launch metadata'][1]).toBe('FRESH');
  expect(Object.fromEntries(inputsOf({ c, mc: null, nowMs: now }).map(r => [r[0], r]))['market cap'][1]).toBe('UNAVAILABLE');
  expect(inputsOf({ c: null, nowMs: now }).every(r => r[1] === 'UNAVAILABLE')).toBe(true);
});

test('trace: each of the ten desks in chain order, from the kernel trace when built, else that desk\'s newest REAL tape line', () => {
  const t = traceOf(D.office, PUMP);
  expect(t.lines.map(l => l.agent)).toEqual(['tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge']);
  expect(t.lines.find(l => l.agent === 'reaper')).toMatchObject({ word: 'PROTECT', src: 'tape' }); expect(t.lines.find(l => l.agent === 'tally').word).toBeNull();
  const k = traceOf({ ...D.office, queue: [{ mint: 'MINTZYN', trace: { lines: [['trigger', 'ENTER', 'hot'], ['devil', '⚠ DEVIL WARNS', 'identity']], final: 'READY', why: 'rank 180' } }] }, 'MINTZYN');
  expect(k.lines.find(l => l.agent === 'trigger')).toMatchObject({ word: 'ENTER', src: 'kernel trace' }); expect(k.final).toBe('READY');
});

test('pulses fire only on a NEW real event id per agent (never on the first look)', () => {
  const a = [{ id: 1, agent: 'trigger' }, { id: 2, agent: 'devil' }];
  expect(newEvents(null, a)).toEqual({});
  const seen = maxIdByAgent(a);
  expect(newEvents(seen, a)).toEqual({});
  expect(newEvents(seen, [...a, { id: 3, agent: 'trigger' }, { id: 4, agent: 'warden' }])).toEqual({ trigger: 3, warden: 4 });
});

test('review queue: status words + market cap from supply, else the live cap (no more "MC —" for a known coin)', () => {
  const [z, p, o] = D.office.kernel.candidates;
  expect([queueStatus(z), queueStatus(p), queueStatus(o)]).toEqual(['READY', 'CONTENDING', 'TRACKING']);
  expect(queueStatus({ status: 'TRACKING', ageMin: 2 })).toBe('NEW'); expect(queueStatus({ status: 'READY', owner: 'arm' })).toBe('ARMED'); expect(queueStatus({ status: 'ORDER_PENDING' })).toBe('PENDING');
  expect(queueStatus({ status: 'CONTENDING', unknown: ['holders'] })).toBe('ANALYZING');
  expect(queueMc(z)).toBe(400000); expect(queueMc({ mint: 'X', price: 0.002, cap: 250000 })).toBe(250000); expect(queueMc(p)).toBeNull();
});

test('hub: an ai_update delta replaces the AI block (advisory notes only)', () => {
  const raw = applyDelta({ office: { kernel: { candidates: [{ mint: 'M', rank: 9 }] } } }, { kind: 'ai_update', data: { providers: [{ key: 'local', state: 'ONLINE' }], notes: { M: { devil: { source: 'local' } } } } });
  expect(raw.office.ai.providers[0].state).toBe('ONLINE'); expect(raw.office.kernel.candidates[0].rank).toBe(9);
});
