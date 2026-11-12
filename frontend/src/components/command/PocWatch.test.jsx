import React from 'react';
import { act } from 'react-dom/test-utils';
import { createRoot } from 'react-dom/client';
import PocWatch from './PocWatch';

const W = { id: 'wt1', host: 'example.com', url: 'https://example.com', steps: ['Launch date?', 'Above 500 points?'], hours: 1, perHour: 4, every: 900, startedAt: 1000, endsAt: 4600, status: 'running', spentUsd: 0.002,
  checks: [{ at: 1000, ok: true, changed: true, sha: 'ab12', usd: 0.002, headline: 'Launch news', steps: [{ step: 1, seen: 'yes', note: 'set for Friday' }, { step: 2, seen: 'no', note: 'top is 320' }] }, { at: 1900, ok: true, carried: true, usd: 0, steps: [] }, { at: 2800, ok: false, why: 'It would not open (503).' }] };
const DONE = { ...W, id: 'wt2', status: 'done', report: { read: 2, checks: 3, headline: 'Launch news', steps: [{ step: 'Launch date?', verdict: 'seen', yes: 1, checks: 2, firstYesAt: 1000, last: 'set for Friday' }, { step: 'Above 500 points?', verdict: 'not seen', yes: 0, checks: 2, last: 'top is 320' }] } };

test('👁 PoC watch: the form sends page + steps + hours + checks an hour; a card shows each check and each step; a done one opens its report', async () => {
  const calls = []; const folder = jest.fn();
  const work = jest.fn(async (id, body) => { calls.push(body); return { watches: [W, DONE], model: 'local/ossy', perAskUsd: null, limits: { watches: 4, steps: 5 } }; });
  const box = document.createElement('div'); document.body.appendChild(box); const root = createRoot(box);
  await act(async () => root.render(<PocWatch cat={{ id: 'c1' }} work={work} onFolder={folder} />));
  const q = id => box.querySelector(`[data-testid="${id}"]`);
  expect(q('pw-cost').textContent).toContain('its own machine: $0');
  expect(q('pw-line-wt1').querySelectorAll('li.is-new, li.is-same, li.is-fail')).toHaveLength(3);
  expect(q('pw-step-wt1-0').textContent).toContain('YES'); expect(q('pw-step-wt2-0').textContent).toContain('SEEN');
  const set = (el, v) => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
  await act(async () => { set(q('pw-url'), 'example.com'); set(q('pw-step-in-0'), 'Launch date?'); });
  await act(async () => { q('pw-h-2').click(); }); await act(async () => { q('pw-p-4').click(); });
  await act(async () => { q('pw-go').click(); });
  expect(calls.find(b => b.op === 'watch_add').tools).toEqual({ url: 'example.com', steps: ['Launch date?'], hours: 2, perHour: 4 });
  await act(async () => { q('pw-open-wt2').click(); }); expect(folder).toHaveBeenCalled();
  await act(async () => { q('pw-stop-wt1').click(); }); expect(calls.at(-1)).toEqual({ op: 'watch_stop', text: 'wt1' });
  act(() => root.unmount());
});
