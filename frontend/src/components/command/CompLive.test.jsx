import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import { parseSse } from '../../lib/agentHub';

let mockFrame = null;
jest.mock('../../lib/compLive', () => ({ useCompLive: () => ({ frame: mockFrame, live: !!mockFrame }) }));

test('📡 COMP LIVE shows only streamed numbers: loss, exam, forge, rows per kind, learner; — when nothing was measured', async () => {
  document.body.classList.add('fx-lite');
  const { CompLive, CompTools, TOOLS } = require('./CompLive');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CompLive />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('cplv-state').textContent).toMatch(/connecting/); expect(q('cplv-loss')).toBeNull();   // no stream yet: one line, no empty tiles (2026-11-14)
  mockFrame = { at: 1700000000, live: true, comp2: { training: true, iter: 40, iters: 200, loss: 1.4, val: 1.9, tail: [[10, 3], [40, 1.4]], examAnswered: 2, examTotal: 3, examN: 28, best: { name: 'COMP v2', acc: 0.61 }, compAcc: 0.61, baseAcc: 0.54, won: 75, lost: 67, market: { rows: 12, open: 3, won: 5, lost: 4, collects: 9 } },
    forge: { live: false, status: 'done', step: 1000, steps: 1000, loss: 3.61, tps: 1200, version: 'v1.02', tail: [[1, 4], [2, 3.6]] }, data: { rows: 144, pairs: 48, kinds: [{ kind: 'PoW', rows: 38 }, { kind: 'PoB', rows: 57 }] } };
  await act(async () => { root.render(<CompLive key="2" />); });
  expect(q('cplv-state').textContent).toMatch(/RUNNING/); expect(q('cplv-loss').textContent).toBe('1.400'); expect(q('cplv-exam').textContent).toBe('2/3');
  expect(q('cplv-forge').textContent).toBe('3.610'); expect(q('cplv-rows').textContent).toBe('144'); expect(q('cplv-market').textContent).toBe('12');
  expect(el.textContent).toContain('1.2K tok/s'); expect(el.textContent).toContain('61%'); expect(el.querySelectorAll('.cplv-kinds li').length).toBe(2);
  await act(async () => { root.render(<CompTools />); }); expect(q('comp-tools').querySelectorAll('li').length).toBe(TOOLS.length); expect(q('comp-tools').textContent).toMatch(/nothing installed or spent/);
  el.remove(); document.body.classList.remove('fx-lite');
});

test('📡 the stream parser turns a COMP frame event into the frame', () => {
  const [evs, rest] = parseSse('event: hello\ndata: {}\n\nevent: frame\ndata: {"at":1,"live":false,"comp2":{"loss":0.2}}\n\n: beat\n\nevent: fr');
  expect(evs.map(e => e.kind)).toEqual(['hello', 'frame']); expect(evs[1].comp2.loss).toBe(0.2); expect(rest).toBe('event: fr');
});
