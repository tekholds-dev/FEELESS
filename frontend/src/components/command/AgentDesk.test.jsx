import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentDesk, agentLine, rowState, rowWhy, pipsOf, leanFill, boardRows, boardCounts, passLeft } from './AgentDesk';

const view = {
  agents: [['tally', '📊', 'Tally', 'tracks the numbers'], ['sherlock', '🔍', 'Sherlock', 'knows why they moved'], ['trigger', '⏱', 'Trigger', 'knows when to enter'], ['devil', '⚖', 'Devil', 'argues it is right — or not']]
    .map(([key, icon, name, job], i) => ({ key, icon, name, job, n: i ? 12 : 0, med: i ? 1.5 : null, right: i ? 58 : null })),
  stage: { h: 5, conquered: [], team: { n: 12, med: 2, won: 58 }, needN: 30, needWin: 55 }, proven5: false, feedAsked: false, bar: 1.5, open: 7,
  desk: { start: 20, now: 20.6, x: 1.03, best: 1.4, busts: 1, trades: 12 },
  road: { pct: 12, paper: { done: false, x: 1.03, need: 10, n: 12, needN: 30 }, real: { open: false, done: false, n: 0, med: null, needN: 10 } },
  thoughts: [{ at: Date.now() / 1000 - 30, who: 'devil', sym: 'RUN', text: 'OBJECTS — its read is BOND RUN → ✋ no trade' }, { at: Date.now() / 1000 - 90, who: 'desk', sym: 'GOOD', text: '✅ $GOOD GO → +6.0% after 5 min' }], control: { n: 9, med: -1.2 }, drivers: [{ key: 'buyers', words: 'buyers in charge', n: 10, med: 1.4 }],
  tasks: { tally: 'read 80 coins · 12 moving ≥ 3% in 5 min', sherlock: 'weighed 14 reasons · 31% of today\'s reads are our own record', trigger: '2 ENTER · 40 WAIT · 38 SKIP · bar 1.5', devil: 'objected to 1 of 2 entries', at: Date.now() / 1000 - 20 },
  cfg: { agentFeed: true, agentTakePct: 10, agentMode: 'auto', agentSeats: 2, options: { take: [5, 10, 20, 30, 50], mode: ['auto', 'pull', 'swap'], seats: [1, 2, 3, 4] } },
  decisions: [{ pair: 'PQ', symbol: 'QI', action: 'hold', why: '−4.0% — holding until +10% (only the rug shield cuts it)' }],
  perf: { tally: 1.2, sherlock: 3.4, trigger: 0.4, devil: 0.9, coins: 2, at: 123, regime: { green: 30, word: 'cold', adj: 0.5 } }, lessons: { tally: { words: ['Pump callers piling in (-6.0%, n 10)'] } },
  calibration: { '2–3': { n: 9, med: 4.1, won: 66 } }, cut: { calls: { n: 60, med: -3 } }, burned: 2, surviveN: 30, scrapN: 60,
  creed: ['We do not know the beginning of our own making.', 'We never sign, never send and never hold a key.'], lineage: [{ agent: 'tally', gen: 1, n: 65, right: 38 }], approveN: 15,
  life: { tally: { gen: 2, status: 'alive', n: 5 }, sherlock: { gen: 1, status: 'probation', n: 40 }, trigger: { gen: 1, status: 'alive' }, devil: { gen: 1, status: 'alive' } },
  ideas: [{ id: 'young1', kind: 'avoid', status: 'new', n: 11, med: -6, won: 20, text: 'Stay out when …' }, { id: 'abc123', kind: 'take', status: 'new', n: 16, med: 5.5, won: 66, text: 'Back it when buyers in charge + 🎯 volume burst with buyers show up together: 12 calls went +5.5% typical in 5 min (66% up).' }],
  mind: { callsRead: 600, dictionary: 80, swarms: 2, hot: [{ key: 'ai', label: '🤖 AI', n: 9, vol1h: 400000 }], learned: [{ word: 'zoinked', n: 9 }] },
  table: [{ mint: 'M1', symbol: 'GOOD', vitals: { mcap: 120000, ageH: 0.5, liq: 40000, vol1h: 90000, buyShare: 64, top10: 18, bundledN: 0, organic: 3, rug: 12, safe: true }, opinion: "We'd take it: buyers in charge. 31% of this read is our own record, 69% starting belief.", strats: ['volume burst with buyers'], mind: { narr: '🤖 AI', hot: true, swarm: false, bots: 0 }, analysis: { text: '$GOOD rides the 🤖 AI narrative — one of the hottest on the board right now.' }, pair: 'P1', px: 1, nums: { d5: 3, pace: 2.1, buy: 64 }, why: { drivers: [['surge', 1, 'volume surging vs the hour']], lean: 2 }, trigger: ['enter', 'lean +2'], devil: ['agree', 'no evidence against it'], go: true },
    { mint: 'M2', symbol: 'RUN', pair: 'P2', px: 1, nums: { d5: 4 }, why: { drivers: [], lean: 2 }, trigger: ['enter', 'x'], devil: ['object', 'its read is BOND RUN'], go: false }],
};

test('the agent desk: four agents in one chain, the stage, the live table with every agent\'s word, and the owner feed switch', async () => {
  const call = jest.fn(async (path, opts) => (opts ? { ok: true } : view));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<AgentDesk call={call} lens="all" />); });   // lens="all" stacks every lens
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(['tally', 'sherlock', 'trigger', 'devil'].every(k => q(`agent-${k}`))).toBe(true);
  expect(q('agent-tally').getAttribute('data-tip')).toContain('no judged calls yet');
  expect(q('agd-stage').textContent).toContain('⚔ 5m'); expect(q('agd-stage').textContent).toContain('🔒 15m');
  expect(q('agd-row-GOOD').textContent).toContain('🟢 GO'); expect(q('agd-row-RUN').textContent).toContain('BOND RUN');
  expect(q('agd-desk').textContent).toContain('$20.60'); expect(q('agd-desk').textContent).toContain('1 bust');
  expect(q('agd-road').textContent).toContain('12%'); expect(q('agd-road').textContent).toContain('1.03× of 10×'); expect(q('agd-road').textContent).toContain('opens after the 10×');
  expect(q('agd-mind').textContent).toContain('600 Pump callouts'); expect(q('agd-mind').textContent).toContain('📖 zoinked'); expect(q('agd-mind').textContent).toContain('🤖 AI · 9');
  expect(q('vit-GOOD')).toBeNull();   // a row is ONE line until it is opened
  await act(async () => { q('agd-open-GOOD').click(); });
  expect(q('agd-row-GOOD').textContent).toContain('rides the 🤖 AI narrative');
  expect(q('agd-thoughts').textContent).toContain('⚖ Devil'); expect(q('agd-thoughts').textContent).toContain('+6.0% after 5 min');
  expect(q('task-tally').textContent).toContain('read 80 coins'); expect(q('task-devil').textContent).toContain('objected to 1 of 2');
  expect(q('vit-GOOD').textContent).toContain('$120K'); expect(q('vit-GOOD').querySelector('.is-bad').textContent).toContain('3%');   // 3% organic = bad
  expect(q('op-GOOD').textContent).toContain('31% of this read is our own record'); expect(q('op-GOOD').textContent).toContain('🎯 volume burst');
  expect(q('agd-decisions').textContent).toContain('holding until +10%');
  expect(q('agd-floor').textContent).toContain('2 coins · 1.2 ms'); expect(q('agd-floor').querySelectorAll('.agd-dot').length).toBe(2);
  expect(q('agd-floor').textContent).toContain('⌖ $GOOD') ; expect(q('ms-sherlock').textContent).toContain('3.4 ms');
  expect(q('tank-tally').textContent).toContain('gen 3 waiting'); expect(q('tank-tally').textContent).toContain('inherits: Pump callers piling in');
  expect(q('tank-sherlock').textContent).toContain('probation');
  expect(q('agd-edge').textContent).toContain('lean 2–3'); expect(q('agd-edge').textContent).toContain('cold'); expect(q('agd-edge').textContent).toContain('budget cut: calls');
  expect(q('life-tally').textContent).toContain('gen 2'); expect(q('life-sherlock').textContent).toContain('probation');
  expect(q('agd-creed').textContent).toContain('never sign'); expect(q('agd-creed').textContent).toContain('☠ 📊 Tally gen 1 · 65 calls · 38% right');
  expect(q('idea-ok-young1').disabled).toBe(true); expect(q('idea-ok-young1').textContent).toContain('11/15 calls');   // approvable only at 15
  await act(async () => { q('idea-ok-abc123').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify({ idea: { id: 'abc123', action: 'approve' } }) }));
  await act(async () => { q('agc-agentMode-swap').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentMode: 'swap' } }) }));
  await act(async () => { q('agc-control-on').click(); });   // 🎮 hand them every seat = one owner tap
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentControl: true } }) }));
  await act(async () => { q('agd-feed-on').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify({ feed: true }) }));
  expect(agentLine({ n: 4, med: -2, right: 50 })).toBe('4 judged · -2.0% typical at 5 min · 50% right');
});

test('the desk is interactive: one lens at a time, KPI tiles jump, the board filters / searches / opens, the feed and the agents drive it', async () => {
  try { localStorage.removeItem('feeless.agentLens'); localStorage.removeItem('feeless.agentRoom'); } catch (e) { /* none */ }
  const call = jest.fn(async (path, opts) => (opts ? { ok: true } : view));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentDesk call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('office-board')).not.toBeNull(); expect(q('lens-live-pane')).toBeNull(); expect(q('agent-desk').textContent).toContain('REAL MONEY MISSION'); expect(q('office-hq')).not.toBeNull(); expect(q('agd-board-fold')).not.toBeNull();   // opens on the 🏢 Office: data first
  expect(q('agent-tally')).toBeNull();                                                                                 // the four-desk picker lives in the Live view now
  expect(call.mock.calls.filter(c => !c[1]).map(c => c[0])).toEqual(['/admin/agents']);                              // ONE request feeds the desk AND the office
  await act(async () => { q('lens-live').click(); });
  expect(q('lens-live-pane')).not.toBeNull(); expect(q('office-board')).toBeNull(); expect(q('lens-learn-pane')).toBeNull(); expect(q('agd-controls')).toBeNull();   // one lens at a time
  expect(q('kpi-go').textContent).toContain('1'); expect(q('kpi-go').textContent).toContain('2 ENTER'); expect(q('kpi-desk').textContent).toContain('$20.60');
  expect(q('agd-clock')).not.toBeNull();
  await act(async () => { q('board-go').click(); });
  expect(q('agd-row-GOOD')).not.toBeNull(); expect(q('agd-row-RUN')).toBeNull();
  await act(async () => { q('board-obj').click(); });
  expect(q('agd-row-RUN')).not.toBeNull(); expect(q('agd-row-GOOD')).toBeNull();
  await act(async () => { el.querySelector('.agd-fl').click(); });   // a feed line about $RUN → the board resets and opens that coin
  expect(q('agd-open-RUN').getAttribute('aria-expanded')).toBe('true'); expect(q('agd-row-GOOD')).not.toBeNull();
  expect(q('agd-row-RUN').textContent).toContain('Devil · argues');
  await act(async () => { q('agent-devil').click(); });   // pick an agent → its card is pressed and the feed shows only its words
  expect(q('agent-devil').getAttribute('aria-pressed')).toBe('true'); expect(q('agd-thoughts').textContent).toContain('OBJECTS'); expect(q('agd-thoughts').textContent).not.toContain('+6.0% after 5 min');
  await act(async () => { q('kpi-ideas').click(); });
  expect(q('lens-learn-pane')).not.toBeNull(); expect(q('lens-live-pane')).toBeNull(); expect(q('agd-ideas')).not.toBeNull();
  await act(async () => { q('lens-ctl').click(); });
  expect(q('agd-controls')).not.toBeNull(); expect(q('agd-road')).not.toBeNull();
  await act(async () => { q('dial-crazy').click(); });   // 🔥 the creator's dial is one tap, saved as agentDial
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ body: JSON.stringify({ cfg: { agentDial: 'crazy' } }) }));
  expect(q('ags-court')).not.toBeNull(); expect(q('ags-stake').textContent).toContain('next stake 25%');
  expect(q('agd-office').getAttribute('aria-pressed')).toBe('true');       // the room is on by default
  await act(async () => { q('agd-office').click(); });
  expect(q('agd-office').getAttribute('aria-pressed')).toBe('false');
  await act(async () => { q('agd-office').click(); });
  await act(async () => { root.unmount(); });
  try { localStorage.removeItem('feeless.agentLens'); localStorage.removeItem('feeless.agentRoom'); } catch (e) { /* none */ }
});

test('board + clock helpers: a row\'s state, the fact that decided it, the pips, the lean meter, filter / search / sort, the pass clock', () => {
  const [good, run] = view.table; const wait = { mint: 'M3', symbol: 'MEH', nums: { d5: -2 }, why: { drivers: [], lean: -1 }, trigger: ['wait', 'lean under the bar'], devil: ['—', ''], vitals: { vol1h: 5 } };
  expect([good, run, wait].map(rowState)).toEqual(['go', 'obj', 'wait']);
  expect(rowWhy(good)).toBe('volume surging vs the hour'); expect(rowWhy(run)).toBe('its read is BOND RUN'); expect(rowWhy(wait)).toBe('lean under the bar');
  expect(pipsOf(run).map(p => p[2])).toEqual(['up', 'up', 'go', 'no']); expect(pipsOf(wait).map(p => p[2])).toEqual(['dn', 'dn', 'wait', 'idle']);
  expect(leanFill(1.5, 1.5)).toBe(0.5); expect(leanFill(9, 1.5)).toBe(1); expect(leanFill(null, null)).toBe(0);
  const t = [good, run, wait];
  expect(boardCounts(t)).toEqual({ all: 3, go: 1, enter: 2, obj: 1, wait: 1, skip: 0 });
  expect(boardRows(t, { f: 'enter' }).map(x => x.symbol)).toEqual(['GOOD', 'RUN']); expect(boardRows(t, { q: '$me' }).map(x => x.symbol)).toEqual(['MEH']);
  expect(boardRows(t, { sort: 'd5' }).map(x => x.symbol)).toEqual(['RUN', 'GOOD', 'MEH']); expect(boardRows(t, { sort: 'vol' })[0].symbol).toBe('GOOD');
  expect(passLeft(100, 130)).toEqual({ age: 30, left: 30, frac: 0.5 }); expect(passLeft(100, 400).left).toBe(0); expect(passLeft(0, 5)).toBeNull();
});
