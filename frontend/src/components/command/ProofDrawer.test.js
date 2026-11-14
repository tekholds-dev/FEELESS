import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ProofDrawer, { lineDiff } from './ProofDrawer';
import { chatProof } from './CatWorkbench';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const click = async el => { await act(async () => { el.dispatchEvent(new MouseEvent('click', { bubbles: true })); }); };
const type = (el, v) => act(() => { const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); });

test('line diff counts what moved between two versions, ignoring indent and blank lines', () => {
  expect(lineDiff('<h1>a</h1>\n  <p>x</p>\n\n', '<h1>a</h1>\n<p>y</p>\n<p>z</p>')).toEqual({ added: 2, removed: 1 });
  expect(lineDiff('', '')).toEqual({ added: 0, removed: 0 });
});

test('a chat line opens the proof it is about, in the desk', () => {
  const d = { pobFolders: [{ id: 'b1', at: 100 }, { id: 'b2', at: 500 }, { id: 'b3', at: 2000 }] };
  expect(chatProof(d, 'bids', 900)).toEqual({ win: 'bids', id: 'b2' });   // filed before the line (+10 min)
  expect(chatProof(d, 'bids', 0)).toEqual({ win: 'bids', id: 'b3' });     // no time: the newest
  expect(chatProof({}, 'pow', 5)).toBe('pow');                              // nothing filed: just the window
});

test('the drawer: file list, grade with a why, re-run with that why, compare two versions', async () => {
  const calls = []; const sent = [];
  const rows = [{ id: 'ps2', ws: 'w1', n: 7, version: 2, topic: 'Shop', by: 'MIND B' }, { id: 'ps1', ws: 'w1', n: 6, version: 1, topic: 'Shop', by: 'MIND A', graded: 'right' }];
  const work = jest.fn(async (id, body) => {
    calls.push(body);
    if (body.op === 'state') return { psFolders: rows };
    if (body.op === 'ps_mark') { rows[0] = { ...rows[0], graded: body.text, gradeWhy: body.tools.why }; return { psFolders: rows }; }
    if (body.op === 'ws_version') return { version: { i: body.i, by: 'X', lines: body.i * 2, html: body.i === 1 ? '<p>a</p>' : '<p>a</p>\n<p>b</p>', preview: '<p>x</p>' } };
    return {};
  });
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  await act(async () => { root.render(<ProofDrawer cat={{ id: 'g' }} row={{ id: 'w1' }} work={work} doc={{ versions: 2 }} send={async (t, to) => sent.push([t, to])} />); });
  await click(host.querySelector('[data-testid=pdr-toggle]'));
  expect(host.querySelector('[data-testid=pdr-panel-file]').textContent).toContain('#7');
  await click(host.querySelector('[data-testid=pdr-step-grade]'));
  type(host.querySelector('[data-testid=pdr-why]'), 'buy button dead');
  await click(host.querySelector('[data-testid=pdr-bad]'));
  expect(calls.find(c => c.op === 'ps_mark')).toEqual({ op: 'ps_mark', job: 'ps2', text: 'wrong', tools: { why: 'buy button dead' } });
  await click(host.querySelector('[data-testid=pdr-step-rerun]'));
  expect(host.querySelector('[data-testid=pdr-ask]').value).toBe('buy button dead');
  await click(host.querySelector('[data-testid=pdr-rerun]'));
  expect(sent[0][0]).toContain('buy button dead'); expect(sent[0][1]).toBe('both');
  await click(host.querySelector('[data-testid=pdr-step-compare]'));
  expect(calls.filter(c => c.op === 'ws_version').map(c => c.i).sort()).toEqual([1, 2]);
  expect(host.querySelector('[data-testid=pdr-diff]').textContent).toContain('+1');
  expect(host.querySelector('[data-testid=pdr-v-a]')).not.toBeNull(); expect(host.querySelector('[data-testid=pdr-v-b]')).not.toBeNull();
  act(() => root.unmount()); host.remove();
});
