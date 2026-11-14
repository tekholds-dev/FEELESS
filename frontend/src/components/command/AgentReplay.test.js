import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import AgentReplay, { deskAt, lastDay, replayOf } from './AgentReplay';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const D = 86400;
const d = { chat: [{ by: 'you', text: 'find a coin', at: 10 * D }, { by: 'cats', text: 'on it', at: 10 * D + 5 }],
  jobs: [{ id: 'j', at: 10 * D + 10, request: 'read pump.fun', minds: [{ steps: [1, 2] }, { steps: [1] }] }],
  powFolders: [{ id: 'p1', n: 4, sym: 'BONK', at: 10 * D + 20, boughtAt: 10 * D + 30, soldAt: 10 * D + 90, pnlPct: 12.5, grade: 'right' }],
  psFolders: [{ id: 's1', n: 7, topic: 'Shop', at: 10 * D + 40, closedAt: 10 * D + 60, graded: 'wrong', sent: { at: 10 * D + 70 } }, { id: 'old', n: 1, topic: 'Old', at: 2 * D }] };

test('every dated thing becomes a step, oldest first; the last day drops older ones; the desk rebuilds at a step', () => {
  const all = replayOf(d);
  expect(all.map(e => e.t)).toEqual(['file', 'ask', 'say', 'research', 'file', 'buy', 'file', 'close', 'grade', 'send', 'sell', 'grade']);
  expect(all.find(e => e.t === 'research').text).toBe('read pump.fun · 2 minds, 3 steps');
  const day = lastDay(all); expect(day[0].t).toBe('ask'); expect(day).toHaveLength(11);
  const at = deskAt(day, day.findIndex(e => e.t === 'send'));
  expect(at.filed.map(e => e.id)).toEqual(['p1', 's1']); expect(at).toMatchObject({ trades: 1, wrong: 1, right: 0, sent: 1, research: 1 });
  expect(deskAt(day, day.length - 1)).toMatchObject({ right: 1, trades: 2 });
});

test('scrub back and the desk shows that moment; a filed proof opens in its window', () => {
  const opened = [];
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  act(() => root.render(<AgentReplay d={d} name="Happy" onOpen={p => opened.push(p)} onClose={() => {}} />));
  const desk = () => host.querySelector('[data-testid=replay-desk]').textContent;
  expect(desk()).toContain('11 of 11');
  const s = host.querySelector('[data-testid=replay-scrub]');
  act(() => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(s, '0'); s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); });
  expect(desk()).toContain('1 of 11'); expect(desk()).toContain('No proof filed yet');
  act(() => { host.querySelectorAll('[data-testid=replay-feed] button')[3].click(); });
  act(() => { host.querySelector('.arp-files button').click(); });
  expect(opened).toEqual([{ win: 'pow', id: 'p1' }]);
  act(() => { host.querySelector('[data-testid=replay-all]').click(); }); expect(desk()).toContain('12 of 12');
  act(() => root.unmount()); host.remove();
});
