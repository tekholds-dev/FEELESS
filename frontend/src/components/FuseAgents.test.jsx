import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseAgents, MAX_PICKS, agentRows, intakeLevels, pnlLine, winLine } from './FuseAgents';

jest.mock('./command/ProChart', () => ({ ProChart: ({ testid, lines }) => <div data-testid={testid} data-lines={lines.length} /> }));
global.IS_REACT_ACT_ENVIRONMENT = true;
const EXITS = [{ exitAt: 3, pnlSol: -0.5 }, { exitAt: 1, pnlSol: 1 }, { exitAt: 2, pnlSol: 0.25 }];

test('the running total adds closed trades in time order', () => {
  expect(pnlLine(EXITS)).toEqual([{ at: 1, v: 1 }, { at: 2, v: 1.25 }, { at: 3, v: 0.75 }]); expect(pnlLine(null)).toEqual([]);
});
test('the win line waits until it has enough to read', () => {
  const rows = [1, 2, 3, 4, 5, 6].map(i => ({ exitAt: i, pnlSol: i % 2 ? 1 : -1 }));
  expect(winLine(rows, 5)).toEqual([{ at: 5, v: 60 }, { at: 6, v: 60 }].map((r, i) => (i ? { at: 6, v: 40 } : r))); expect(winLine(rows.slice(0, 4), 5)).toEqual([]);
});
test('the intake counts each stage', () => {
  expect(intakeLevels([{ status: 'TRACKING' }, { status: 'DISCOVERED' }, { status: 'READY' }, { status: 'HELD' }, { status: 'CONTENDING' }])).toEqual({ in: 2, contending: 1, ready: 1, picked: 1 });
});
test('at most five agents are offered, the ones with a record first', () => {
  const rows = agentRows([...Array(8)].map((_, i) => ({ id: `a${i}`, trades: i })));
  expect(rows).toHaveLength(5); expect(rows[0].id).toBe('a7');
});

test('it opens on real agents, picks up to three, and shows what its ledger does to its size', async () => {
  const rows = ['a', 'b', 'c', 'd'].map((id, i) => ({ id, name: id.toUpperCase(), trades: 10 - i }));
  const seen = [];
  global.fetch = jest.fn(async url => { seen.push(url); return { ok: true, json: async () => (url.includes('leaderboard') ? { rows } : url.includes('intake') ? { coins: [{ status: 'READY' }] } : { exits: EXITS, discipline: { sizeMult: 0.5, lives: 7, maxLives: 9, winRate: 40, netSol: -0.02, why: '3 losses in a row, half size until a win' } }) }; });
  const el = document.createElement('div'); const root = createRoot(el); await act(async () => { root.render(<FuseAgents />); });
  const q = t => el.querySelector(`[data-testid="${t}"]`); const on = () => el.querySelectorAll('.fag-picks button[aria-pressed="true"]').length;
  expect(on()).toBe(MAX_PICKS); expect(q('fag-size-a').textContent).toBe('0.5x'); expect(q('fag-why-a').textContent).toContain('half size'); expect(q('fag-lane-ready').textContent).toContain('1'); expect(q('fag-pnl').dataset.lines).toBe('3');
  await act(async () => { q('fag-pick-d').click(); }); expect(on()).toBe(MAX_PICKS); expect(q('fag-card-a')).toBeNull(); expect(q('fag-card-d')).not.toBeNull();
  expect(seen.every(u => !u.includes('admin') && !u.includes('/work'))).toBe(true);   // public reads only
  await act(async () => { root.unmount(); });
});
