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
  mind: { callsRead: 600, dictionary: 80, swarms: 2, hot: [{ key: 'ai', label: '🤖 AI', n: 9, vol1h: 400000 }], learned: [{ word: 'zoinked', n: 9 }] },
  table: [{ mint: 'M1', symbol: 'GOOD', mind: { narr: '🤖 AI', hot: true, swarm: false, bots: 0 }, analysis: { text: '$GOOD rides the 🤖 AI narrative — one of the hottest on the board right now.' }, pair: 'P1', px: 1, nums: { d5: 3, pace: 2.1, buy: 64 }, why: { drivers: [['surge', 1, 'volume surging vs the hour']], lean: 2 }, trigger: ['enter', 'lean +2'], devil: ['agree', 'no evidence against it'], go: true },
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
  await act(async () => { q('agd-feed-on').click(); });
  expect(call).toHaveBeenCalledWith('/admin/agents', expect.objectContaining({ method: 'POST', body: JSON.stringify({ feed: true }) }));
  expect(agentLine({ n: 4, med: -2, right: 50 })).toBe('4 judged · -2.0% typical at 5 min · 50% right');
});
