import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentDesk, Generations, agentLine, rowState, rowWhy, pipsOf, rankFill, boardRows, boardCounts, passLeft, liCells } from './AgentDesk';
import { devilOf, VERD } from '../../lib/agentRead';
import office from './__fixtures__/office.json';
jest.mock('../../lib/liveCandles', () => ({ useLiveCandles: () => null }));   // no network in tests
jest.mock('../terminal/PriceChart', () => ({ PriceChart: () => <div data-testid="price-chart" /> }));   // the live chart needs a canvas

// the KERNEL's decision rides on every row as `k` (backend `_paper_view`); `trigger` / `devil` / `go` / `why` are the practice desk's paper words
const K = { ready: { status: 'READY', rank: 152, why: 'RUNNING — +3.0% on rising volume, buyers 64%', trigger: 'ENTER', narrative: 'RUNNING', devil: [], hard: false, size: 1, unknown: [], courier: true },
  warned: { status: 'CONTENDING', rank: 96, why: 'BUILDING — rank 96', trigger: 'ARM', narrative: 'BUILDING', devil: [['busted_read', 'STRONG_WARNING', 'its read is BOND RUN — coins with it typically -82% in an hour'], ['identity', 'WARNING', 'no site']], hard: false, size: 0.75, unknown: ['holders'], courier: true },
  blocked: { status: 'TRACKING', rank: 40, why: 'collapsing: -22% in 5 min', trigger: 'NO', narrative: 'COLLAPSING', devil: [['wall', 'HARD_VETO', 'collapsing: -22% in 5 min']], hard: true, size: 0, unknown: [], courier: true } };
const view = {
  agents: [['tally', '📊', 'Tally', 'tracks the numbers'], ['sherlock', '🔍', 'Sherlock', 'knows why they moved'], ['trigger', '⏱', 'Trigger', 'knows when to enter'], ['devil', '⚖', 'Devil', 'argues it is right — or not']]
    .map(([key, icon, name, job], i) => ({ key, icon, name, job, n: i ? 12 : 0, med: i ? 1.5 : null, right: i ? 58 : null })),
  stage: { h: 5, conquered: [], team: { n: 12, med: 2, won: 58 }, needN: 30, needWin: 55 }, proven5: false, feedAsked: false, bar: 1.5, open: 7,
  desk: { start: 20, now: 20.6, x: 1.03, best: 1.4, busts: 1, trades: 12 },
  road: { pct: 12, paper: { done: false, x: 1.03, need: 10, n: 12, needN: 30 }, real: { open: false, done: false, n: 0, med: null, needN: 10 } },
  thoughts: [{ at: Date.now() / 1000 - 30, who: 'devil', sym: 'RUN', text: 'paper: its read is BOND RUN → no paper trade' }, { at: Date.now() / 1000 - 90, who: 'desk', sym: 'GOOD', text: '✅ $GOOD GO → +6.0% after 5 min' }], control: { n: 9, med: -1.2 }, drivers: [{ key: 'buyers', words: 'buyers in charge', n: 10, med: 1.4 }],
  tasks: { tally: 'read 80 coins · 12 moving ≥ 3% in 5 min', sherlock: 'weighed 14 reasons', trigger: '2 ENTER · 40 WAIT · 38 SKIP · bar 1.5', devil: 'argued 2 paper entries', at: Date.now() / 1000 - 20 },
  cfg: { agentFeed: true, agentTakePct: 10, agentMode: 'auto', agentSeats: 2, options: { take: [5, 10, 20, 30, 50], mode: ['auto', 'pull', 'swap'], seats: [1, 2, 3, 4] } },
  decisions: [{ pair: 'PQ', symbol: 'QI', action: 'hold', why: '−4.0% — holding until +10%' }],
  perf: { tally: 1.2, sherlock: 3.4, trigger: 0.4, devil: 0.9, coins: 3, at: 123, regime: { green: 30, word: 'cold', adj: 0.5 } },
  calibration: { '2–3': { n: 9, med: 4.1, won: 66 } }, cut: {}, burned: 2,
  creed: ['We do not know the beginning of our own making.', 'We never sign, never send and never hold a key.'], approveN: 15,
  ideas: [{ id: 'young1', kind: 'avoid', status: 'new', n: 11, med: -6, won: 20, text: 'Stay out when …' }, { id: 'abc123', kind: 'take', status: 'new', n: 16, med: 5.5, won: 66, text: 'Back it when buyers in charge + volume burst show up together.' }],
  mind: { callsRead: 600, dictionary: 80, swarms: 2, hot: [{ key: 'ai', label: '🤖 AI', n: 9, vol1h: 400000 }], learned: [{ word: 'zoinked', n: 9 }] },
  table: [{ mint: 'M1', symbol: 'GOOD', k: K.ready, vitals: { mcap: 120000, ageH: 0.5, liq: 40000, vol1h: 90000, buyShare: 64, top10: 18, bundledN: 0, organic: 3, rug: 12, safe: true }, opinion: "We'd take it: buyers in charge.", strats: ['volume burst with buyers'], mind: { narr: '🤖 AI', hot: true, swarm: false, bots: 0 }, analysis: { text: '$GOOD rides the 🤖 AI narrative — one of the hottest on the board right now.' }, pair: 'P1', px: 1, nums: { d5: 3, pace: 2.1, buy: 64 }, why: { drivers: [['surge', 1, 'volume surging vs the hour']], lean: 2.4 }, trigger: ['wait', 'lean under the bar'], devil: ['—', ''], go: false },
    { mint: 'M2', symbol: 'RUN', k: K.warned, pair: 'P2', px: 1, nums: { d5: 4 }, why: { drivers: [], lean: 2 }, trigger: ['enter', 'x'], devil: ['agree', ''], go: true, vitals: { vol1h: 10 } },
    { mint: 'M3', symbol: 'DUMP', k: K.blocked, pair: 'P3', px: 1, nums: { d5: -22 }, why: { drivers: [], lean: 0.2 }, trigger: ['skip', 'falling'], devil: ['—', ''], go: false, vitals: { vol1h: 5 } }],
  office: { ...office, kernel: { ...office.kernel, candidates: [{ mint: 'M1', symbol: 'GOOD', pair: 'P1', ...K.ready }, { mint: 'M2', symbol: 'RUN', pair: 'P2', ...K.warned }], lanes: office.kernel.lanes,
    metrics: { ...office.kernel.metrics, byStatus: { ...office.kernel.metrics.byStatus, READY: 1, CONTENDING: 1, TRACKING: 1, HELD: 1 } } },
    generations: office.generations.map(g => (g.role === 'sherlock' ? { ...g, generation: 2, status: 'PROBATION', net: 2, lossesAttributed: 2, why: '2 real losses pinned vs 0 wins credited — replaced at net 3',
      lineage: [{ gen: 1, status: 'SHADOW', why: 'real money: 3 losses pinned', changed: 'weighs early-wallet evidence 1.5×', at: 50 }], lessonVector: { walletTrust: 1.5 } } : g)) },
};

test('the Agents tab shows the KERNEL\'s decision on every coin; the practice desk\'s paper words are labelled and decide nothing', async () => {
  const call = jest.fn(async (path, opts) => (opts ? { ok: true } : view));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AgentDesk call={call} lens="all" />); });   // lens="all" stacks every lens
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(['tally', 'sherlock', 'trigger', 'devil'].every(k => q(`agent-${k}`))).toBe(true);
  expect(q('agd-stage').textContent).toContain('⚔ 5m'); expect(q('agd-stage').textContent).toContain('🔒 15m');
  // $GOOD: the paper desk said WAIT, the kernel has it READY → the board says READY. $RUN: paper GO, kernel CONTENDING with a Devil warning.
  expect(q('verdict-GOOD').textContent).toBe('🟢 READY'); expect(q('verdict-RUN').textContent).toBe('⚠ DEVIL WARNS'); expect(q('verdict-DUMP').textContent).toBe('✕ BLOCKED');
  expect(q('agd-row-RUN').textContent).toContain('BOND RUN'); expect(el.textContent).not.toMatch(/OBJECTED|objected|Devil objects/);   // a warning is never worded as a veto
  expect(q('agd-desk').textContent).toContain('$20.60'); expect(q('agd-road').textContent).toContain('1.03× of 10×');
  expect(q('agd-mind').textContent).toContain('600 Pump callouts');
  expect(q('vit-GOOD')).toBeNull();   // a row is ONE line until it is opened
  await act(async () => { q('agd-open-GOOD').click(); });
  expect(q('agd-row-GOOD').textContent).toContain('RUNNING'); expect(q('devil-GOOD').textContent).toContain('NO OBJECTION');
  expect(q('practice-GOOD').textContent).toContain('practice desk (paper, graded — no live authority)'); expect(q('practice-GOOD').textContent).toContain('WAIT');
  expect(q('op-GOOD').textContent).toContain('practice opinion');
  expect(q('vit-GOOD').textContent).toContain('$120K'); expect(q('vit-GOOD').querySelector('.is-bad').textContent).toContain('3%');   // 3% organic = bad
  await act(async () => { q('agd-open-RUN').click(); });
  expect(q('devil-RUN').textContent).toContain('⚠ DEVIL WARNS'); expect(q('devil-RUN').textContent).toContain('Warden would size ×0.75'); expect(q('agd-row-RUN').textContent).toContain('researching holders');
  expect(q('agd-floor').querySelectorAll('.agd-dot').length).toBe(3); expect(q('agd-floor').textContent).toContain('⌖ $GOOD'); expect(q('ms-sherlock').textContent).toContain('3.4 ms');
  // 🧬 ONE lifecycle for all ten roles
  expect(q('agd-gens').querySelectorAll('li').length).toBe(10); expect(q('gen-status-sherlock').textContent).toContain('PROBATION'); expect(q('gen-status-reaper').textContent).toContain('ACTIVE');
  expect(q('gen-sherlock').textContent).toContain('gen 2'); expect(q('gen-sherlock').textContent).toContain('walletTrust 1.5'); expect(q('gen-sherlock').textContent).toContain('gen 1 SHADOW');
  expect(q('life-sherlock').textContent).toContain('PROBATION'); expect(q('life-tally').textContent).toContain('ACTIVE'); expect(q('tank-tally')).toBeNull();   // the old tanks / lives / duty are gone
  expect(q('kpi-gens').textContent).toContain('1 ⚠'); expect(q('kpi-kernel').textContent).toContain('1 READY'); expect(q('kpi-lives')).toBeNull(); expect(q('kpi-duty')).toBeNull();
  expect(q('practice-note').textContent).toContain('no fill, switch, exit, size or generation reads it');
  expect(q('agd-creed').textContent).toContain('never sign');
  expect(q('idea-ok-young1').disabled).toBe(true);
  await act(async () => { q('idea-ok-abc123').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify({ idea: { id: 'abc123', action: 'approve' } }) }));
  await act(async () => { q('agc-agentMode-swap').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentMode: 'swap' } }) }));
  await act(async () => { q('agc-control-on').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentControl: true } }) }));
  expect(agentLine({ n: 4, med: -2, right: 50 })).toBe('4 judged · -2.0% typical at 5 min · 50% right');
});

test('the desk is interactive: one lens at a time, KPI tiles open ONE drawer, the board filters by the kernel\'s state', async () => {
  try { localStorage.removeItem('feeless.agentLens'); localStorage.removeItem('feeless.agentRoom'); } catch (e) { /* none */ }
  const call = jest.fn(async (path, opts) => (opts ? { ok: true } : view));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesk call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('agent-desk').textContent).toContain('REAL MONEY MISSION'); expect(q('office-hq')).not.toBeNull(); expect(q('office-board')).toBeNull();
  expect(q('agd-stream').textContent).toContain('snapshot');                                                           // no stream in a test: the snapshot poll is said, never "live"
  for (const k of ['mission', 'seats', 'kernel', 'judge', 'go', 'desk', 'road', 'market', 'ideas', 'gens']) expect(q(`kpi-${k}`)).not.toBeNull();
  expect(q('agd-drawer')).toBeNull();
  await act(async () => { q('kpi-kernel').click(); });
  expect(q('agd-drawer')).not.toBeNull(); expect(q('agd-drawer').querySelector('[data-testid="kernel-board"]')).not.toBeNull(); expect(q('ags-mission')).toBeNull();
  await act(async () => { q('kpi-mission').click(); });
  expect(q('ags-mission')).not.toBeNull(); expect(q('agd-drawer').querySelector('[data-testid="kernel-board"]')).toBeNull();   // ONE at a time
  await act(async () => { q('kpi-mission').click(); });
  expect(q('agd-drawer')).toBeNull();
  expect(call.mock.calls.filter(c => !c[1]).map(c => c[0])).toEqual(['/admin/agents']);                              // ONE request feeds the desk AND the office
  await act(async () => { q('lens-live').click(); });
  expect(q('lens-live-pane')).not.toBeNull(); expect(q('lens-learn-pane')).toBeNull();
  expect(q('kpi-go').textContent).toContain('1'); expect(q('kpi-go').textContent).toContain('1 contending');
  await act(async () => { q('board-go').click(); });
  expect(q('agd-row-GOOD')).not.toBeNull(); expect(q('agd-row-RUN')).toBeNull();
  await act(async () => { q('board-warn').click(); });   // ⚖ an ordinary concern is a WARNING, never a block
  expect(q('agd-row-RUN')).not.toBeNull(); expect(q('agd-row-GOOD')).toBeNull();
  await act(async () => { q('board-obj').click(); });    // only the hard wall is BLOCKED
  expect(q('agd-row-DUMP')).not.toBeNull(); expect(q('agd-row-RUN')).toBeNull();
  await act(async () => { el.querySelector('.agd-fl').click(); });   // a feed line about $RUN → the board resets and opens that coin
  expect(q('agd-open-RUN').getAttribute('aria-expanded')).toBe('true'); expect(q('agd-row-GOOD')).not.toBeNull();
  await act(async () => { q('kpi-ideas').click(); });
  expect(q('lens-learn-pane')).not.toBeNull(); expect(q('lens-live-pane')).toBeNull(); expect(q('agd-ideas')).not.toBeNull(); expect(q('ags-court')).not.toBeNull();   // the paper court lives in the practice lens
  await act(async () => { q('lens-life').click(); });
  expect(q('agd-gens')).not.toBeNull();
  await act(async () => { q('lens-ctl').click(); });
  expect(q('agd-controls')).not.toBeNull(); expect(q('agd-road')).not.toBeNull();
  await act(async () => { q('dial-crazy').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentDial: 'crazy' } }) }));
  expect(q('dial-crazy').parentElement.getAttribute('data-tip')).toContain('the live kernel has no dial');
  await act(async () => { q('lens-board').click(); });
  expect(q('office-board')).not.toBeNull();
  await act(async () => { root.unmount(); });
  try { localStorage.removeItem('feeless.agentLens'); localStorage.removeItem('feeless.agentRoom'); } catch (e) { /* none */ }
});

test('ONE meaning of a decision: the state, the fact that decided it, the pips, Devil\'s word, filter / search / sort, the pass clock', () => {
  const [good, run, dump] = view.table;
  expect([good, run, dump].map(rowState)).toEqual(['go', 'warn', 'obj']);
  expect(rowState({ ...good, go: true, trigger: ['enter', ''], k: undefined })).toBe('skip');                          // a paper GO with no kernel decision is nothing
  expect(rowState({ k: { ...K.ready, status: 'HELD' } })).toBe('held'); expect(rowState({ k: { ...K.ready, status: 'ORDER_PENDING' } })).toBe('pending');
  expect(rowState({ k: { status: 'CONTENDING', rank: 90, devil: [] } })).toBe('wait');
  expect(devilOf(run)).toMatchObject({ verdict: 'warn', word: '⚠ DEVIL WARNS' }); expect(devilOf(dump)).toMatchObject({ verdict: 'veto', word: '✕ BLOCKED' }); expect(devilOf(good).word).toBe('NO OBJECTION');
  expect(devilOf({ devil: { verdict: 'warn', objections: [{ rule: 'identity', evidence: 'no site', severity: 'WARNING' }] } }).word).toBe('⚠ DEVIL WARNS');   // the office's case block reads the same
  expect(Object.values(VERD).join(' ')).not.toMatch(/OBJECT/i);
  expect(rowWhy(good)).toContain('RUNNING'); expect(rowWhy(run)).toContain('BOND RUN'); expect(rowWhy(dump)).toContain('collapsing');
  expect(pipsOf(run).map(p => p[2])).toEqual(['up', 'wait', 'wait', 'warn']); expect(pipsOf(dump).map(p => p[2])).toEqual(['dn', 'go', 'no', 'no']);
  expect(rankFill(120)).toBe(0.5); expect(rankFill(999)).toBe(1); expect(rankFill(null)).toBe(0);
  const t = [dump, run, good];
  expect(boardCounts(t)).toEqual({ all: 3, go: 1, warn: 1, obj: 1, wait: 0, held: 0, skip: 0 });
  expect(boardRows(t).map(x => x.symbol)).toEqual(['GOOD', 'RUN', 'DUMP']);                                           // the kernel's order: READY, then by rank
  expect(boardRows(t, { q: '$du' }).map(x => x.symbol)).toEqual(['DUMP']); expect(boardRows(t, { sort: 'd5' }).map(x => x.symbol)).toEqual(['RUN', 'GOOD', 'DUMP']);
  expect(boardRows(t, { sort: 'vol' })[0].symbol).toBe('GOOD');
  expect(passLeft(100, 130)).toEqual({ age: 30, left: 30, frac: 0.5 }); expect(passLeft(100, 400).left).toBe(0); expect(passLeft(0, 5)).toBeNull();
});

test('the generations lens says when the book has not arrived', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<Generations gens={[]} agents={[]} />); });
  expect(el.textContent).toContain('arrives with the first office pass');
});

test('🕵 launch intel cells: every field with its tone and evidence', () => {
  expect(liCells(null)).toEqual([]);
  const c = Object.fromEntries(liCells({ ageH: 0.3, mcap: 85000, rank: ['FIRST 25', '≈ holders at entry'], first10: 34, first25: 40, cls: 'BUNDLED', clsWhy: ['5 wallets bought in the creation slot'],
    early: 22, trend: 'WORSENING', acts: { EXIT: 3, HOLD: 4 }, phase: 'ACCELERATING', healthy: true, phaseWhy: ['volume 2×'], press: 'WATCH', pressWhy: 'early buyer #3 sold $90',
    danger: 1, players: 2, conf: 80, clsRec: { n: 30, med: -12, rug: 20 } }).map(([k, v, t, tip]) => [k, { v, t, tip }]));
  expect(c['launch age'].v).toBe('18m'); expect(c.MC.v).toBe('$85K');
  expect(c['buyer rank']).toMatchObject({ v: 'FIRST 25', t: 'good' });
  expect(c['first 10'].t).toBe('bad'); expect(c.bundle).toMatchObject({ v: 'BUNDLED', t: 'warn' });
  expect(c.bundle.tip).toContain('30 launches');
  expect(c['early supply']).toMatchObject({ v: '22% held · worsening', t: 'bad' }); expect(c['early supply'].tip).toContain('3 exit');
  expect(c['FOMO phase']).toMatchObject({ v: 'ACCELERATING', t: 'good' }); expect(c['exit pressure']).toMatchObject({ v: 'WATCH', t: 'warn' });
  expect(c['dev / cluster'].t).toBe('bad'); expect(c.confidence.v).toBe('80%');
});
