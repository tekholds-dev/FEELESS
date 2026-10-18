import { selectors, freshness } from './agentHub';

test('one store, normalized selectors: agent · mint · seat · hunter · position · bench · metrics', () => {
  const d = { office: { at: 100, agents: [{ key: 'reaper', name: 'Reaper' }], generations: [{ role: 'reaper', generation: 2, status: 'ACTIVE' }],
    kernel: { lanes: [{ lane: 1, state: 'HUNTING' }], candidates: [{ mint: 'M', symbol: 'M', decidedAgo: 3 }], metrics: { mints: 9 } },
    seatBoard: [{ seat: 1, empty: true }], positions: [{ mint: 'P' }], bench: [{ mint: 'B' }], rpcStats: { logical: 10, physical: 7, saved: 3 } } };
  const s = selectors(d, 130);
  expect(s.getAgent('reaper').generation.generation).toBe(2); expect(s.getMint('M').symbol).toBe('M'); expect(s.getCandidate('X')).toBeNull();
  expect(s.getSeat(1).empty).toBe(true); expect(s.getHunter(1).state).toBe('HUNTING'); expect(s.getPosition('P')).toEqual({ mint: 'P' });
  expect(s.getBench()).toHaveLength(1); expect(s.getMetrics().rpc.saved).toBe(3); expect(s.snapshotAge()).toBe(30);
});

test('market freshness and decision freshness are kept apart', () => {
  const f = freshness({ decidedAgo: 45, ages: { price: 50, research: 300 } }, { at: Date.now() - 2000 });
  expect(f.market).toBe(2); expect(f.decision).toBe(45); expect(f.research).toBe(300);
});

// ── deltas: the snapshot is loaded once, then the kernel's own updates are folded in ─────────────────────────────────────────────
const { applyDelta, parseSse, hubSnapshot, hubReset, useAgentHub: useHubHook } = require('./agentHub');
const { rowState: stateOf, devilOf: devilWord, VERD: WORDS } = require('./agentRead');
const snap = () => ({ table: [{ mint: 'A', symbol: 'AAA', k: { status: 'CONTENDING', rank: 90, devil: [] } }, { mint: 'B', symbol: 'BBB', k: { status: 'TRACKING', rank: 10, devil: [] } }],
  office: { agents: [{ key: 'reaper', name: 'Reaper', card: { status: 'active' } }], positions: [{ mint: 'H', symbol: 'HHH', pct: 1, bars: [1, 2] }], generations: [{ role: 'reaper', generation: 1, status: 'ACTIVE' }],
    mission: { lastAction: null }, kernel: { lanes: [], metrics: { byStatus: { READY: 0 } }, candidates: [{ mint: 'A', symbol: 'AAA', status: 'CONTENDING', rank: 90, devil: [] }] } } });

test('applyDelta folds every delta kind into the ONE snapshot — and never mutates the old one', () => {
  const a = snap(); const frozen = JSON.stringify(a);
  let s = applyDelta(a, { kind: 'candidate_update', key: 'A', data: { mint: 'A', symbol: 'AAA', status: 'READY', rank: 150, trigger: 'ENTER', devil: [['identity', 'WARNING', 'no site']] } });
  expect(JSON.stringify(a)).toBe(frozen); expect(s).not.toBe(a);
  expect(s.office.kernel.candidates[0]).toMatchObject({ status: 'READY', rank: 150 }); expect(stateOf(s.table[0])).toBe('go');                // the board row follows the kernel at once
  expect(devilWord(s.table[0]).word).toBe('⚠ DEVIL WARNS'); expect(s.table[1]).toBe(a.table[1]);                                            // an untouched row keeps its identity (no re-render)
  s = applyDelta(s, { kind: 'candidate_update', key: 'N', data: { mint: 'N', symbol: 'NEW', status: 'HELD', rank: 5, devil: [] } });
  expect(s.office.kernel.candidates.map(c => c.mint)).toEqual(['N', 'A']);                                                                 // held first, then by rank
  s = applyDelta(s, { kind: 'candidate_update', key: 'N', data: null }); expect(s.office.kernel.candidates.map(c => c.mint)).toEqual(['A']); // a closed mint leaves
  s = applyDelta(s, { kind: 'candidate_update', key: 'A', data: { mint: 'A', symbol: 'AAA', status: 'TRACKING', rank: 40, devil: [['wall', 'HARD_VETO', 'collapsing']] } });
  expect(stateOf(s.table[0])).toBe('obj'); expect(WORDS[stateOf(s.table[0])]).toBe('✕ BLOCKED');
  s = applyDelta(s, { kind: 'hunter_update', data: [{ lane: 1, state: 'ARMED', symbol: 'AAA' }] }); expect(s.office.kernel.lanes[0].state).toBe('ARMED');
  s = applyDelta(s, { kind: 'position_update', key: 'H', data: { mint: 'H', pct: 7.5, decision: 'PROTECT' } });
  expect(s.office.positions[0]).toMatchObject({ pct: 7.5, decision: 'PROTECT', bars: [1, 2] });                                             // the snapshot's candles stay
  s = applyDelta(s, { kind: 'position_update', key: 'H', data: null }); expect(s.office.positions).toEqual([]);
  s = applyDelta(s, { kind: 'agent_update', key: 'reaper', data: { task: 'watching 2' } }); expect(s.office.agents[0]).toMatchObject({ name: 'Reaper', task: 'watching 2' });
  s = applyDelta(s, { kind: 'lifecycle_update', data: [{ role: 'reaper', generation: 2, status: 'PROBATION' }] }); expect(s.office.generations[0]).toMatchObject({ generation: 2, status: 'PROBATION' });
  s = applyDelta(s, { kind: 'execution_update', data: { courier: { health: 'BAD' }, lastAction: { kind: 'fill', symbol: 'AAA' } } });
  expect(s.office.execution.health).toBe('BAD'); expect(s.office.mission.lastAction.symbol).toBe('AAA');
  s = applyDelta(s, { kind: 'metric_update', data: { kernel: { byStatus: { READY: 2 } }, enrich: { queueDepth: 3 }, rpc: { logical: 9 }, stream: { subs: 1 } } });
  expect(s.office.kernel.metrics.byStatus.READY).toBe(2); expect(s.office.enrich.queueDepth).toBe(3); expect(s.office.rpcStats.logical).toBe(9);
  const m = applyDelta(s, { kind: 'mint_update', key: 'A', data: { price: 0.5, priceAt: 777 } });
  expect(m.office.kernel.candidates[0]).toMatchObject({ price: 0.5, times: { price: 777 }, rank: 40 });                                      // a price tick moves MARKET freshness only — the decision stays as decided
  expect(applyDelta(s, { kind: 'nonsense' })).toBe(s); expect(applyDelta(null, { kind: 'hunter_update', data: [] })).toBeNull(); expect(applyDelta(s, null)).toBe(s);
});

test('parseSse: whole frames only, a torn frame waits for the rest, beats are skipped', () => {
  const frame = (id, kind, body) => `id: ${id}\nevent: ${kind}\ndata: ${JSON.stringify(body)}\n\n`;
  const txt = `${frame(4, 'hello', { seq: 4 })}: beat\n\n${frame(5, 'candidate_update', { key: 'A', data: { status: 'READY' } })}id: 6\nevent: hunter_update\ndata: {"da`;
  const [evs, rest] = parseSse(txt);
  expect(evs).toEqual([{ kind: 'hello', seq: 4, data: { seq: 4 } }, { kind: 'candidate_update', seq: 5, key: 'A', data: { status: 'READY' } }]);
  const [more, tail] = parseSse(`${rest}ta":[]}\n\n`); expect(more).toEqual([{ kind: 'hunter_update', seq: 6, data: [] }]); expect(tail).toBe('');
  expect(parseSse('event: candidate_update\ndata: {broken\n\n')[0]).toEqual([]);                                                            // a broken frame is dropped, never thrown
});

test('ONE snapshot for every surface: two readers share one request, a one-off reader takes the store\'s copy', async () => {
  const React = require('react'); const { createRoot } = require('react-dom/client'); const { act } = require('react');
  hubReset(); const call = jest.fn(async () => snap());
  const seen = []; const Reader = ({ id }) => { const h = useHubHook(call); seen.push([id, h.d?.table?.length ?? null]); return null; };
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(React.createElement(React.Fragment, null, React.createElement(Reader, { id: 'room' }), React.createElement(Reader, { id: 'card' }))); });
  expect(call).toHaveBeenCalledTimes(1); expect(seen.filter(x => x[1] === 2).map(x => x[0]).sort()).toEqual(['card', 'room']);
  expect((await hubSnapshot(call)).table).toHaveLength(2); expect(call).toHaveBeenCalledTimes(1);                                            // the picker's 🤖 list reads the store — no second request
  await act(async () => { root.unmount(); }); hubReset();
  await hubSnapshot(call); expect(call).toHaveBeenCalledTimes(2);                                                                           // nobody mounted → one plain request
});

test('🔁 duo_update replaces the OSSY × G4 block live', () => {
  const { applyDelta } = require('./agentHub');
  const raw = { office: {}, duo: { trade: [] } };
  expect(applyDelta(raw, { kind: 'duo_update', data: { trade: [{ at: 1 }] } }).duo.trade).toHaveLength(1);
  expect(applyDelta(raw, { kind: 'duo_update', data: null })).toBe(raw);
});

test('📡 a stream that goes silent (sleep / wake, dropped network) is closed and reopened by itself — no refresh by hand', async () => {
  const React = require('react'); const { createRoot } = require('react-dom/client'); const { act } = require('react');
  const { STREAM_IDLE_MS } = require('./agentHub');
  jest.useFakeTimers(); hubReset();
  localStorage.setItem('feeless:cc-session', JSON.stringify({ address: 'A', ts: 1, sig: 'S' }));
  const enc = new (require('util').TextEncoder)(); let opened = 0;
  const realFetch = global.fetch; const realTD = global.TextDecoder;
  if (!global.TextDecoder) global.TextDecoder = require('util').TextDecoder;
  global.fetch = jest.fn(async (url, { signal }) => {
    opened += 1; let sent = false;
    return { ok: true, body: { getReader: () => ({ read: () => (sent ? new Promise((_, rej) => signal.addEventListener('abort', () => rej(new Error('aborted'))))
      : (sent = true, Promise.resolve({ done: false, value: enc.encode('event: hello\ndata: {"seq":1}\n\n') }))) }) } };
  });
  const call = jest.fn(async () => snap()); const Reader = () => { useHubHook(call); return null; };
  const root = createRoot(document.createElement('div'));
  await act(async () => { root.render(React.createElement(Reader)); });
  expect(opened).toBe(1);
  await act(async () => { jest.advanceTimersByTime(STREAM_IDLE_MS + 6000); });   // silence past the idle line → the watchdog aborts
  await act(async () => { jest.advanceTimersByTime(4500); });                     // … and the stream reconnects
  expect(opened).toBe(2);
  await act(async () => { root.unmount(); }); hubReset(); jest.useRealTimers();
  global.fetch = realFetch; global.TextDecoder = realTD; localStorage.removeItem('feeless:cc-session');
});
