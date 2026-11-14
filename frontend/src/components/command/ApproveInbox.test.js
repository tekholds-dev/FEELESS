import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ApproveInbox, { ApproveButton, costLine, useApprovals } from './ApproveInbox';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const row = { id: 'ap1', kind: 'redo', state: 'waiting', what: 'Redo PoStatic #2 with both minds, fixing Sources', models: ['gpt-x', 'q3'], estUsd: 0.0123, at: 1,
  op: { op: 'ws_build', job: 'w1', text: 'Run it again and fix this first: Sources', to: 'both' } };

test('the inbox says what runs, on which models, about what it costs; nothing runs without the Approve tap', async () => {
  expect(costLine(0.0123)).toContain('$0.0123'); expect(costLine(null)).toContain('not known');
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host);
  const calls = []; const work = jest.fn(async (_id, body) => { calls.push(body); return body.op === 'approve' ? { approvals: [{ ...row, state: body.job === 'yes' ? 'ran' : 'declined' }], row: { ...row, state: body.job === 'yes' ? 'ran' : 'declined' } } : { approvals: [row] }; });
  function Box() { const [rows, decide] = useApprovals('g', work); return <><ApproveButton rows={rows} onOpen={() => {}} /><ApproveInbox rows={rows} onDecide={decide} onClose={() => {}} /></>; }
  await act(async () => root.render(<Box />));
  expect(calls).toEqual([{ op: 'approvals' }]);   // reading the inbox spends nothing
  expect(host.querySelector('[data-testid=dsk-approve]').textContent).toContain('1');
  const r = host.querySelector('[data-testid=apx-ap1]').textContent;
  expect(r).toContain('Both minds rebuild the page'); expect(r).toContain('gpt-x'); expect(r).toContain('q3'); expect(r).toContain('$0.0123'); expect(r).toContain('Nothing runs until you tap Approve');
  await act(async () => { host.querySelector('[data-testid=apx-yes-ap1]').click(); });
  expect(calls[1]).toEqual({ op: 'approve', text: 'ap1', job: 'yes' });
  expect(host.textContent).toContain('Approved: it is running'); expect(host.querySelector('[data-testid=apx-yes-ap1]')).toBeNull();
  act(() => root.unmount()); host.remove();
});

test('decline sends no, and an empty inbox explains itself', async () => {
  const host = document.createElement('div'); document.body.appendChild(host); const root = createRoot(host); const onDecide = jest.fn(async () => ({ ...row, state: 'declined' }));
  await act(async () => root.render(<ApproveInbox rows={[row]} onDecide={onDecide} onClose={() => {}} />));
  await act(async () => { host.querySelector('[data-testid=apx-no-ap1]').click(); });
  expect(onDecide).toHaveBeenCalledWith('ap1', false); expect(host.textContent).toContain('Declined: nothing ran.');
  await act(async () => root.render(<ApproveInbox rows={[]} onDecide={onDecide} onClose={() => {}} />));
  expect(host.textContent).toContain('Nothing is waiting');
  act(() => root.unmount()); host.remove();
});
