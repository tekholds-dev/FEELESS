import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AgentRoom, packetsOf, spinSec, screensOf } from './AgentRoom';

const d = { perf: { tally: 1.2, sherlock: 3.4, trigger: 0.3, devil: 0.8, at: Date.now() / 1000 - 30 },
  tasks: { tally: 'read 80 coins · 12 moving', sherlock: 'weighed 14 reasons · 30% ours', trigger: '2 ENTER · 40 WAIT', devil: 'objected to 1 of 2 entries' },
  life: { tally: { gen: 2, status: 'alive' }, sherlock: { gen: 1, status: 'probation' }, trigger: { gen: 1 }, devil: { gen: 1 } },
  agents: [{ key: 'tally', icon: '📊', name: 'Tally', n: 40, med: 0.5, right: 52 }, { key: 'devil', icon: '⚖', name: 'Devil', n: 6, med: -2, right: 66 }],
  rules: { tally: ['pace = 5-min volume × 12 ÷ the hour'], devil: ['objects to: busted reads · rug meter ≥ 50'] },
  thoughts: [{ at: Date.now() / 1000 - 20, who: 'devil', text: 'OBJECTS — its read is BOND RUN → ✋ no trade' }],
  hist: [{ at: 1, tally: { right: 48 } }, { at: 2, tally: { right: 55 } }], lessons: { devil: { words: ['Pump callers piling in (-6%)'] } },
  table: [{ mint: 'A', symbol: 'GOOD', go: true, trigger: ['enter'], devil: ['agree'], nums: { d5: 4 }, why: { drivers: [[0, 0, 'buyers lead']] } }, { mint: 'B', symbol: 'RUN', go: false, trigger: ['enter'], devil: ['object'], nums: { d5: -6 } }, { mint: 'C', symbol: 'MEH', trigger: ['wait'] }] };

test('the office: four robots with live tasks, real coins as packets, click an agent for its rules + rulings, pop out', async () => {
  expect(packetsOf(d.table).map(p => p.end)).toEqual(['go', 'obj', 'wait']);
  const sc = screensOf(d);
  expect(sc.bars.map(b => b.v)).toEqual([4, -6, 0]); expect(sc.enters).toBe(2); expect(sc.go).toBe(1);
  expect(sc.verdicts.map(v => [v.sym, v.ok, v.go])).toEqual([['GOOD', true, true], ['RUN', false, false]]); expect(sc.tags[0][0]).toBe('buyers lead');
  expect(spinSec(0)).toBe(8); expect(spinSec(100000)).toBeGreaterThanOrEqual(1.2);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AgentRoom d={d} />); });
  const q = id => document.querySelector(`[data-testid="${id}"]`);
  expect(q('agr-st-tally').textContent).toContain('read 80 coins'); expect(q('agr-st-sherlock').textContent).toContain('⚠');
  expect(q('agr').textContent).toContain('🟢 $GOOD'); expect(q('agr-board').textContent).toContain('GO'); expect(q('agr').textContent).toContain('✕ $RUN');
  expect(q('agr-detail-tally').textContent).toContain('pace = 5-min volume'); expect(q('spark-tally')).not.toBeNull();
  await act(async () => { q('agr-st-devil').dispatchEvent(new MouseEvent('click', { bubbles: true })); });
  expect(q('agr-detail-devil').textContent).toContain('BOND RUN'); expect(q('agr-detail-devil').textContent).toContain('CARRIES FROM ITS LAST LIFE');
  await act(async () => { q('agr-popout').click(); });
  expect(q('agr-pop')).not.toBeNull();
  await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); });
  expect(q('agr-pop')).toBeNull();
  await act(async () => { root.unmount(); });
});
