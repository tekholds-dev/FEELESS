import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentDesk, agentLine } from './AgentDesk';

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
  await act(async () => { createRoot(el).render(<AgentDesk call={call} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(['tally', 'sherlock', 'trigger', 'devil'].every(k => q(`agent-${k}`))).toBe(true);
  expect(q('agent-tally').textContent).toContain('no judged calls yet');
  expect(q('agd-stage').textContent).toContain('⚔ 5m'); expect(q('agd-stage').textContent).toContain('🔒 15m');
  expect(q('agd-row-GOOD').textContent).toContain('🟢 GO'); expect(q('agd-row-RUN').textContent).toContain('BOND RUN');
  expect(q('agd-desk').textContent).toContain('$20.60'); expect(q('agd-desk').textContent).toContain('1 bust');
  expect(q('agd-road').textContent).toContain('12%'); expect(q('agd-road').textContent).toContain('1.03× of 10×'); expect(q('agd-road').textContent).toContain('opens after the 10×');
  expect(q('agd-mind').textContent).toContain('600 Pump callouts'); expect(q('agd-mind').textContent).toContain('📖 zoinked'); expect(q('agd-mind').textContent).toContain('🤖 AI · 9');
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
  await act(async () => { q('agd-feed-on').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify({ feed: true }) }));
  expect(agentLine({ n: 4, med: -2, right: 50 })).toBe('4 judged · -2.0% typical at 5 min · 50% right');
});
